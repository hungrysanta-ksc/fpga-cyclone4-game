# SPDX-License-Identifier: MIT
"""Early H2/BEGIN and closed tile ranges during the actual incremental planner."""
import inspect,shutil
import probe_nes_live289 as old
from nes_stage290 import prepare as native
from nes_joint290 import apply
from nes_delta231 import ROOT,sha,once


def build_rom(d):
    ns=dict(old.__dict__);ns['native']=native
    exec(compile(inspect.getsource(old.build_rom),'build290','exec'),ns);ns['build_rom'](d)


def prepare(*args,**kwargs):
    src,pins=old.prepare(*args,**kwargs);d=args[0];apply(d)
    for n in ('nes_stage290.py','nes_joint290.py','probe_nes_live290.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins


def worker(*args,**kwargs):
    s=inspect.getsource(old.previous.worker)
    s=once(s,'arm.uc.mem_write(0x20010000,blob)',"arm.uc.mem_write(0x20010000,b'\\xa5'*len(blob))")
    s=once(s,"arm.call('seed287',[generation]);ep.checkpoint();", "arm.call('seed287',[generation]);call('start290',[f-904,generation]);ep.checkpoint();")
    s=once(s,"steps=[];prefills=0;last_size=0", "steps=[];prefills=0;last_size=0;early_dma290=0")
    s=once(s,"            ep.checkpoint()", "            call('tiles290',[0]);ep.checkpoint()\n            if ok!=2:early_dma290=sum(p[0]==7 for p in ep.packets[sent:])")
    s=once(s,'row=dict(frame=f,instructions=', 'row=dict(frame=f,early_DMA_descriptors=early_dma290,instructions=')
    ns=dict(old.previous.__dict__);exec(compile(s,'worker290','exec'),ns);return ns['worker'](*args,**kwargs)


def main():
    ns=dict(old.previous.prior.__dict__)
    ns.update(prepare=prepare,build_rom=build_rom,worker=worker,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(old.previous.prior.main),'live290','exec'),ns);ns['main']()


if __name__=='__main__':main()
