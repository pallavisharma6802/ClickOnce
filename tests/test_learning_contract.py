"""Learning/data contracts; algorithms are not implemented at the planning stage.

Expected API:
make_manifest(split, count) -> list of {seed, scenario, delay}
QLearner(alpha, gamma, seed); update(state, action, reward, next_state,
terminated, truncated); values(state); act(observation); save(path); load(path).
The learner may maintain public action memory internally. It receives no audit.
"""
import importlib
import inspect
import tempfile
from pathlib import Path
import unittest


class LearningContract(unittest.TestCase):
    def test_split_seeds_are_disjoint(self):
        make = importlib.import_module("click_once.experiment").make_manifest
        seeds = {s: {r["seed"] for r in make(s, 100)} for s in ("train", "validation", "test")}
        self.assertFalse(seeds["train"] & seeds["validation"])
        self.assertFalse(seeds["train"] & seeds["test"])
        self.assertFalse(seeds["validation"] & seeds["test"])

    def test_manifest_reproducible_and_balanced(self):
        make = importlib.import_module("click_once.experiment").make_manifest
        a, b = make("test", 100), make("test", 100)
        self.assertEqual(a, b)
        from collections import Counter
        self.assertEqual(sorted(Counter(r["scenario"] for r in a).values()), [20]*5)

    def test_invalid_split_rejected(self):
        make = importlib.import_module("click_once.experiment").make_manifest
        with self.assertRaises(ValueError):
            make("test_used_for_training", 100)

    def test_q_update_uses_reward_and_terminal_mask(self):
        cls = importlib.import_module("click_once.learning").QLearner
        learner = cls(alpha=0.5, gamma=0.9, seed=1)
        learner.update("s", 0, 1.0, "next", terminated=True, truncated=False)
        self.assertAlmostEqual(learner.values("s")[0], 0.5)

    def test_checkpoint_roundtrip_preserves_learned_values(self):
        cls = importlib.import_module("click_once.learning").QLearner
        learner = cls(alpha=0.5, gamma=0.9, seed=1)
        learner.update("s", 0, 1.0, "next", terminated=True, truncated=False)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"checkpoint.json"
            learner.save(path)
            loaded = cls.load(path)
        self.assertEqual(list(learner.values("s")), list(loaded.values("s")))

    def test_inference_accepts_public_observation_only(self):
        cls = importlib.import_module("click_once.learning").QLearner
        parameters = inspect.signature(cls.act).parameters
        self.assertEqual(set(parameters), {"self", "observation"})
        self.assertFalse(any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()))
