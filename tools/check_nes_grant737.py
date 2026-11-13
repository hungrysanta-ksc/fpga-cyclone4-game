"""Linked seal issue order on granted, withheld, and interrupted DMA progress."""
import argparse
import json
from pathlib import Path

from check_nes_deadline719 import Deadline
from check_nes_game478 import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1
from nes_raw506 import sha
from check_nes_tail735 import emit


class Probe(Deadline):
    def hook(self, u, at, size, user):
        if at == self.callback and self.reject is not None:
            header = bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1), 16))
            if header[1] == 5 and int.from_bytes(header[10:12], 'little') == self.reject:
                self.rejected = True
                u.reg_write(UC_ARM_REG_R0, 0)
                u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
                return
        super().hook(u, at, size, user)


def check(src, name, mask):
    m = Probe(src, 'normal')
    sink = m.test_sink = 0x20015800
    window = m.window719 = 0x20016b00
    plan = 0x20016300
    m.clock719 = 10000000
    m.event719 = name != 'expiry'
    m.samples = m.drains = 0
    m.reasons, m.heads = [], []
    m.bad_drain = int(name == 'bad_credit')
    m.stop_at = int(name == 'STOP')
    m.reject_final = name == 'bad_final'
    m.reject = {'scroll_fault': 0, 'pad_fault': 21}.get(name)
    m.rejected = False
    m.u.mem_write(m.data_symbols['nes_cost471_available'], (1).to_bytes(4,'little'))
    def fields(addr, kind, values):
        for key, value, width in values:
            m.put(addr,kind,key,value,width)
    fields(sink,'nes_native_sink165',[
        ('serial',5,4),('generation',957,2),('displayed',1,1),('state',1,1),('plan',plan,4),
        ('enqueue',m.callback|1,4),('exchange',m.callback|1,4),('ack635',3|(4<<32),8),
        ('ack_clock719',m.clock719-2795400+200000,4),('obj_next',int(name=='already_sent'),2)])
    fields(plan,'nes_plan200',[('window',window,4),('guard',m.guard|1,4),('bank_history',0 if name=='cold' else 2,1)])
    fields(window,'nes_sink_window184',[('wait',m.guard|1,4),('poll_limit',12,4)])
    m.u.mem_write(window+m.layout['nes_sink_window184']['last'],bytes([2,2])+bytes(8))
    fields(m.resident,'nes_resident211',[('prepared',1,1),('open',1,1),('serial',5,4),
           ('generation',957,2),('displayed',1,1),('map_upload',0x3f<<32,8)])
    fields(m.video,'nes_native_video165',[('valid',1,1),('generation',957,2),('bg_count',1,2),
           ('obj_count',16,2),('hdma_size',21,2),('display_mask',0x1e,1),('patch_count',2,1)])
    for key in ('used','dirty'):
        m.u.mem_write(m.resident+m.layout['nes_resident211'][key]+128,mask.to_bytes(16,'little'))
    m.u.mem_write(m.video+2292,b'\x15\0'*3)
    ok=bool(m.call('nes_sink212_seal',[sink,m.video,m.resident]))
    assert ok==(name not in ('bad_credit','STOP','bad_final','scroll_fault','pad_fault'))
    assert m.get(sink,'nes_native_sink165','ack635',4)==(5 if ok else 3)
    assert m.rejected==(m.reject is not None)
    rows=[(h[1],int.from_bytes(h[10:12],'little')) for h in m.heads]
    assert rows[:2]==[(2,2048),(2,2240)], (name,rows)
    if ok or name=='bad_final':
        assert rows.count((5,0))==rows.count((5,21))==1
        early=name in ('cross_byte','slot0','slot127','all','bad_final')
        assert (rows.index((5,21))<rows.index((4,0)))==early,(name,rows)
    else:
        assert not any(h[0]==3 for h in m.heads)
    m.call('nes_sink165_reset',[sink,m.callback|1,0])
    assert m.get(sink,'nes_native_sink165','ack635',8)==0
    return name


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('arm',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    masks={'cross_byte':0x3fe0,'slot0':1,'slot127':1<<127,'all':(1<<128)-1,'empty':0,
           'two_runs':0x6c,'gap_byte':0x70003,'far_gap':1|(1<<127)}
    for n in ('cold','expiry','already_sent','STOP','bad_credit','bad_final','scroll_fault','pad_fault'):
        masks[n]=0x3fe0
    rows=[check(a.arm,k,v) for k,v in masks.items()]
    raw=[(21,0,0),(871,1,192),(21,2,66),(1121,3,2),(1,7,2048)]
    for scroll,count,zero in raw:
        emit(a.arm,scroll,count,zero)
    a.out.write_text(json.dumps(dict(passed=True,cases=rows,independent_raw=raw,firmware=sha(a.arm/'obj-nes-100/firmware.stm')),indent=2)+'\n')
