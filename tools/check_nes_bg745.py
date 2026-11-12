# SPDX-License-Identifier: MIT
"""Exercise the linked section-5 issue delay with a sticky DMA pulse and fault endpoints."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
import check_nes_receipt742 as receipt
from check_nes_game478 import UC_ARM_REG_R0, UC_ARM_REG_R2, UC_ARM_REG_PC, UC_ARM_REG_LR
from check_nes_deadline719 import Deadline
from nes_raw506 import sha


def check(arm,case):
    m=Deadline(arm,'normal')
    m.clock719=10_000_000
    stamp=m.clock719-(2*1397700-200000)
    m.event719=False
    m.heads=[];m.reasons=[];m.drains=m.samples=0
    m.stop_at=2 if case=='STOP' else 0
    m.bad_drain=2 if case=='bad_credit' else 0
    m.reject_final=case=='bad_final'
    sink=m.test_sink=0x20015800
    plan=0x20016300
    window=m.window719=0x20016b00
    def fields(address,kind,values):
        for name,value,width in values:m.put(address,kind,name,value,width)
    m.u.mem_write(m.data_symbols['nes_cost471_available'],(1).to_bytes(4,'little'))
    fields(sink,'nes_native_sink165',[('serial',48,4),('generation',952,2),('displayed',1,1),('state',1,1),
        ('plan',plan,4),('map_next',64,1),('enqueue',m.callback|1,4),('exchange',m.callback|1,4),
        ('ack635',45|(46<<32),8),('ack_clock719',stamp,4)])
    fields(m.resident,'nes_resident211',[('serial',48,4),('generation',952,2),('displayed',1,1),('target',1,1),
        ('prepared',1,1),('open',1,1),('map_upload',(1<<24)-1,8)])
    fields(m.video,'nes_native_video165',[('valid',1,1),('generation',952,2),('bg_count',1,2),('obj_count',16,2),
        ('hdma_size',21,2),('display_mask',0x1e,1)])
    fields(plan,'nes_plan200',[('window',window,4),('guard',m.guard|1,4),('bank_history',2,1),('bulk_valid',1,1)])
    m.u.mem_write(plan+m.layout['nes_plan200']['bulk'],bytes((1,0,32 if case=='other_BG' else 48,0))+bytes(8))
    fields(window,'nes_sink_window184',[('wait',m.guard|1,4),('poll_limit',2 if case=='bound' else 65536,4),
        ('status_flags',10,1)])
    m.u.mem_write(window+m.layout['nes_sink_window184']['last'],bytes((2,2))+bytes(8))
    ok=bool(m.call('nes_sink212_seal',[sink,m.video,m.resident,4192]))
    assert ok==(case in ('normal','other_BG','bound'))
    assert sum(h[:2]==bytes((9,4)) for h in m.heads)==1
    assert all(x==4 for x in m.reasons)
    assert (m.samples==0 if case=='other_BG' else m.samples>=1)
    if case=='bound':assert m.drains==m.samples==2
    if case=='normal':assert 2<m.samples<12
    assert any(h[0]==3 for h in m.heads)==(case not in ('STOP','bad_credit'))
    assert m.get(sink,'nes_native_sink165','ack635',8)==45|((48 if ok else 46)<<32)
    return dict(case=case,callbacks=m.samples,drains=m.drains,committed=ok)


def check_input_order(arm):
    """Bind the original 678 admission check to the first reason-4 callback."""
    sample={}
    class Probe(receipt.Handoff):
        def hook(self,u,at,size,user):
            if at==self.callback and u.reg_read(UC_ARM_REG_R2)==4:
                sample.update(sent=self.get(self.w,'nes_sink_window184','sent',2),
                              retired=self.get(self.w,'nes_sink_window184','retired',2),
                              bulk_pending=self.get(self.p,'nes_plan200','bulk_pending'),
                              SPI=list(self.ops))
            return super().hook(u,at,size,user)
    with patch.object(receipt,'Handoff',Probe):
        try:receipt.check(arm,'pending',True)
        except AssertionError:
            assert sample['sent']>sample['retired'] and not sample['bulk_pending'] and 0xe1 not in sample['SPI']
        else:raise AssertionError('unexpected old admission success')
    return sample


def check_submit_order(arm):
    # Separate diagnostic for the changed callback contract. Keep the original
    # failing callback check above. The latest identity must still be confirmed
    # before the actual OBJ submit, including when input service returns STOP.
    class BeforeDrain(receipt.Handoff):
        def hook(self,u,at,size,user):
            if at==self.callback and u.reg_read(UC_ARM_REG_R2)==4:
                assert not self.get(self.p,'nes_plan200','bulk_pending')
                if self.case=='STOP_after_input':
                    self.endpoint.mode='STOP_after_bulk'
                    self.endpoint.bulk=1
                u.reg_write(UC_ARM_REG_R0,1)
                u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
                return
            if at==self.syms.get('nes_sink195_submit'):
                assert self.get(self.w,'nes_sink_window184','sent',2)==self.get(self.w,'nes_sink_window184','retired',2)
            return super().hook(u,at,size,user)
    with patch.object(receipt,'Handoff',BeforeDrain):
        return [receipt.check(arm,c,True) for c in ('normal','pending','wrap','expired','future',
            'wrong_map','bad_descriptor_crc','bad_receipt_crc','STOP')]


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('arm','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--check-input-order',action='store_true')
    a=p.parse_args()
    result=dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=[check(a.arm,c) for c in
        ('normal','bound','other_BG','STOP','bad_credit','bad_final')])
    if a.check_input_order:
        result['old_reason4_rejection']=check_input_order(a.arm)
        result['submit_boundary']=check_submit_order(a.arm)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
