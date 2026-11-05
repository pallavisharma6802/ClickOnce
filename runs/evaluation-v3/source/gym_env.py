"""Gymnasium API adapter; Dict/Text observation reflects only visible UI."""
import json
import gymnasium as gym
from gymnasium import spaces
from .env import ClickOnceEnv,ACTIONS

class ClickOnceGym(gym.Env):
    metadata={'render_modes':['ansi']}
    def __init__(self,reward_mode='strict',max_steps=12,render_mode=None):
        self.core=ClickOnceEnv(reward_mode,max_steps)
        self.action_space=spaces.Discrete(4)
        self.observation_space=spaces.Text(max_length=4096,min_length=1,
             charset=''.join(chr(i) for i in range(32,127)))
        self.render_mode=render_mode
    def reset(self,seed=None,options=None):
        super().reset(seed=seed)
        obs,info=self.core.reset(seed,options)
        return json.dumps(obs,sort_keys=True),info
    def step(self,action):
        if not self.action_space.contains(action):raise ValueError('Invalid discrete action')
        obs,r,t,tr,i=self.core.step(ACTIONS[int(action)])
        return json.dumps(obs,sort_keys=True),r,t,tr,i
    def render(self):return json.dumps(self.core.observe(),indent=2)
    def close(self):self.core.close()
