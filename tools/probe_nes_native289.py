# SPDX-License-Identifier: MIT
"""Actual M4 producer; intercepted packet sink is an oracle test, not live ACK."""
import argparse,binascii,json,struct
from pathlib import Path
from probe_nes_live287 import ARM
from probe_nes_arm264 import plans
from probe_nes_decode280 import records,chunks
from unicorn import UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_PC,UC_ARM_REG_LR
from nes_delta231 import BASE,sha


class Producer(ARM):
    def __init__(self,*args):
        self.packets=[];self.fixture_reads=0;self.fail_at=None
        super().__init__(*args)
        self.uc.hook_add(UC_HOOK_MEM_READ,self.fixture,begin=0x20010000,end=0x20017fff)
    def fixture(self,*args):self.fixture_reads+=1
    def hook(self,uc,address,size,user):
        if address==(self.symbols['dispatch289']&~1):
            self.instructions+=1;p=uc.reg_read(UC_ARM_REG_R0);n=uc.reg_read(UC_ARM_REG_R1)
            assert 16<=n<=256;self.packets.append(bytes(uc.mem_read(p,n)))
            uc.reg_write(UC_ARM_REG_R0,int(self.fail_at!=len(self.packets)));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
        super().hook(uc,address,size,user)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--last',type=int,default=975);a=ap.parse_args()
    d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);elf=a.source/'output.elf';arm=Producer(elf,None)
    for name in ('reset259','reset285','reset280'):arm.call(name,[])
    arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes());arm.uc.mem_write(0x20010000,b'\xa5'*32768)
    _,groups=plans();rows=[];guards=[]
    word=lambda n:struct.unpack('<I',arm.uc.mem_read(arm.symbols[n],4))[0]
    def normalized(p):return p[:16]+b'\0'*4 if p[0]==7 else p
    def save():return bytes(arm.uc.mem_read(0x20000000,0x40000)),arm.uc.context_save(),len(arm.packets)
    def restore(x):arm.uc.mem_write(0x20000000,x[0]);arm.uc.context_restore(x[1]);del arm.packets[x[2]:];arm.fail_at=None
    for f in range(905,a.last+1):
        for b in chunks(records(BASE/f'probes/nes-joint284/test04/frame{f}.records')):
            arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
        for name in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286'):assert arm.call(name,[])
        for _ in range(34):
            ok=arm.call('next_step286',[]);assert ok
            if ok==2:break
        else:raise AssertionError('unbounded planner')
        assert bytes(arm.uc.mem_read(arm.symbols['output285'],word('output_size285')))==(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes()
        at=len(arm.packets);snap=save()
        if f in (905,907):
            assert not arm.call('commit285',[]);assert bytes(arm.uc.mem_read(0x20000000,0x30000))==snap[0][:0x30000];guards.append([f,'producer not staged cannot commit'])
            restore(snap);assert arm.call('prepare289',[]);arm.fail_at=len(arm.packets)+2;assert not arm.call('produce289',[]) and not arm.call('commit285',[]);guards.append([f,'failed packet cannot commit'])
            restore(snap);arm.call('stop286',[]);assert not arm.call('prepare289',[]) and not arm.call('commit285',[]);guards.append([f,'STOP rejects production and commit']);restore(snap)
        before=arm.instructions
        assert arm.call('prepare289',[]) and arm.call('produce289',[])
        emitted=arm.packets[at:];expected=groups[f-904]
        assert list(map(normalized,emitted))==list(map(normalized,expected)),('native packets',f,[(p[0],len(p)) for p in emitted],[(p[0],len(p)) for p in expected])
        cost=arm.instructions-before
        assert arm.call('commit285',[])
        row=dict(frame=f,packets=len(emitted),bytes=sum(map(len,emitted)),producer_instructions=cost,fixture_reads=arm.fixture_reads)
        rows.append(row);(d/f'frame{f}.packets').write_bytes(b''.join(len(p).to_bytes(2,'little')+p for p in emitted));print(json.dumps(row),flush=True)
    assert not arm.fixture_reads
    result=dict(passed=True,frames=rows,guards=guards,ELF_sha256=sha(elf),script_sha256=sha(Path(__file__)),stack_observed=0x2003f000-arm.low_sp,fixture_reads=0,actual_ACK=False,scope=__doc__)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
