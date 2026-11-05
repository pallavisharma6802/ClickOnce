"""Gymnasium screenshot environment for the five-family suite."""
import io,json,string
import numpy as np
from PIL import Image
import gymnasium as gym
from gymnasium import spaces
from .tasks import catalog
from .suite_browser import TaskEpisode
from .screenshot_agent import validate_action

class BrowserTaskEnv(gym.Env):
    metadata={'render_modes':['rgb_array']}
    def __init__(self,max_steps=24):
        self.max_steps=max_steps;self.episode=None;self.ended=True;self.steps=0
        self.action_space=spaces.Text(max_length=4096,min_length=1,charset=string.printable)
        self.observation_space=spaces.Dict(dict(image=spaces.Box(0,255,shape=(820,1120,3),dtype=np.uint8),
            instruction=spaces.Text(max_length=4096,min_length=1,charset=string.printable),
            tabs=spaces.Text(max_length=4096,min_length=1,charset=string.printable),active_tab=spaces.Discrete(4)))
    def reset(self,seed=None,options=None):
        super().reset(seed=seed);self.close();options=options or {};cases=catalog()
        case=options.get('case')
        if case is None:
            wanted=options.get('case_id')
            case=next((c for c in cases if c['id']==wanted),None) if wanted else cases[int(self.np_random.integers(len(cases)))]
        if case is None:raise ValueError('Unknown case')
        self.case=case;self.episode=TaskEpisode(case).__enter__();self.steps=0;self.ended=False
        return self.observe(),{}
    def observe(self):
        self.last_png=self.episode.screenshot()
        return dict(image=np.asarray(Image.open(io.BytesIO(self.last_png)).convert('RGB')),
            instruction=self.case['instruction'],tabs=json.dumps(self.episode.tabs(),ensure_ascii=True),active_tab=self.episode.active)
    def step(self,action):
        if self.ended:raise RuntimeError('Reset before stepping')
        parsed=validate_action(json.loads(action));self.steps+=1;self.last_execution_error=None
        try:self.episode.execute(parsed)
        except (ValueError,KeyError) as exc:self.last_execution_error=str(exc)
        terminated=parsed['action']=='done';truncated=self.steps>=self.max_steps and not terminated
        self.ended=terminated or truncated;reward=-.01
        if self.ended and self.episode.grade()['success']:reward+=1
        return self.observe(),reward,terminated,truncated,{}
    def render(self):return np.asarray(Image.open(io.BytesIO(self.last_png)).convert('RGB'))
    def close(self):
        if self.episode is not None:
            self.episode.__exit__(None,None,None);self.episode=None
        self.ended=True
