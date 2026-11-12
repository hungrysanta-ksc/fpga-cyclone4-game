# SPDX-License-Identifier: MIT
"""Exercise linked 739 issue order and failure propagation with mock transport endpoints."""
import argparse
import json
from pathlib import Path
from check_nes_deadline719 import Deadline
from check_nes_game478 import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1
from nes_raw506 import sha


class Probe(Deadline):
    case=None
    def hook(self,u,at,size,user):
        reject=False
        if self.case=='interrupted_progress' and at==self.syms.get('nes_plan200_progress'):
            reject=True
        if self.case=='bad_oam' and at==self.callback:
            reject=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),2))==bytes((9,4))
        if at==self.syms.get('nes_window184_through'):
            self.through+=1
            # This fixture has instant checked receipt unless specifically rejected.
            u.reg_write(UC_ARM_REG_R0,int(self.case!='bad_through'))
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        if reject:
            self.injected=True
            u.reg_write(UC_ARM_REG_R0,0)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        super().hook(u,at,size,user)


def check(src, single, case):
    m=Probe(src,'normal')
    m.case=case
    m.clock719=10000000
    m.test_sink=sink=0x20015800
    window=m.window719=0x20016b00
    plan=0x20016300
    m.heads=[];m.reasons=[]
    m.samples=m.drains=m.stop_at=m.bad_drain=m.through=0
    m.event719=m.injected=False
    m.reject_final=case=='bad_final'
    def fields(address,typ,**items):
        for key,(value,width) in items.items():
            m.put(address,typ,key,value,width)
    fields(sink,'nes_native_sink165',serial=(5,4),generation=(957,2),displayed=(1,1),state=(1,1),
           plan=(plan,4),enqueue=(m.callback|1,4),exchange=(m.callback|1,4),
           ack635=(3|(4<<32),8),obj_next=(int(case=='sent'),2))
    fields(plan,'nes_plan200',window=(window,4),guard=(m.guard|1,4),
           bank_history=(0 if case=='cold' else 2,1),bulk_pending=(1,1),bulk_until=(17,2))
    mask=(1<<24)-1
    shift={'first_page':0,'end_page':40,'cross_page':18}.get(case,32)
    if case=='short':mask>>=1
    fields(m.resident,'nes_resident211',prepared=(1,1),open=(1,1),serial=(5,4),
           generation=(957,2),displayed=(1,1),map_upload=(mask<<shift,8))
    fields(m.video,'nes_native_video165',valid=(1,1),generation=(957,2),bg_count=(1,2),
           obj_count=(32,2),hdma_size=(21,2),display_mask=(0x1e,1))
    dirty=0x3fe0 if case!='split_obj' else 0x6c
    for key in ('used','dirty'):
        m.u.mem_write(m.resident+m.layout['nes_resident211'][key]+128,dirty.to_bytes(16,'little'))
    if case=='palette_changed':
        m.u.mem_write(m.video+m.layout['nes_native_video165']['cgram'],bytes([42]))
    ok=bool(m.call('nes_sink212_seal',[sink,m.video,m.resident]))
    assert ok==(case not in ('interrupted_progress','bad_oam','bad_final','bad_through'))
    assert m.get(sink,'nes_native_sink165','ack635',4)==(5 if ok else 3)
    if ok:
        sections=[h[1] for h in m.heads]
        early=case not in ('cold','short','cross_page','sent','palette_changed') and not (single and case=='split_obj')
        assert (sections.index(4)<sections.index(2))==early,(case,sections)
        assert sum(h[:2]==bytes((9,4)) for h in m.heads)==int(case!='palette_changed')
        assert m.heads[-1][0]==3
    elif case!='bad_final':
        assert not any(h[0]==3 for h in m.heads)
        assert m.injected or (case=='bad_through' and m.through==1)
    m.call('nes_sink165_reset',[sink,m.callback|1,0])
    assert m.get(sink,'nes_native_sink165','ack635',8)==0
    return case


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path);p.add_argument('out',type=Path);p.add_argument('--single',action='store_true')
    a=p.parse_args()
    cases=['normal','first_page','end_page','cross_page','short','cold','sent','split_obj','palette_changed',
           'interrupted_progress','bad_oam','bad_final']
    if a.single:cases.append('bad_through')
    results=[check(a.src,a.single,c) for c in cases]
    a.out.write_text(json.dumps(dict(cases=results,firmware=sha(a.src/'obj-nes-100/firmware.stm')),indent=2)+'\n')
