# SPDX-License-Identifier: MIT
"""Actual linked502 SEAL guard deadline; modeled clock/SPI, not physical replay."""
import argparse,json,re,shutil
from pathlib import Path
from check_nes_hardware494_termination import SealDeadline,sha
from analyze_nes_supply485_hardware import analyse,fields
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR
ROOT=Path(__file__).resolve().parents[1]

class GuardDeadline(SealDeadline):
    def __init__(self,src,mode):
        self.after_pending_ticks=0
        super().__init__(src,mode)
    def hook(self,u,at,size,user):
        if self.mode=='guard_deadline' and at==getattr(self,'ticks_cb',0):
            if self.seal_polls:
                self.after_pending_ticks+=1
            # First tick after pending status is the transfer postguard.
            # Expire on the subsequent guard, before another SPI operation.
            u.reg_write(UC_ARM_REG_R0,10 if self.after_pending_ticks>=2 else 0)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','raw','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    firmware=sha(a.arm/'obj-nes-100/firmware.stm')
    assert firmware==json.loads((ROOT/'analysis/capture502-release-verification.json').read_text())['ARM']['firmware_SHA256']
    rows=[]
    for mode in ['normal','guard_deadline','deadline','IO_fault']:
        m=GuardDeadline(a.arm,mode);ok=m.call('nes_sink212_seal',[m.s,m.video,m.resident])
        row=dict(mode=mode,ok=ok,runtime=m.get(m.rt,'nes_native_runtime165','result'),window=m.get(m.w,'nes_sink_window184','error'),sink=m.get(m.s,'nes_native_sink165','error'),displayed=m.get(m.s,'nes_native_sink165','displayed'),resident_displayed=m.get(m.resident,'nes_resident211','displayed'),pending=m.get(m.w,'nes_sink_window184','sent',2)-m.get(m.w,'nes_sink_window184','retired',2),flags=m.get(m.w,'nes_sink_window184','status_flags'),seal_polls=m.seal_polls)
        if mode=='normal':assert ok and row['displayed'] and row['resident_displayed'] and row['runtime']==row['window']==row['sink']==0
        else:
            assert not ok and row['runtime']==(3 if mode=='IO_fault' else 1) and row['window']==(2 if mode=='guard_deadline' else 3) and row['sink']==2
            assert row['displayed']==row['resident_displayed']==0 and row['pending']==1 and row['flags']==3
            before=len(m.calls);assert m.call('nes_sink212_seal',[m.s,m.video,m.resident])==0 and len(m.calls)==before
        rows.append(row)
    assert analyse(a.raw,502)['termination_class']=='deadline_during_SEAL_guard_or_wait_signature'
    cases={'native_result':'3','native_video_error':'14','native_receiver_error':'1','native_sink_error':'3','sink_window_error':'3','plan_error':'2','plan_sent':'0','plan_end':'0','trace_aborts':'1','trace_commits':'1','fault_context_valid':'1','sink_trace_ack_valid':'1','sink_trace_mismatch_hex':'01','sink_window_flags':'2','sink_window_retired':'16293','trace_generation':'695'}
    for key,value in cases.items():
        folder=a.out/key;folder.mkdir()
        for src in a.raw.glob('*.txt'):shutil.copy2(src,folder/src.name)
        dst=folder/'nes-game-last-mmc502.txt';s=dst.read_text();s,n=re.subn(r'^'+key+r'=.*$',key+'='+value,s,flags=re.M);assert n==1;dst.write_text(s)
        try:analyse(folder,502)
        except AssertionError:pass
        else:raise AssertionError('Accepted corrupt signature '+key)
    result=dict(passed=True,firmware_SHA256=firmware,cases=rows,negative_signatures=len(cases),physical_instant_replayed=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(result))
