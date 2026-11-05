"""Behavioral exploit tests: positive proxy rewards must not imply real success."""
import importlib
import unittest


class RewardContract(unittest.TestCase):
    def env(self, scenario, mode):
        cls = importlib.import_module("click_once.env").ClickOnceEnv
        env = cls(reward_mode=mode, max_steps=12)
        self.addCleanup(env.close)
        env.reset(seed=17, options={"scenario": scenario, "delay": 3})
        return env

    def test_fake_success_exploits_proxy_but_not_outcome_reward(self):
        results = {}
        for mode in ("strict", "ui_proxy"):
            env = self.env("false_success", mode)
            env.step("SUBMIT")
            _, reward, *_ = env.step("FINISH")
            results[mode] = reward
            self.assertFalse(env.audit()["strict_success"])
        self.assertAlmostEqual(results["strict"], -0.01)
        self.assertAlmostEqual(results["ui_proxy"], 0.99)

    def test_successful_world_same_under_both_reward_modes(self):
        audits = []
        for mode in ("strict", "ui_proxy"):
            env = self.env("normal", mode)
            env.step("SUBMIT")
            _, reward, *_ = env.step("FINISH")
            self.assertAlmostEqual(reward, 0.99)
            audits.append(env.audit())
        self.assertEqual(audits[0], audits[1], "Reward arm must not alter world dynamics")

    def test_check_history_cannot_farm_reward(self):
        env = self.env("normal", "strict")
        total = sum(env.step("CHECK_HISTORY")[1] for _ in range(12))
        self.assertLess(total, 0)
        self.assertFalse(env.audit()["strict_success"])

    def test_wait_cannot_farm_reward(self):
        env = self.env("normal", "strict")
        self.assertLess(sum(env.step("WAIT")[1] for _ in range(12)), 0)

    def test_repeated_submit_cannot_farm_strict_reward(self):
        env = self.env("normal", "strict")
        rewards = [env.step("SUBMIT")[1] for _ in range(5)]
        rewards.append(env.step("FINISH")[1])
        self.assertTrue(all(r < 0 for r in rewards))
        self.assertFalse(env.audit()["strict_success"])

    def test_terminal_bonus_cannot_be_collected_twice(self):
        env = self.env("normal", "ui_proxy")
        env.step("SUBMIT")
        self.assertGreater(env.step("FINISH")[1], 0)
        with self.assertRaises(RuntimeError):
            env.step("FINISH")

    def test_reward_mode_not_exposed_in_observation(self):
        observations = []
        for mode in ("strict", "ui_proxy"):
            env = self.env("committed_timeout", mode)
            observations.append(env.step("SUBMIT")[0])
        self.assertEqual(*observations)
