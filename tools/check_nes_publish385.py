# SPDX-License-Identifier: MIT
"""ActualM4 publication repair using existing stable current-frame objects.

Component at a separate flash page reuses the referenceELF's real RAM symbols.
Mixed actual precommit/postdisplay RAM models next-source lifetime overlap;
this is not a live early-SPI scheduler or a replacement selectedARM image.
"""
import argparse,binascii,json,os,shutil,struct,subprocess
from pathlib import Path
from check_nes_compact354 import objects
from probe_nes_arm264 import ARM,ELFFile
from probe_nes_decode280 import records,chunks
from nes_delta231 import ROOT,BASE,sha


def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);assert d.as_posix().isascii()
 ref=BASE/'probes/nes-frontier377/joint01';base=ref/'output.elf';syms=objects(base)
 for path in ref.glob('*.h'):shutil.copyfile(path,d/path.name)
 shutil.copyfile(ROOT/'tools/nes_publish385.c',d/'nes_publish385.c')
 names=('input285','resident285','dirty285','source_cancel367','source_error367','raw_groups352','display_epoch352','display_serial352','display_count352')
 (d/'unit.ld').write_text('SECTIONS { . = 0x08010000; .text : { *(.text*) *(.rodata*) } .data : { *(.data*) } .bss : { *(.bss*) } }\n')
 (d/'layout.c').write_text('#include "nes_delta231.h"\nconst unsigned offsets385[]={offsetof(struct nes_native165,generation),offsetof(struct nes_native165,state),offsetof(struct nes_native165,patch_count),offsetof(struct nes_dirty231,generation),offsetof(struct nes_dirty231,epoch),offsetof(struct nes_dirty231,serial),offsetof(struct nes_resident211,open),offsetof(struct nes_resident211,fault)};\n')
 tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
 def run(name,args,log):
  r=subprocess.run([str(tool/name),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);(d/(log+'.log')).write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')[-1000:]
 run('arm-none-eabi-gcc.exe',['-std=c11','-Os','-Wall','-Wextra','-Werror','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-ffunction-sections','-fdata-sections','-fno-builtin','-nostdlib','-Wl,-T,unit.ld','-Wl,-e,publish385','-Wl,-Map,unit.map',*[f'-Wl,--defsym,{n}=0x{syms[n][0]:x}' for n in names],'nes_publish385.c','layout.c','-o','unit.elf'],'build')
 run('arm-none-eabi-size.exe',['unit.elf'],'size');run('arm-none-eabi-objdump.exe',['-dr','unit.elf'],'disassembly')
 with (d/'unit.elf').open('rb') as f:
  elf=ELFFile(f);symbols=elf.get_section_by_name('.symtab');entry=symbols.get_symbol_by_name('publish385')[0]['st_value'];segments=[(s['p_vaddr'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD'];text=symbols.get_symbol_by_name('publish385')[0]['st_size'];offset_at=symbols.get_symbol_by_name('offsets385')[0]['st_value']
  assert all(s is None or s['sh_size']==0 for s in (elf.get_section_by_name('.data'),elf.get_section_by_name('.bss')))
 with base.open('rb') as f:old_text=ELFFile(f).get_section_by_name('.symtab').get_symbol_by_name('publish352')[0]['st_size']
 pre=(ref/'precommit352-3.bin').read_bytes();post=(ref/'causal368-4-2.bin').read_bytes()
 arm=ARM(base,None);arm.uc.mem_write(0x20000000,pre)
 for b in chunks(records(ref/'frame908.records')):
  arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])==1
 # Import the actual current3 metadata after its successfully checked retire.
 for n in ('input285','resident285','dirty285'):
  at,nbytes=syms[n];arm.uc.mem_write(at,post[at-0x20000000:at-0x20000000+nbytes])
 overlap=bytes(arm.uc.mem_read(0x20000000,0x40000));rows=[]
 def fresh():
  x=ARM(base,None);x.uc.mem_map(0x08010000,0x10000)
  for at,data in segments:x.uc.mem_write(at,data)
  x.symbols['publish385']=entry;x.uc.mem_write(0x20000000,overlap);return x
 def word(x,n):return int.from_bytes(x.uc.mem_read(syms[n][0],4),'little')
 old=fresh();old.call('publish352',[]);assert word(old,'display_serial352')==4
 for phase in (0,1,2):
  x=fresh();x.uc.mem_write(syms['receiver280'][0]+21,bytes([phase]));before=x.instructions;assert x.call('publish385',[])==1
  assert (word(x,'display_epoch352'),word(x,'display_serial352'),word(x,'display_count352'))==(1,3,512)
  rows.append(dict(case='nextreceiverphase'+str(phase),instructions=x.instructions-before,observed_component_stack_bytes=0x2003f000-x.low_sp,current_display_serial=3,next_receiver_serial=4,correct=True))
 # Metadata perturbations use offsets exported by the actual C compiler.
 offsets=struct.unpack('<8I',fresh().uc.mem_read(offset_at,32));receiver_at=syms['receiver280'][0]
 for label,offset,data in [('next_raw0',16,b'\0\0'),('next_raw256',16,b'\0\1')]:
  x=fresh();x.uc.mem_write(receiver_at+offset,data);assert x.call('publish385',[])==1 and word(x,'display_count352')==512;rows.append(dict(case=label,correct=True))
 for name in ('source_cancel367','source_error367'):
  x=fresh();x.uc.mem_write(syms[name][0],struct.pack('<I',1));assert x.call('publish385',[])==0 and word(x,'display_epoch352')==0 and word(x,'raw_groups352')==0xffffffff;rows.append(dict(case=name,rejected=True))
 x=fresh();x.call('stop286',[]);assert x.call('publish385',[])==0 and word(x,'display_epoch352')==0;rows.append(dict(case='actualSTOP286',rejected=True))
 for label,obj,off,width in [('current_input_generation','input285',offsets[0],2),('current_input_state','input285',offsets[1],1),('current_patch_count','input285',offsets[2],1),('dirty_generation','dirty285',offsets[3],2),('dirty_epoch','dirty285',offsets[4],4),('dirty_serial','dirty285',offsets[5],4),('resident_open','resident285',offsets[6],1),('resident_fault','resident285',offsets[7],1)]:
  x=fresh();at=syms[obj][0]+off;value=int.from_bytes(x.uc.mem_read(at,width),'little');x.uc.mem_write(at,(value^1).to_bytes(width,'little'));assert x.call('publish385',[])==0 and word(x,'display_epoch352')==0;rows.append(dict(case=label,rejected=True))
 result=dict(passed=True,cases=rows,old_counterexample=dict(displayed=3,old_published=4,new_published=3,old_instructions=old.instructions,observed_component_stack_bytes=0x2003f000-old.low_sp),component_text_bytes=text,replaced_function_text_bytes=old_text,extra_static_RAM_bytes=0,selected_ARM_changed=False,early_scheduler=False,full_IRQ_instruction_race=False,scope=__doc__,pins={str(p):sha(p) for p in (base,ref/'precommit352-3.bin',ref/'causal368-4-2.bin',ref/'frame908.records',ROOT/'tools/nes_publish385.c',ROOT/'tools/check_nes_publish385.py',d/'unit.elf')})
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
