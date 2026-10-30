# SPDX-License-Identifier: MIT
"""Prove error13 can propagate from OBJ writer failure, not only slot capacity.

Actual485 linked M4 receiver/planner on one pinned historical frame. Writer
failure and SPI completion are models; this does not recreate the physical
deadline instant. Strict log-classification negatives retain fault rejection.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import struct
from check_nes_game478 import Machine,encode,sha
from analyze_nes_supply485_hardware import analyse
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR


class AbortOBJ(Machine):
    def hook(self,u,at,size,user):
        if at==getattr(self,'writer',0):
            q=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R2),40))
            if q[6]==1:
                self.failed_OBJ=True
                u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','dataset','reference','raw','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    reference=json.loads((a.reference/'result.json').read_text(encoding='utf8'))
    files=[a.dataset/f'frame905.{ext}' for ext in ['geometry','raw']]
    for q in files:assert sha(q)==reference['input_sha256'][q.name]
    geometry,raw=[q.read_bytes() for q in files];packets,_,_=encode(geometry,raw,905)
    nums=list(map(int,re.search(r'\{(.*?)\}',(a.arm/'nes_palette165.inc').read_text(encoding='utf8'),re.S)[1].split(',')))
    palette=struct.pack('<64H',*nums)
    control=Machine(a.arm,palette).frame(packets,geometry,raw,905,1)
    expected=json.loads((a.reference/'frame905.json').read_text(encoding='utf8'))['candidate']
    assert control['state_sha256']==expected['state_sha256'] and control['plans']==expected['plans']
    m=AbortOBJ(a.arm,palette)
    try:m.frame(packets,geometry,raw,905,1)
    except AssertionError as e:assert str(e)=='planner'
    else:raise AssertionError('OBJ abort was not propagated')
    error=m.u.mem_read(m.video+m.layout['nes_native_video165']['error'],1)[0]
    slots=int.from_bytes(m.u.mem_read(m.resident+m.layout['nes_resident211']['obj_slots'],2),'little')
    assert m.failed_OBJ and error==13 and slots==1
    assert analyse(a.raw,485)['termination_class']=='deadline_during_OBJ_emit'
    negatives=[]
    for key,value in [('native_result','5'),('plan_error','0'),('native_video_error','14'),('sink_window_error','3'),('native_sink_error','2')]:
        d=a.out/key;d.mkdir()
        for q in a.raw.glob('*.txt'):shutil.copyfile(q,d/q.name)
        q=d/'nes-game-last-mmc485.txt';s=q.read_text(encoding='utf-8-sig')
        s,n=re.subn(rf'(?m)^{key}=.*$',f'{key}={value}',s);assert n==1
        q.write_text(s,encoding='utf8',newline='\n')
        try:analyse(d,485)
        except AssertionError:negatives.append(key)
        else:raise AssertionError('Unexpected failure accepted:'+key)
    r={'passed':True,'scope':__doc__,'firmware_SHA256':sha(a.arm/'obj-nes-100/firmware.stm'),
       'control_full_state_and_plans_equal':True,'forced_OBJ_writer_failure_error':error,
       'OBJ_slots_at_failure':slots,'OBJ_capacity':128,'negative_log_cases':negatives,
       'physical_failure_instant_replayed':False}
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(r))
