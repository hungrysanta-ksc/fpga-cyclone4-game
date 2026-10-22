# SPDX-License-Identifier: MIT
"""Run the existing C planner on Cortex-M4, exposing its committed-input gate.

No live SPI/IRQ timing claim: baseline284 already includes output serialization,
IRQ and ROM. The new planner cost is separately identified, not double charged.
"""
import argparse,csv,json,shutil,struct,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ARM
from elftools.elf.elffile import ELFFile
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1


class Planner(ARM):
    def __init__(self,*a):
        self.events=[];self.helper_instructions=0;self.helper_ranges=[]
        with a[0].open('rb') as fp:
            elf=ELFFile(fp)
            for symbol in elf.get_section_by_name('.symtab').iter_symbols():
                if symbol.name in ('memcpy','memset','memcmp','memmove'):
                    start=symbol['st_value']&~1;self.helper_ranges.append((start,start+symbol['st_size']))
        super().__init__(*a)
    def hook(self,uc,address,size,user):
        if any(start<=address<end for start,end in self.helper_ranges):self.helper_instructions+=1
        if address==(self.symbols['trace259']&~1):
            self.events.append(dict(instructions=self.instructions,kind=uc.reg_read(UC_ARM_REG_R0),value=uc.reg_read(UC_ARM_REG_R1)))
        super().hook(uc,address,size,user)
    def word(self,name):return struct.unpack('<I',self.uc.mem_read(self.symbols[name],4))[0]


def build(d):
    old=BASE/'probes/nes-wholepath247/jointdecode-host01';pins={}
    for p in old.iterdir():
        if p.suffix in ('.h','.inc') or p.name in ('nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_delta231.c'):
            shutil.copyfile(p,d/p.name);pins[str(p)]=sha(p)
    shutil.copyfile(ROOT/'tools/nes_planner285.c',d/'nes_planner285.c')
    (d/'stubs.s').write_text('.syntax unified\n.thumb\n.global io259,trace259\n.thumb_func\nio259:\n bx lr\n.thumb_func\ntrace259:\n bx lr\n')
    (d/'layout.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) *(.rodata*) } . = 0x20000000; .data : { *(.data*) } .bss : { *(.bss*) *(COMMON) } }')
    tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
    lib=tool.parent/'lib/gcc/arm-none-eabi/13.3.1/thumb/v7e-m/nofp/libgcc.a'
    shutil.copyfile(lib,d/'libgcc.a');pins[str(lib)]=sha(lib)
    sources=['nes_planner285.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_delta231.c','stubs.s']
    for name,args in [
      ('gcc',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fstack-usage','-fno-builtin','-nostdlib','-Wl,--gc-sections,-e,reset285','-Wl,-u,load285,-u,begin285,-u,plan285,-u,commit285,-u,layout285,-u,io259','-Wl,-T,layout.ld','-Wl,-Map,planner.map',*sources,'libgcc.a','-o','planner.elf']),
      ('size',['planner.elf']),('objdump',['-dr','planner.elf'])]:
        r=subprocess.run([str(tool/f'arm-none-eabi-{name}.exe'),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        (d/f'{name}.log').write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')
    return pins


def wire(f):
    p=BASE/f'probes/nes-geometry230/rtl02/frame{f}.wire';out=bytearray();widths=[2,1,7,4,7,1,2,8]
    for line in p.read_text().splitlines():
        raw=int(line,16);hi=raw>>64;value=raw&((1<<64)-1)
        k=hi>>29;index=hi&8191;gen=(hi>>13)&65535;n=8 if k==0 and index&4096 else widths[k]
        record=((k<<13)|index).to_bytes(2,'big')+gen.to_bytes(2,'big')+value.to_bytes(8,'big')[-n:]
        out+=bytes([len(record)])+record
    return p,bytes(out)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--last',type=int,default=975);a=ap.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins=build(d)
    arm=Planner(d/'planner.elf',None);arm.call('reset285',[])
    palette=BASE/'probes/nes-delta231/test07/palette.bin';pins[str(palette)]=sha(palette);arm.uc.mem_write(arm.symbols['palette285'],palette.read_bytes())
    layout=[arm.call('layout285',[i]) for i in range(7)];rows=[];guards=[]
    for f in range(905,a.last+1):
        path,data=wire(f);assert len(data)<0x17000;pins[str(path)]=sha(path)
        arm.uc.mem_write(0x20028000,data);assert arm.call('load285',[0x20028000,len(data)])==1,f
        # Clone complete RAM/context so failed early invocations cannot poison
        # the retained baseline. This is a test snapshot, not target storage.
        if f in (905,907,954):
            saved=bytes(arm.uc.mem_read(0x20000000,0x40000));ctx=arm.uc.context_save()
            for state in (1,2,3,5):
                arm.uc.mem_write(0x20000000,saved);arm.uc.context_restore(ctx)
                assert arm.call('begin285',[])==1;before=arm.instructions
                assert arm.call('plan285',[state])==0 and arm.word('calls285')==0
                guards.append(dict(frame=f,state=state,error=arm.word('error285'),instructions=arm.instructions-before))
            arm.uc.mem_write(0x20000000,saved);arm.uc.context_restore(ctx)
        helpers_before=arm.helper_instructions
        before=arm.instructions;assert arm.call('begin285',[])==1;begin=arm.instructions-before
        before=arm.instructions;at=len(arm.events);assert arm.call('plan285',[4])==1,(f,arm.word('error285'))
        cost=arm.instructions-before;events=arm.events[at:];out=bytes(arm.uc.mem_read(arm.symbols['output285'],arm.word('output_size285')))
        expected=BASE/f'probes/nes-joint284/test04/plans{f-904}.bin';pins[str(expected)]=sha(expected);assert out==expected.read_bytes(),('plan bytes',f)
        old=BASE/f'probes/nes-wholepath247/jointdecode-test02/run/expected-{f-904}.bin';pins[str(old)]=sha(old)
        meta=old.read_bytes();v=arm.symbols['video285']
        assert bytes(arm.uc.mem_read(v+layout[0],4096))==meta[:4096]
        assert bytes(arm.uc.mem_read(v+layout[1],512))==meta[4096:4608]
        assert bytes(arm.uc.mem_read(v+layout[2],544))==meta[4608:5152]
        # Paired header: byte arrays follow CGRAM without padding; patch is
        # the first union member and its uint16 sizes align after 2,291 bytes.
        assert layout[2]+544==layout[1] and len(meta)==8570
        bundle=bytes(arm.uc.mem_read(v+layout[1]+512,1121))+bytes(arm.uc.mem_read(v,2291))+bytes(arm.uc.mem_read(v+2292,6))
        assert bundle==meta[5152:],('HDMA/raw material',f)
        helper_cost=arm.helper_instructions-helpers_before
        before_commit=arm.instructions;assert arm.call('commit285',[])==1
        row=dict(frame=f,begin_instructions=begin,plan_instructions=cost,commit_instructions=arm.instructions-before_commit,
            first_plan_instructions=next(e['instructions']-before for e in events if e['kind']==1),
            first_batch_instructions=next(e['instructions']-before for e in events if e['kind']==2),
            callbacks=arm.word('calls285'),plan_bytes=len(out),frozen_CPI1_ms=(begin+cost)/84000,
            local_memory_helper_instructions=helper_cost,optimistic_zero_memory_helper_ms=(begin+cost-helper_cost)/84000)
        rows.append(row);print(json.dumps(row),flush=True)
        (d/f'frame{f}-events.json').write_text(json.dumps(events,indent=2)+'\n')
    with (d/'costs.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    result=dict(passed=True,frames=rows,early_rejects=guards,layout=layout,size=(d/'size.log').read_text(),observed_stack=0x2003f000-arm.low_sp,
        ELF_sha256=sha(d/'planner.elf'),input_hashes=pins,source_hash=sha(ROOT/'tools/nes_planner285.c'),script_hash=sha(Path(__file__)),
        metadata_bytes_per_frame=8570,full_RUN=False,new_schedule=False,new_RTL=False,new_MAP=False,hardware_cycles=False,
        scope='Unchanged actual M4 planner + resident/dirty + sorted encoding; canonical input fixtures; output trace callback and storage diagnostic only. Local byte-loop memory helpers are charged, not the full firmware libc; zero-helper sensitivity is optimistic, not measured. No new live source/IRQ/SPI schedule.')
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
