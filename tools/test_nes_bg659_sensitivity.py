"""Sensitivity only: no BG reader latency, original verified bulk/65816 schedule."""
import runpy
from pathlib import Path
from unittest.mock import patch
from nes_raw506 import once
original=runpy.run_module
selected=None

def shortcut(name,*args,**kwargs):
    if name!="test_nes_board611":return original(name,*args,**kwargs)
    path=Path(__file__).with_name(name+".py");s=path.read_text()
    s=once(s,"        hit=False;mode='ROM';delay=0","""        if kind==0 and (selected is None or g in selected):
            link.allocations.append(dict(requested=t,grant=t,response=t))
            link.phases[g].setdefault('cache611',[]).append([kind,addr,t,t,t,'upper_bound'])
            return t
        hit=False;mode='ROM';delay=0""")
    ns=dict(__name__="__main__",__file__=str(path),selected=selected);exec(compile(s,str(path),"exec"),ns);return ns

if __name__=="__main__":
    with patch.object(runpy,"run_module",shortcut):runpy.run_module("test_nes_direct653",run_name="__main__")
