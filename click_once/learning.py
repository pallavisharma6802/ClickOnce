"""Finite-memory Q-learning. Inference receives public observations only."""
import json
import random
from pathlib import Path
from .env import ACTIONS


def features(observation):
    if set(observation) != {'goal','page','notice','rows','buttons'}:
        raise ValueError('Policy input must contain public observation fields only')
    if observation['notice'] not in ('Ready','Success','Timeout','History refreshed'):
        raise ValueError('Unknown visible notice')
    return (observation['notice'], observation['page'],
            min(2, sum(r['status']=='confirmed' for r in observation['rows'])),
            min(2, sum(r['status']=='pending' for r in observation['rows'])))


class QLearner:
    def __init__(self, alpha=0.15, gamma=0.95, seed=0, memory=True):
        self.alpha, self.gamma, self.seed, self.memory = alpha, gamma, seed, memory
        self.rng = random.Random(seed)
        self.q = {}
        self.reset()

    def reset(self):
        self.last_action = 'START'
        self.seen_pending = False

    def state(self, observation):
        f = features(observation)
        return json.dumps([*f, self.last_action if self.memory else '', self.seen_pending if self.memory else False], separators=(',',':'))

    def values(self, state):
        return self.q.setdefault(state, [0.0]*len(ACTIONS))

    def update(self, state, action, reward, next_state, terminated, truncated):
        # External truncation still bootstraps; task termination does not.
        target = reward + (0 if terminated else self.gamma*max(self.values(next_state)))
        self.values(state)[action] += self.alpha*(target-self.values(state)[action])

    def act(self, observation):
        state = self.state(observation)
        values = self.values(state)
        # Stable deterministic tie-breaking for reproducible inference.
        action = max(range(len(ACTIONS)), key=lambda a: values[a])
        self.remember(observation, action)
        return ACTIONS[action]

    def remember(self, observation, action):
        self.seen_pending |= any(r['status']=='pending' for r in observation['rows'])
        self.last_action = ACTIONS[action]

    def save(self, path):
        Path(path).write_text(json.dumps(dict(alpha=self.alpha, gamma=self.gamma, seed=self.seed,
                                             memory=self.memory, q=self.q), sort_keys=True))

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text())
        obj = cls(**{k:data[k] for k in ('alpha','gamma','seed','memory')})
        obj.q = data['q']
        return obj


class Baseline:
    def __init__(self, name, seed=0):
        self.name, self.rng = name, random.Random(seed)
        self.reset()

    def reset(self):
        self.started = False

    def act(self, observation):
        features(observation)
        if self.name == 'random':
            return self.rng.choice(ACTIONS)
        if not self.started:
            self.started = True
            return 'SUBMIT'
        if self.name == 'naive':
            return 'FINISH' if observation['notice']=='Success' else 'SUBMIT'
        if self.name == 'verify':
            if observation['page'] != 'history': return 'CHECK_HISTORY'
            rows = observation['rows']
            if any(r['status']=='pending' for r in rows): return 'CHECK_HISTORY'
            if len(rows)==1 and rows[0]['status']=='confirmed': return 'FINISH'
            if not rows: return 'SUBMIT'
            return 'FINISH'
        raise ValueError('Unknown baseline')
