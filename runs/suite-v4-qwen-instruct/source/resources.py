"""Resource guard observes only this process tree; no unrelated process kills."""
import csv
import os
import platform
import signal
import subprocess
import threading
import time
from pathlib import Path

class PressureGate:
    def __init__(self):self.critical=0
    def sample(self,level):
        if level<0:return True
        self.critical=self.critical+1 if level>=4 else 0
        return self.critical>=2

def pressure():
    if platform.system()!='Darwin':return 0
    try:
        r=subprocess.run(['sysctl','-n','kern.memorystatus_vm_pressure_level'],capture_output=True,text=True,timeout=3)
        return int(r.stdout.strip()) if r.returncode==0 else -1
    except (subprocess.TimeoutExpired,OSError,ValueError):return -1

class ResourceGuard:
    def __init__(self,output):
        self.output=Path(output);self.stop=threading.Event();self.gate=PressureGate()
    def __enter__(self):
        self.output.mkdir(parents=True,exist_ok=True)
        self.thread=threading.Thread(target=self.monitor,daemon=True);self.thread.start();return self
    def monitor(self):
        import psutil
        with (self.output/'resources.csv').open('w') as f:
            w=csv.writer(f);w.writerow(['unix_time','pressure','process_tree_rss_bytes','system_available_bytes','system_swap_bytes'])
            while not self.stop.is_set():
                proc=psutil.Process()
                rss=proc.memory_info().rss
                for child in proc.children(recursive=True):
                    try:rss+=child.memory_info().rss
                    except psutil.Error:pass
                level=pressure();w.writerow([time.time(),level,rss,psutil.virtual_memory().available,psutil.swap_memory().used]);f.flush()
                if self.gate.sample(level):
                    (self.output/'memory_stop.txt').write_text('Stopped: two critical pressure samples or unavailable pressure monitor. No automatic restart.\n')
                    os.kill(os.getpid(),signal.SIGINT);return
                self.stop.wait(3)
    def __exit__(self,*args):self.stop.set();self.thread.join(timeout=4)
