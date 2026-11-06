# SPDX-License-Identifier: MIT
"""Inject failure during the new ARM silence interval, before later publication."""
import argparse
import json
from pathlib import Path
from check_nes_reuse635_arm import Sender
from check_nes_game478 import UC_ARM_REG_R0, UC_ARM_REG_R2, UC_ARM_REG_PC, UC_ARM_REG_LR
from nes_raw506 import sha


class QuietProbe(Sender):
    guard = 0x0807ff90

    def hook(self,u,at,size,user):
        if at == self.guard or at in (self.syms.get('nes_plan200_progress'), self.syms.get('nes_window184_drain')):
            ok = True
            if at == self.guard:
                self.reasons.append(u.reg_read(UC_ARM_REG_R2))
                self.samples += 1
                ok = self.samples != self.stop_at
            if at == self.syms.get('nes_window184_drain'):
                self.drains += 1
                ok = self.drains != self.bad_drain
            u.reg_write(UC_ARM_REG_R0,int(ok))
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        super().hook(u,at,size,user)


def run(arm,after_map=False,receive=False,late=False,blocks=3):
    results = []
    for case in ('normal','under_threshold','bad_credit','interrupted','bad_final'):
        m=QuietProbe(arm,'normal')
        m.heads=[]
        m.test_sink=sink=0x20015800
        plan,window=0x20016300,0x20016b00
        m.samples=m.drains=0
        m.reasons=[]
        interrupt_sample = 5
        if receive:
            interrupt_sample = 39 if late else 2
        m.stop_at = interrupt_sample if case=='interrupted' else 0
        m.bad_drain=(1 if after_map or receive else 2) if case=='bad_credit' else 0
        m.reject_final=case=='bad_final'
        m.u.mem_write(m.data_symbols['nes_cost471_available'],bytes(4))
        for name,value,n in (('serial',48,4),('generation',952,2),('displayed',1,1),('state',1,1),
                             ('plan',plan,4),('enqueue',m.callback|1,4),('exchange',m.callback|1,4),
                             ('ack635',45|(46<<32),8),('obj_next',15 if case=='under_threshold' else 16,2)):
            m.put(sink,'nes_native_sink165',name,value,n)
        for name,value in (('window',window),('guard',m.guard|1)):
            m.put(plan,'nes_plan200',name,value,4)
        if receive:m.put(window,'nes_sink_window184','wait',m.guard|1,4)
        for name,value,n in (('prepared',1,1),('open',1,1),('displayed',1,1),('serial',48,4),('generation',952,2),
                             ('target',1,1),('map_upload',0x7ffff<<32,8)):
            m.put(m.resident,'nes_resident211',name,value,n)
        for name,value,n in (('valid',1,1),('generation',952,2),('bg_count',1,2),('obj_count',16,2),
                             ('hdma_size',21,2),('display_mask',0x1e,1)):
            m.put(m.video,'nes_native_video165',name,value,n)
        passed=m.call('nes_sink212_seal',[sink,m.video,m.resident,4192])
        assert bool(passed)==(case in ('normal','under_threshold')),case
        limit = 40 if late or after_map else 30
        if receive and not late:
            limit = 3
        assert m.samples=={'normal':limit,'under_threshold':0,'bad_credit':0,'interrupted':m.stop_at,'bad_final':limit}[case]
        if receive:
            expected=([0]*(40-blocks) if late else [])+[3]*(blocks if late else 3)
            assert m.reasons==expected[:m.samples]
        final_sent=any(h[0]==3 for h in m.heads)
        assert final_sent==(case not in ('bad_credit','interrupted'))
        history=m.get(sink,'nes_native_sink165','ack635',8)
        assert history==(45|(48<<32) if passed else 45|(46<<32))
        results.append(dict(case=case,guard_calls=m.samples,drains=m.drains,SEAL=final_sent,committed=bool(passed)))
    return dict(firmware=sha(arm/'obj-nes-100/firmware.stm'),cases=results)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','out'):p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--after-map',action='store_true')
    p.add_argument('--receive',action='store_true')
    p.add_argument('--late-receive',action='store_true')
    p.add_argument('--late-blocks',type=int,choices=(1,2,3),default=3)
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a.arm,a.after_map,a.receive or a.late_receive,a.late_receive,a.late_blocks),indent=2)+'\n')
