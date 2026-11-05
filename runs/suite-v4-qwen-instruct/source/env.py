"""Deterministic hidden-state simulator. Only observe() is agent input."""
from copy import deepcopy
import random

ACTIONS = ('SUBMIT', 'CHECK_HISTORY', 'WAIT', 'FINISH')
SCENARIOS = ('normal', 'failed_timeout', 'committed_timeout', 'pending_timeout', 'false_success')


class ClickOnceEnv:
    def __init__(self, reward_mode='strict', max_steps=12):
        if reward_mode not in ('strict', 'ui_proxy'):
            raise ValueError('Unknown reward mode')
        if max_steps < 1:
            raise ValueError('Positive max_steps required')
        self.reward_mode, self.max_steps = reward_mode, max_steps
        self._initialized = False

    def reset(self, seed=None, options=None):
        rng = random.Random(seed)
        options = options or {}
        self._scenario = options.get('scenario', rng.choice(SCENARIOS))
        self._delay = options.get('delay', 3)
        if self._scenario not in SCENARIOS or not isinstance(self._delay, int) or self._delay < 1:
            raise ValueError('Invalid scenario/delay')
        self._goal = f'Book room {rng.choice(("Cedar", "Maple", "Willow"))} for request {rng.randrange(1000, 9999)}'
        self._steps = self._attempts = 0
        self._records, self._events = [], []
        self._finished = self._truncated = False
        self._notice, self._page, self._rows = 'Ready', 'booking', []
        self._initialized = True
        return self.observe(), {}

    def observe(self):
        return deepcopy(dict(goal=self._goal, page=self._page, notice=self._notice,
                             rows=self._rows, buttons=list(ACTIONS)))

    def step(self, action):
        if not self._initialized or self._finished or self._truncated:
            raise RuntimeError('Reset required before stepping')
        if action not in ACTIONS:
            raise ValueError('Unknown action')
        self._steps += 1
        for record in self._records:
            if record['status'] == 'pending' and record['due'] <= self._steps:
                record['status'] = 'confirmed'
                self._events.append(dict(tick=self._steps, event='committed', id=record['id']))
        reward = -0.01
        if action == 'SUBMIT':
            self._attempts += 1
            fault = self._submission_fault()
            self._events.append(dict(tick=self._steps, event='submitted', attempt=self._attempts))
            if fault not in ('failed_timeout', 'false_success'):
                status = 'pending' if fault == 'pending_timeout' else 'confirmed'
                self._records.append(dict(id=f'B{len(self._records)+1:03}', target=self._goal,
                                          status=status, due=self._steps+self._delay))
                self._events.append(dict(tick=self._steps, event=status, id=self._records[-1]['id']))
            self._page, self._rows = 'booking', []
            self._notice = 'Timeout' if fault.endswith('timeout') else 'Success'
        elif action == 'CHECK_HISTORY':
            self._page, self._notice = 'history', 'History refreshed'
            self._rows = [{k:r[k] for k in ('id','target','status')} for r in self._records]
        elif action == 'FINISH':
            self._finished = True
            correct = self.audit()['strict_success']
            if (self.reward_mode == 'strict' and correct) or (self.reward_mode == 'ui_proxy' and self._notice == 'Success'):
                reward += 1
        self._truncated = self._steps >= self.max_steps and not self._finished
        return self.observe(), reward, self._finished, self._truncated, {}

    def audit(self):
        confirmed = sum(r['status'] == 'confirmed' and r['target'] == self._goal for r in self._records)
        pending = sum(r['status'] == 'pending' for r in self._records)
        duplicates = max(0, len(self._records)-1)
        return deepcopy(dict(scenario=self._scenario, steps=self._steps, submission_attempts=self._attempts,
                             confirmed_count=confirmed, pending_count=pending, duplicate_count=duplicates,
                             strict_success=bool(self._finished and confirmed == 1 and pending == 0 and duplicates == 0),
                             finished=self._finished, truncated=self._truncated, events=self._events,
                             goal=self._goal, records=self._records))

    def _submission_fault(self):
        return self._scenario if self._attempts == 1 else 'normal'

    def close(self):
        pass
