# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil,subprocess,re
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
from nes_checkpoint112 import adapt

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence109','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--cases',default='0:0');p.add_argument('--geometry96',action='store_true')
 a=p.parse_args();e=a.evidence109.resolve();o=a.out.resolve();assert not o.exists()
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/css109-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prefix='fat32-96-01' if a.geometry96 else 'normal02'
 o.mkdir(parents=True)
 for f in (e/prefix).rglob('*'):
  if f.is_file() and f.suffix in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:
   key=f.relative_to(e).as_posix();assert sha(f)==pins[key],key
   d=o/f.relative_to(e/prefix);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
 adapt(o)
 def edit(n,old,new):
  f=o/n;f.write_text(once(f.read_text(encoding='utf-8'),old,new),encoding='utf-8',newline='\n')
 (o/'linked112-checkpoint.c').write_text('#include "product-output103.h"\n#include "nes_checkpoint112.c"\n',encoding='utf-8')
 edit('host109.c','card_writes096()==5&&writes_at_release098==5','card_writes096()>5&&writes_at_release098==card_writes096()')
 # Inspect the simulated card after the product lifecycle. This helper reads
 # its backing image directly; it never adds product SD traffic after a fault.
 f=o/'card.c';f.write_text(f.read_text(encoding='utf-8')+'''
void dump_checkpoint112(void){
 FILE*f=fopen("checkpoint-sectors.txt","wb");assert(f);
 for(unsigned i=0;i<sectors;i++)if(!memcmp(media+i*512u,"NES112 seq=",11))
  assert(fwrite(media+i*512u,1,512,f)==512);
 assert(!fclose(f));
}
void read_checkpoint112(void){
 FIL file;UINT got=0;char record[513];unsigned sequence=0;
 FILE*out=fopen("checkpoint-file.txt","wb");assert(out);
 assert(f_open(&file,"/sd2snes/nes-progress-112.txt",FA_READ)==FR_OK);
 assert(f_size(&file)>0&&f_size(&file)%512==0);
 while(f_tell(&file)<f_size(&file)){
  assert(f_read(&file,record,512,&got)==FR_OK&&got==512);record[512]=0;
  unsigned actual;assert(sscanf(record,"NES112 seq=%u",&actual)==1&&actual==sequence++);
  assert(fwrite(record,1,512,out)==512);
 }
 assert(f_close(&file)==FR_OK&&!fclose(out));
}
''',encoding='utf-8',newline='\n')
 edit('host109.c','int main(int argc,char **argv){','void dump_checkpoint112(void);\nint main(int argc,char **argv){\n atexit(dump_checkpoint112);')
 # Early SD checkpoint failures should return before a new configuration/IO.
 edit('host109.c','assert(nes_menu_diagnostic_run((const uint8_t*)', 'bool run112=nes_menu_diagnostic_run((const uint8_t*)')
 edit('host109.c','"NES VERIFY 094 80.nh1")));','"NES VERIFY 094 80.nh1"));\n if(!run112){assert(nes_return_failed()&&!irq&&reset_held&&!release097);unsigned c=card_commands096(),edges=card_edges096(),fr=frames;assert(!nes_checkpoint112("FORBIDDEN",0,0));assert(c==card_commands096()&&edges==card_edges096()&&fr==frames);printf("PASS112 early fault error=%u commands=%u\\n",nes_diag_status()->error,c);return 0;}')
 edit('host109.c','#undef printf\nvoid dump_checkpoint112','#include "nes_checkpoint112.h"\n#undef printf\nvoid dump_checkpoint112')
 # Fault options 300.. are SD write rejection at a selected diagnostic phase.
 edit('host109.c','init109();','unsigned checkpoint_fault112=baseline098>=300&&baseline098<400?baseline098-300:0;\n if(checkpoint_fault112){baseline098=0;rtc_mode099=0;}\n init109();')
 edit('host109.c','if(setjmp(nmi_env109))', 'if(checkpoint_fault112)card_phase_fault096(checkpoint_fault112,1,1);\n if(setjmp(nmi_env109))')
 edit('host109.c','if(!run112){assert(', 'if(!run112){assert(checkpoint_fault112);if(first_error096)assert(card_commands096()==first_commands096&&card_edges096()==first_edges096&&frames==first_frames096&&configs==first_configs096);assert(')
 edit('host109.c','void dump_checkpoint112(void);','void dump_checkpoint112(void);void read_checkpoint112(void);')
 edit('host109.c','printf("PASS109 scenario=%u baseline=', '''if(ok){
  unsigned product_commands112=card_commands096();
  irq=0;nes_diag_begin();read_checkpoint112();nes_diag_leave();irq=1;
  printf("READBACK112 product_commands=%u harness_extra=%u\\n",product_commands112,card_commands096()-product_commands112);
 }
 printf("PASS109 scenario=%u baseline=''')
 edit('host109.c','/* main begins only after base restoration;', '''if(scenario098==50){
  nes_return_io_begin();native_ns096+=59000000000ull;
  assert(nes_return_checkpoint_enter112());assert(!nes_return_checkpoint_enter112());
  nes_return_checkpoint_leave112();assert(!nes_return_log_allowed());
  assert(nes_checkpoint112("BUDGET_CHECK",0,0));native_ns096+=2000000000ull;
  assert(!nes_return_io_step()&&nes_return_failed());
  unsigned c=card_commands096(),edges=card_edges096();
  assert(!nes_checkpoint112("FORBIDDEN",0,0));
  assert(c==card_commands096()&&edges==card_edges096());
  printf("PASS112 original60sec budget retained across checkpoint; nested/fault denied\\n");return 0;
 }
 /* main begins only after base restoration;''')
 sources=['card.c','host109.c','printf103.c','linked109-css.c','linked112-checkpoint.c']+['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')[-6000:]
 results=[]
 for i,item in enumerate(a.cases.split(',')):
  case=list(map(int,item.split(':')));log=o/f'case-{i}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),*map(str,case),*[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  text=log.read_text(errors='replace');assert not r.returncode and ('PASS109' in text or 'PASS112' in text),(case,r.returncode,text[-3500:])
  records=(o/'checkpoint-sectors.txt').read_bytes();(o/f'case-{i}-checkpoints.txt').write_bytes(records)
  stages=re.findall(rb'stage=([A-Z_]+)',records)
  if case in [[0,0],[1,0],[2,0],[3,0],[12,0],[13,0]]:
   logical=(o/'checkpoint-file.txt').read_bytes()
   assert len(logical)%512==0 and b'stage=MENU_PREPARED' in logical
   (o/f'case-{i}-file.txt').write_bytes(logical)
   for stage in [b'OPEN_INPUT',b'CONFIG_START',b'CONFIG_READY',b'BEGIN_LOAD',b'LOAD',b'CHECK',b'STOP_START',b'STOP_DONE',b'BASE_START',b'BASE_DONE',b'MENU_COPY_START',b'MENU_PREPARED']:assert stage in stages,stage
   for stage in [b'LOAD',b'CHECK']:
    counts=[int(x) for x in re.findall(rb'stage='+stage+rb' bytes=(\d+)',records)]
    assert 0 in counts and (98304 if a.geometry96 else 81920) in counts,counts
  results.append(dict(case=case,exit=r.returncode,log_sha256=sha(log),checkpoint_records=len(stages),checkpoints_sha256=sha(o/f'case-{i}-checkpoints.txt')))
 shutil.copy2(__file__,o/'executed-test112.py')
 production=['nes_checkpoint112.c','nes_checkpoint112.h','nes_diag_runtime.c','nes_menu_return.c','nes_menu_diagnostic.c','nes_h1_stm32.c']
 (o/'result.json').write_text(json.dumps(dict(cases=results,geometry96=a.geometry96,production_sources={n:sha(o/n) for n in production},physical=False),indent=2)+'\n',encoding='utf-8')
 print('PASS112 integration cases='+str(len(results)))
if __name__=='__main__':main()
