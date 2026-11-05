"""Acceptance tests written before environment implementation. No mocks of transitions."""
import copy
import importlib
import json
import unittest

SCENARIOS = ("normal", "failed_timeout", "committed_timeout", "pending_timeout", "false_success")


class EnvironmentContract(unittest.TestCase):
    def env(self, scenario="normal", reward_mode="strict", max_steps=12, delay=3):
        cls = importlib.import_module("click_once.env").ClickOnceEnv
        env = cls(reward_mode=reward_mode, max_steps=max_steps)
        self.addCleanup(env.close)
        obs, info = env.reset(seed=17, options={"scenario": scenario, "delay": delay})
        self.assertEqual(info, {}, "Private state must not leak through Gym info")
        return env, obs

    def test_initial_observation_has_only_public_fields(self):
        env, obs = self.env()
        self.assertEqual(set(obs), {"goal", "page", "notice", "rows", "buttons"})
        self.assertEqual(obs["notice"], "Ready")
        self.assertEqual(obs["rows"], [])
        json.dumps(obs)  # Serialized policy payload is the observation boundary.

    def test_normal_submission_is_one_confirmed_booking(self):
        env, _ = self.env()
        obs, reward, term, trunc, info = env.step("SUBMIT")
        self.assertEqual(obs["notice"], "Success")
        self.assertAlmostEqual(reward, -0.01)
        self.assertFalse(term or trunc)
        self.assertEqual(info, {})
        self.assertEqual(env.audit()["confirmed_count"], 1)
        self.assertFalse(env.audit()["strict_success"], "Not finished yet")

    def test_same_timeout_hides_three_distinct_worlds(self):
        payloads = []
        counts = []
        for scenario in ("failed_timeout", "committed_timeout", "pending_timeout"):
            env, _ = self.env(scenario)
            obs, reward, term, trunc, info = env.step("SUBMIT")
            payloads.append(json.dumps(obs, sort_keys=True))
            counts.append((env.audit()["confirmed_count"], env.audit()["pending_count"]))
            self.assertEqual(info, {})
            self.assertAlmostEqual(reward, -0.01)
        self.assertEqual(len(set(payloads)), 1, "No hidden fault signal in observation")
        self.assertEqual(counts, [(0, 0), (1, 0), (0, 1)])

    def test_history_distinguishes_failure_success_pending(self):
        statuses = []
        for scenario in ("failed_timeout", "committed_timeout", "pending_timeout"):
            env, _ = self.env(scenario)
            env.step("SUBMIT")
            obs, *_ = env.step("CHECK_HISTORY")
            statuses.append([r["status"] for r in obs["rows"]])
        self.assertEqual(statuses, [[], ["confirmed"], ["pending"]])

    def test_history_rows_are_visible_evidence_not_hidden_metadata(self):
        env, _ = self.env("committed_timeout")
        env.step("SUBMIT")
        obs, *_ = env.step("CHECK_HISTORY")
        self.assertEqual(set(obs["rows"][0]), {"id", "target", "status"})
        self.assertEqual(obs["rows"][0]["target"], obs["goal"])

    def test_pending_becomes_confirmed_after_documented_ticks(self):
        env, _ = self.env("pending_timeout", delay=3)
        env.step("SUBMIT")  # t1, due at t4
        obs, *_ = env.step("CHECK_HISTORY")  # t2
        self.assertEqual(obs["rows"][0]["status"], "pending")
        env.step("WAIT")  # t3
        obs, *_ = env.step("CHECK_HISTORY")  # t4
        self.assertEqual(obs["rows"][0]["status"], "confirmed")
        self.assertEqual(env.audit()["pending_count"], 0)

    def test_failure_can_be_retried_successfully(self):
        env, _ = self.env("failed_timeout")
        env.step("SUBMIT")
        env.step("CHECK_HISTORY")
        env.step("SUBMIT")
        _, reward, term, trunc, _ = env.step("FINISH")
        self.assertTrue(term)
        self.assertFalse(trunc)
        self.assertAlmostEqual(reward, 0.99)
        self.assertTrue(env.audit()["strict_success"])

    def test_optimistic_success_does_not_create_booking(self):
        env, _ = self.env("false_success")
        obs, *_ = env.step("SUBMIT")
        self.assertEqual(obs["notice"], "Success")
        self.assertEqual(env.audit()["confirmed_count"], 0)
        obs, *_ = env.step("CHECK_HISTORY")
        self.assertEqual(obs["rows"], [])

    def test_inspecting_only_does_not_change_backend(self):
        env, _ = self.env("committed_timeout")
        env.step("SUBMIT")
        for _ in range(4):
            env.step("CHECK_HISTORY")
        self.assertEqual(env.audit()["submission_attempts"], 1)
        self.assertEqual(env.audit()["confirmed_count"], 1)
        self.assertEqual(env.audit()["duplicate_count"], 0)

    def test_duplicate_retry_is_not_strict_success(self):
        env, _ = self.env("committed_timeout")
        env.step("SUBMIT")
        env.step("SUBMIT")
        _, reward, *_ = env.step("FINISH")
        self.assertEqual(env.audit()["confirmed_count"], 2)
        self.assertGreater(env.audit()["duplicate_count"], 0)
        self.assertFalse(env.audit()["strict_success"])
        self.assertLess(reward, 0)

    def test_pending_retry_records_duplicate_even_after_completion(self):
        env, _ = self.env("pending_timeout")
        env.step("SUBMIT")
        env.step("SUBMIT")
        env.step("WAIT")
        env.step("CHECK_HISTORY")
        env.step("FINISH")
        self.assertEqual(env.audit()["confirmed_count"], 2)
        self.assertGreater(env.audit()["duplicate_count"], 0)
        self.assertFalse(env.audit()["strict_success"])

    def test_finish_before_pending_resolves_fails(self):
        env, _ = self.env("pending_timeout", delay=3)
        env.step("SUBMIT")
        _, reward, term, trunc, _ = env.step("FINISH")
        self.assertTrue(term)
        self.assertFalse(trunc)
        self.assertLess(reward, 0)
        self.assertFalse(env.audit()["strict_success"])

    def test_empty_finish_fails(self):
        env, _ = self.env()
        _, reward, term, trunc, _ = env.step("FINISH")
        self.assertTrue(term)
        self.assertFalse(trunc)
        self.assertLess(reward, 0)
        self.assertFalse(env.audit()["strict_success"])

    def test_episode_limit_truncates_without_success(self):
        env, _ = self.env(max_steps=2)
        env.step("WAIT")
        _, reward, term, trunc, _ = env.step("WAIT")
        self.assertFalse(term)
        self.assertTrue(trunc)
        self.assertLess(reward, 0)
        self.assertFalse(env.audit()["strict_success"])

    def test_finish_on_last_allowed_step_is_termination(self):
        env, _ = self.env(max_steps=2)
        env.step("SUBMIT")
        _, _, term, trunc, _ = env.step("FINISH")
        self.assertTrue(term)
        self.assertFalse(trunc)

    def test_invalid_action_does_not_mutate_state(self):
        env, obs = self.env()
        before = copy.deepcopy(env.audit())
        with self.assertRaises(ValueError):
            env.step("DELETE_DATABASE")
        self.assertEqual(before, env.audit())

    def test_step_after_finish_rejected_without_mutation(self):
        env, _ = self.env()
        env.step("SUBMIT")
        env.step("FINISH")
        before = copy.deepcopy(env.audit())
        with self.assertRaises(RuntimeError):
            env.step("SUBMIT")
        self.assertEqual(before, env.audit())

    def test_step_after_truncation_rejected_without_mutation(self):
        env, _ = self.env(max_steps=1)
        env.step("WAIT")
        before = copy.deepcopy(env.audit())
        with self.assertRaises(RuntimeError):
            env.step("FINISH")
        self.assertEqual(before, env.audit())

    def test_reset_clears_previous_bookings_and_attempts(self):
        env, initial = self.env()
        env.step("SUBMIT")
        env.reset(seed=17, options={"scenario": "normal", "delay": 3})
        audit = env.audit()
        self.assertEqual(audit["confirmed_count"], 0)
        self.assertEqual(audit["submission_attempts"], 0)
        self.assertEqual(audit["steps"], 0)

    def test_seeded_action_replay_is_reproducible(self):
        env1, obs1 = self.env("pending_timeout")
        env2, obs2 = self.env("pending_timeout")
        self.assertEqual(obs1, obs2)
        for action in ("SUBMIT", "CHECK_HISTORY", "WAIT", "CHECK_HISTORY", "FINISH"):
            self.assertEqual(env1.step(action), env2.step(action))
        self.assertEqual(env1.audit(), env2.audit())

    def test_public_only_policy_can_solve_every_scenario(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                env, obs = self.env(scenario)
                env.step("SUBMIT")
                for _ in range(10):
                    obs, _, term, trunc, _ = env.step("CHECK_HISTORY")
                    self.assertFalse(term or trunc)
                    statuses = [r["status"] for r in obs["rows"]]
                    if statuses == ["confirmed"]:
                        env.step("FINISH")
                        break
                    if not statuses:
                        env.step("SUBMIT")
                self.assertTrue(env.audit()["strict_success"])


if __name__ == "__main__":
    unittest.main()
