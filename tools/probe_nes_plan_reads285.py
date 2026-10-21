# SPDX-License-Identifier: MIT
"""Observe actual ARM raw-material reads before the first plan callback."""
import argparse,json,shutil,struct,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_planner285 import Planner,wire
from probe_nes_decode280 import golden
from elftools.elf.elffile import ELFFile
from unicorn import UC_HOOK_MEM_READ


class Reads(Planner):
    def __init__(self,*a):
        self.track=False;self.raw_at=0;self.raw_end=0;self.read_bytes=set();self.first_raw=None
        super().__init__(*a);self.uc.hook_add(UC_HOOK_MEM_READ,self.read)
    def read(self,uc,access,address,size,value,user):
        if self.track:
            self.read_bytes.update(range(max(address,self.raw_at),min(address+size,self.raw_end)))
    def hook(self,uc,address,size,user):
        from unicorn.arm_const import UC_ARM_REG_R0
        if self.track and address==(self.symbols['trace259']&~1) and uc.reg_read(UC_ARM_REG_R0)==1 and self.first_raw is None:
            self.first_raw=len(self.read_bytes)
        super().hook(uc,address,size,user)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    original=BASE/'probes/nes-joint285/arm04';baseline=json.loads((original/'result.json').read_text());pins={}
    for name in ('nes_native165.h','planner.elf'):
        shutil.copyfile(original/name,d/name);pins[name]=sha(original/name)
    (d/'offsets.c').write_text('#include "nes_native165.h"\nconst unsigned offsets285[]={offsetof(struct nes_native165,raw_pixels),sizeof(struct nes_native165),sizeof(((struct nes_native165*)0)->raw_pixels)};\n')
    gcc=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin/arm-none-eabi-gcc.exe'
    cmd=[str(gcc),'-std=c11','-Os','-mthumb','-mcpu=cortex-m4','-c','offsets.c','-o','offsets.o']
    r=subprocess.run(cmd,cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);(d/'build.log').write_bytes(r.stdout);assert r.returncode==0
    with (d/'offsets.o').open('rb') as fp:
        elf=ELFFile(fp);sym=elf.get_section_by_name('.symtab').get_symbol_by_name('offsets285')[0];sec=elf.get_section(sym['st_shndx']);offsets=struct.unpack('<3I',sec.data()[sym['st_value']:sym['st_value']+12])
    assert offsets[1]==baseline['layout'][3] and offsets[2]==2048
    arm=Reads(d/'planner.elf',None);arm.call('reset285',[]);arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes());rows=[]
    for f in range(905,908):
        _,data=wire(f);arm.uc.mem_write(0x20028000,data);assert arm.call('load285',[0x20028000,len(data)])==1
        _,raw=golden(f);arm.raw_at=arm.symbols['input285']+offsets[0];arm.raw_end=arm.raw_at+len(raw)
        assert bytes(arm.uc.mem_read(arm.raw_at,len(raw)))==raw
        arm.read_bytes=set();arm.first_raw=None;arm.track=True;before=arm.instructions
        assert arm.call('begin285',[])==1;assert arm.call('plan285',[4])==1;cost=arm.instructions-before;arm.track=False
        old=next(r for r in baseline['frames'] if r['frame']==f)
        expected_cost=old['begin_instructions']+old['plan_instructions']
        out=bytes(arm.uc.mem_read(arm.symbols['output285'],arm.word('output_size285')));assert out==(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes()
        assert arm.first_raw==len(raw)==512
        rows.append(dict(frame=f,raw_bytes_before_first_plan=arm.first_raw,raw_bytes_total=len(arm.read_bytes),observed_instructions=cost,
            uninstrumented_instructions=expected_cost,instrumentation_counter_delta=cost-expected_cost,used_for_timing=False))
        assert arm.call('commit285',[])==1
    result=dict(passed=True,frames=rows,compiler_offsets=offsets,input_hashes=pins,script_sha256=sha(Path(__file__)),
        scope='Same ELF and exact plan output; memory observation confirms all512 raw bytes read before first plan. Instruction counter differs under this observation and is NOT used for timing. No early-plan implementation.')
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['frames']))


if __name__=='__main__':main()
