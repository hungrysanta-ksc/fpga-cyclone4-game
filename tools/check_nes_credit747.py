# SPDX-License-Identifier: MIT
"""Run credit, STOP and stale-response cases on the complete linked ARM images."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import check_nes_oam746 as oam
import check_nes_receipt742 as receipt
from check_nes_handoff678 import Handoff,sha,crc
from check_nes_game478 import UC_ARM_REG_R0, UC_ARM_REG_PC, UC_ARM_REG_LR


class Guard(Handoff):
    def setup(self):
        # The previous unit fixture installs a placeholder then each case
        # installs its test callback before sending anything. 747's unused
        # four-argument default adapter was garbage-collected at full link.
        with patch.dict(self.syms,nes_cost474_pause=self.callback):
            super().setup()


def ownership_scope(src,debt=False):
    from unicorn import UC_HOOK_MEM_WRITE
    job=0x20014500
    changes=[]
    class Pending(Guard):
        def setup(self):
            super().setup()
            self.put(self.w,'nes_sink_window184','pending_oam',job,4)
            def write(u,access,address,size,value,context):
                changes.append(value)
            self.u.hook_add(UC_HOOK_MEM_WRITE,write,begin=job+124,end=job+127)
    with patch.object(receipt,'Handoff',Pending):
        cases=('normal','bad_descriptor_crc','bad_receipt_crc') if debt else ('normal','bad_descriptor_crc','bad_receipt_crc','STOP')
        for case in cases:
            changes.clear()
            receipt.check(src,case,True)
            if case in ('normal','STOP'):
                assert len(changes)>=3 and changes[0]==1 and changes[-1]==0 and 0<changes[1]<=21504,(case,changes)
            else:assert not changes,(case,changes)
    return len(cases)


def final_wire(src):
    # Damage every protected bit of one otherwise successful final response.
    # Each exchange starts with exactly one outstanding checked map.
    m=Guard(src,'normal');m.setup()
    w=m.w; job=0x20014500
    last=bytes.fromhex('0202000034000000bd03')
    u=m.u
    u.mem_write(w+m.layout['nes_sink_window184']['last'],last)
    for k,v,n in [('sent',17,2),('ever_sent',1,1),('wait',m.callback|1,4),('pending_oam',job,4)]:
        m.put(w,'nes_sink_window184',k,v,n)
    raw=bytearray.fromhex('00f70200110011')+bytes((0,2))+last[2:]+bytes((0x65,0x9a,0))
    raw[19]=crc(raw[1:19],8,7,0)
    assert len(raw)==20
    for bit in range(-1,152):
        m.put(w,'nes_sink_window184','retired',16,2);m.put(w,'nes_sink_window184','error',0,1)
        u.mem_write(job+124,(1).to_bytes(4,'little'))
        reply=bytearray(raw)
        if bit>=0:reply[1+bit//8]^=1<<(bit%8)
        m.endpoint.exchange=lambda tx,clock:bytes(reply)
        assert bool(m.call('nes_window184_drain',[w,m.q]))==(bit==-1)
        assert m.get(w,'nes_sink_window184','retired',2)==(17 if bit==-1 else 16)
    return 152


def pay_guard(src,case):
    # Isolate send635's lifetime after packet_wire. The full coupled run
    # independently exercises the real nested emitter and SNES queue.
    class Pay(Guard):
        def hook(self,u,pc,size,ctx):
            def ret(ok):
                u.reg_write(UC_ARM_REG_R0,int(ok));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            if getattr(self,'pay_active',False):
                if pc==self.syms['packet_wire']:
                    work=self.get(self.w,'nes_sink_window184','pending_oam',4)
                    assert work and not u.mem_read(work+128,1)[0]
                    u.mem_write(work+128,bytes([int(case!='unowed')]))
                    self.edges.append('offer')
                    ret(case!='send_error');return
                if pc==self.syms['nes_window184_drain'] or pc==self.callback:
                    assert self.get(self.w,'nes_sink_window184','pending_oam',4)==0
                    is_drain=pc==self.syms['nes_window184_drain']
                    self.edges.append('identity' if is_drain else 'input')
                    ret(case!=('bad_receipt' if is_drain else 'STOP'));return
            super().hook(u,pc,size,ctx)
    m=Pay(src,'normal');m.setup()
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    m.put(m.w,'nes_sink_window184','wait',m.callback|1,4)
    m.edges=[];m.pay_active=True
    ok=m.call('send635',[m.s,m.video,1])
    expected=['offer'] if case in ('unowed','send_error') else ['offer','identity'] if case=='bad_receipt' else ['offer','identity','input']
    assert m.edges==expected and bool(ok)==(case in ('unowed','success')),(case,m.edges,ok)
    assert not m.get(m.w,'nes_sink_window184','pending_oam',4)
    return dict(case=case,steps=m.edges,ok=bool(ok))


def run(src,debt=False):
    with patch.object(receipt,'Handoff',Guard):
        receipts=[receipt.check(src,c,True) for c in ('normal','pending','wrap','expired','future','wrong_map',
                  'bad_descriptor_crc','bad_receipt_crc','STOP')]
    credit=[]
    for elapsed in (0,647,40000):
        limits=[]
        class Timed(Guard):
            def put(self,base,kind,name,value,n):
                super().put(base,kind,name,value,n)
                if kind=='nes_sink_window184' and name=='pending_oam' and value:
                    self.job=value
                    self.u.mem_write(value+124,(1).to_bytes(4,'little'))
                    self.clock747=0xfffffff0
            def hook(self,u,pc,size,userdata):
                if hasattr(self,'job') and pc==self.syms['nes_cost471_now']:
                    u.reg_write(UC_ARM_REG_R0,self.clock747&0xffffffff)
                    self.clock747+=elapsed
                    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
                    return
                if hasattr(self,'job') and pc==self.callback:
                    limits.append(int.from_bytes(u.mem_read(self.job+124,4),'little'))
                super().hook(u,pc,size,userdata)
        with patch.object(oam,'Handoff',Timed):
            rows=[oam.check(src,False,c) for c in ('pending','ready','CRC','identity','STOP','bound')]
        assert limits and set(limits)=={max(1,min(21504,elapsed))},(elapsed,limits)
        credit.append(dict(elapsed=elapsed,budget=limits[0],rows=rows))
    for stop in (False,True):
        m=Guard(src,'normal');m.setup()
        if stop:m.endpoint.mode='STOP_after_bulk';m.endpoint.bulk=1
        assert m.call('nes_cost747_pause',[0,m.guard485|1,1,0,647])==int(not stop)
    return dict(repayment=[pay_guard(src,c) for c in ('unowed','success','send_error','bad_receipt','STOP')] if debt else [],scope_cases=ownership_scope(src,debt),rejected_bits=final_wire(src),firmware=sha(src/'obj-nes-100/firmware.stm'),receipt=receipts,credit=credit,guarded_pause=['ready','STOP'])


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('arm','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--debt',action='store_true')
    a=p.parse_args();a.out.write_text(json.dumps(run(a.arm,a.debt),indent=2)+'\n')
