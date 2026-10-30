# SPDX-License-Identifier: MIT
"""Execute linked489 guard2 -> zero-plan callback -> video14 propagation.

Pinned historical capture and modeled guard/SPI, not the physical final instant.
Reject incomplete or transport-fault log signatures rather than waiving code14.
"""
import argparse,json,re,shutil,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,Machine,sha
from check_nes_game478 import encode
from analyze_nes_supply485_hardware import analyse
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR

class AbortZero(ARM):
    deny=False
    failed_zero=False
    def hook(self,u,at,size,user):
        if at==getattr(self,'writer',0):
            q=u.reg_read(UC_ARM_REG_R2)
            assert bytes(u.mem_read(q,40))[6]==2
            self.calls_before_failure=len(self.endpoint.calls)
            self.failed_zero=self.deny=True
            # Tail-call the actual plan service using the existing writer LR.
            u.reg_write(UC_ARM_REG_R0,self.p);u.reg_write(UC_ARM_REG_R1,q)
            u.reg_write(UC_ARM_REG_PC,self.syms['nes_plan200_emit']|1);return
        if at==self.guard485 and self.deny:
            u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if at==getattr(self,'spi',0) and bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),1))[0] in range(0xd0,0xd4):
            Machine.hook(self,u,at,size,user);return
        super().hook(u,at,size,user)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','dataset','reference','raw','baseline-raw','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    reference=json.loads((a.reference/'result.json').read_text())
    paths=[a.dataset/f'frame905.{ext}' for ext in ['geometry','raw']]
    for q in paths:assert sha(q)==reference['input_SHA256'][q.name]
    geometry,raw=[q.read_bytes() for q in paths];packets,_,_=encode(geometry,raw,905)
    nums=list(map(int,re.search(r'\{(.*?)\}',(a.arm/'nes_palette165.inc').read_text(),re.S)[1].split(',')))
    palette=struct.pack('<64H',*nums)
    control=Machine(a.arm,palette).frame(packets,geometry,raw,905,1)
    m=AbortZero(a.arm,'normal');m.setup();m.put(m.s,'nes_native_sink165','generation',905,2);m.u.mem_write(m.lut,palette)
    try:m.frame(packets,geometry,raw,905,1)
    except AssertionError as e:assert str(e)=='planner'
    else:raise AssertionError('Guard rejection was not propagated')
    video=m.u.mem_read(m.video+m.layout['nes_native_video165']['error'],1)[0]
    assert m.failed_zero and video==14 and m.get(m.p,'nes_plan200','error')==2
    assert m.get(m.p,'nes_plan200','sent',2)==0 and not m.get(m.p,'nes_plan200','finished')
    assert m.u.mem_read(m.resident+m.layout['nes_resident211']['fault'],1)[0]==1
    assert not m.u.mem_read(m.resident+m.layout['nes_resident211']['displayed'],1)[0]
    assert len(m.endpoint.calls)==m.calls_before_failure
    assert analyse(a.raw,489)['termination_class']=='deadline_during_plan_emit_signature'
    assert analyse(a.baseline_raw,485)['termination_class']=='deadline_during_OBJ_emit'
    negatives=[]
    for key,value in [('native_result','5'),('plan_error','0'),('native_video_error','15'),
                      ('sink_window_error','3'),('native_sink_error','2'),('native_receiver_error','1'),
                      ('plan_sent','1'),('plan_end','1'),('trace_commits','577'),
                      ('trace_ends','577'),('trace_aborts','1'),('fault_context_valid','1')]:
        d=a.out/key;d.mkdir()
        for q in a.raw.glob('*.txt'):shutil.copyfile(q,d/q.name)
        q=d/'nes-game-last-mmc489.txt';s=q.read_text(encoding='utf-8-sig')
        s,n=re.subn(rf'(?m)^{key}=.*$',f'{key}={value}',s);assert n==1;q.write_text(s,encoding='utf8')
        try:analyse(d,489)
        except AssertionError:negatives.append(key)
        else:raise AssertionError('Unexpected failure accepted:'+key)
    r={'passed':True,'scope':__doc__,'firmware_SHA256':sha(a.arm/'obj-nes-100/firmware.stm'),
       'input_SHA256':{q.name:sha(q) for q in paths},'control_plans':len(control['plans']),
       'actual_plan_error':2,'actual_video_error':video,'sent':0,'displayed':False,'resident_fault':True,
       'SPI_calls_after_guard_failure':len(m.endpoint.calls)-m.calls_before_failure,'negative_log_cases':negatives,
       'previous485_signature_still_accepted':True,'physical_failure_instant_replayed':False}
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
