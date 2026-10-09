# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
from nes_entry113 import adapt

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--old',action='store_true');p.add_argument('--cases',default='60,61,62,63,64,65,66,67,68,70')
 a=p.parse_args();o=a.out.resolve();assert not o.exists();o.mkdir(parents=True)
 for f in a.baseline.rglob('*'):
  if f.is_file() and f.suffix in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:
   d=o/f.relative_to(a.baseline);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
 if not a.old:adapt(o)
 def edit(n,old,new):
  f=o/n;f.write_text(once(f.read_text(encoding='utf-8'),old,new),encoding='utf-8',newline='\n')
 # Model CMD12 response/R1b, decoded from actual native command GPIO traffic.
 # No claim that this models the whole menu/SD multi-read electrically.
 edit('card.c','cmd_number==17||cmd_number==24','cmd_number==17||cmd_number==24||cmd_number==12')
 edit('card.c','if(cmd_number==24)write_commands++;else read_commands++;','if(cmd_number==24)write_commands++;else if(cmd_number==17)read_commands++;')
 edit('card.c','if(!data_end)return 1;', 'if(cmd_number==12)return !(command_fault&&fault==BUSY_FOREVER);\n if(!data_end)return 1;')
 edit('card.c','cmd_number==24&&write_commands==fault_at','(cmd_number==24&&write_commands==fault_at)||cmd_number==12')
 # Fault options: bad response CRC, no response, busy forever on CMD12.
 f=o/'card.c';f.write_text(f.read_text(encoding='utf-8')+'''
void entry_card113(unsigned n){
 during_blocktrans=n==60?0:n==62?2:n==63?3:1;
 if(n==64)sd_offload=1;
 if(n==65)card_fault096(2,1);
 if(n==66)card_fault096(6,1);
 if(n==67)card_fault096(5,1);
}
void entry_assert113(unsigned n,int old){
 assert(!write_commands); /* FPGA configuration/frame counts checked by host. */
 if(old||n==62||n==63||n==64)assert(!commands);
 else assert(commands==1&&command_kind[1]==12);
 assert(during_blocktrans!=TRANS_NONE);
}
void read_entry113(void){
 FIL file;UINT got=0;char record[513];unsigned sequence=0;
 FILE*out=fopen("entry-logical.txt","wb");assert(out);
 assert(f_open(&file,"/sd2snes/nes-progress-113.txt",FA_READ)==FR_OK);
 assert(f_size(&file)>0&&f_size(&file)%512==0);
 while(f_tell(&file)<f_size(&file)){
  assert(f_read(&file,record,512,&got)==FR_OK&&got==512);record[512]=0;
  unsigned actual;assert(sscanf(record,"NES113 seq=%u",&actual)==1&&actual==sequence++);
  assert(fwrite(record,1,512,out)==512);
 }
 assert(f_close(&file)==FR_OK&&!fclose(out));
}
''',encoding='utf-8')
 edit('host109.c','void dump_checkpoint112(void);','void dump_checkpoint112(void);void entry_card113(unsigned);void entry_assert113(unsigned,int);')
 edit('host109.c','bool run112=nes_menu_diagnostic_run', '''unsigned entry_case113=scenario098;
 entry_card113(entry_case113);
 if(entry_case113==68)RCC->CR|=RCC_CR_CSSON;
 bool run112=nes_menu_diagnostic_run''')
 if not a.old:
  edit('host109.c','"NES VERIFY 094 80.nh1"));','(entry_case113==70?"NES VERIFY 094 80.nh1":"NES ENTRY 113.nh1")));')
  edit('card.c','"NES112 seq="','"NES113 seq="')
 edit('host109.c','if(!run112){assert(checkpoint_fault112);', '''if(!run112){
 assert(entry_case113>=61&&entry_case113<=68);
 assert(!configs&&!frames&&!release097&&nes_return_failed());
 if(entry_case113!=68)entry_assert113(entry_case113,OLD113);
 unsigned ec=card_commands096(),ee=card_edges096();
 assert(!nes_checkpoint112("FORBIDDEN",0,0));
 assert(ec==card_commands096()&&ee==card_edges096());
 printf("PASS113 rejection case=%u old=%u commands=%u error=%u\\n",entry_case113,OLD113,ec,nes_diag_status()->error);return 0;
 }\n if(!run112){assert(checkpoint_fault112);'''.replace('OLD113','1' if a.old else '0'))
 edit('host109.c','assert(configs==2&&!irq&&reset_held&&finishes==1&&check_acks==original_length-16&&!memcmp(loaded,rom+16,original_length-16));', '''if(entry_case113==70){
 assert(configs==2&&finishes==1&&check_acks==original_length-16&&!memcmp(loaded,rom+16,original_length-16));
 }else assert(!configs&&!frames&&!finishes&&!check_acks);
 assert(!irq&&reset_held);scenario098=0;''')
 if not a.old:
  edit('host109.c','void dump_checkpoint112(void);','void read_entry113(void);void dump_checkpoint112(void);')
  edit('host109.c','printf("PASS109 scenario=%u baseline=', '''if(ok){unsigned before113=card_commands096();
 irq=0;nes_diag_begin();read_entry113();nes_diag_leave();irq=1;
 printf("READBACK113 product_commands=%u harness_extra=%u\\n",before113,card_commands096()-before113);
 }
 printf("PASS109 scenario=%u baseline=''')
 sources=['card.c','host109.c','printf103.c','linked109-css.c','linked112-checkpoint.c']+['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')[-4000:]
 results=[]
 for case in map(int,a.cases.split(',')):
  log=o/f'case-{case}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),str(case),'0',*[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  t=log.read_text(errors='replace');assert not r.returncode and ('PASS113' in t or 'PASS109' in t),(case,r.returncode,t[-3000:])
  records=(o/'checkpoint-sectors.txt').read_bytes();(o/f'case-{case}-records.txt').write_bytes(records)
  if a.old or case in [62,63,64,65,66,67]:assert not records
  elif case==68:assert b'CSS_CHECK_NEXT' in records and b'CSS_READY' not in records
  else:
   assert b'ENTRY_SD_READY' in records and b'MENU_PREPARED' in records
   assert (b'ENTRY_ONLY_DONE' in records)==(case!=70)
   if case!=70:assert b'BEGIN_LOAD' not in records
   logical=(o/'entry-logical.txt').read_bytes();assert b'MENU_PREPARED' in logical
   (o/f'case-{case}-logical.txt').write_bytes(logical)
  results.append(dict(case=case,log_sha256=sha(log),records=len(records)//512))
 (o/'result.json').write_text(json.dumps(dict(old=a.old,cases=results,physical=False),indent=2)+'\n',encoding='utf-8')
 shutil.copy2(__file__,o/'executed-test113.py');print('PASS113',len(results),'cases old=',a.old)
if __name__=='__main__':main()
