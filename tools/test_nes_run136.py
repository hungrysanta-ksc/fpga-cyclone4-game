# SPDX-License-Identifier: MIT
"""Actual116 FatFs/MCU/guard/recovery code plus136; external FPGA/SD models."""
from pathlib import Path
import argparse,json,shutil,subprocess,re
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
from nes_run136_mcu import adapt,fixture

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence116','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence116.resolve();o=a.out.resolve();assert not o.exists();o.mkdir(parents=True)
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/base116-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 for f in (e/'host03').rglob('*'):
  if f.is_file() and f.suffix in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:
   assert sha(f)==pins[f.relative_to(e).as_posix()]
   d=o/f.relative_to(e/'host03');d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
 adapt(o);(o/'fixture.nes').write_bytes(fixture())
 def edit(n,old,new):
  f=o/n;f.write_text(once(f.read_text(encoding='utf8'),old,new),encoding='utf8',newline='\n')
 for name in ['card.c','config097_card.inc']:
  f=o/name;s=f.read_text().replace('NES116 seq=','NES136 seq=').replace('nes-progress-116.txt','nes-progress-136.txt').replace('nes-verify-last-094.txt','nes-run-last-136.txt').replace('fine_x.nes','run136.nes').replace('fpga_n86.bi3','fpga_n136.bi3');f.write_text(s,encoding='utf8',newline='\n')
 # Fake FPGA responds through the actual bit-level MCU transfer. No production guard stubs.
 edit('platform.c','static enum fault fault;','static enum fault fault;\nstatic unsigned run_case136,observer_count136,start_count136,observe_count136;')
 edit('platform.c','assert(bits==16||bits==64);frames++;', '''assert(bits==16||bits==64);frames++;
 if(run_case136==0&&(tx[0]==NES_ROM_START||start_count136)){
  FILE *f=fopen("run-commands136.txt",start_count136?"a":"w");assert(f);
  for(unsigned i=0;i<8;i++)fprintf(f,"%02x%c",tx[i],i==7?'\\n':' ');assert(!fclose(f));
 }''')
 edit('platform.c','assert(tx[0]!=NES_ROM_START); /* Also reject accidental legacy E8. */', '''if(tx[0]==0x70){assert(bits==64);for(unsigned i=1;i<8;i++)assert(!tx[i]);observe_count136++;return;}
 assert(tx[0]!=0xe8);''')
 edit('platform.c','case NES_ROM_END:assert(count==total&&!flags);end_count++;flags=2;break;', '''case NES_ROM_END:assert(count==total&&!flags);end_count++;flags=2;break;
  case NES_ROM_START:assert(flags==0x82&&offset==total);start_count136++;flags=0x86;break;''')
 edit('platform.c','if(tx[0]==0xcf)reply[1]=', '''if(tx[0]==0x70){
    if(flags==0x86&&run_case136!=2)observer_count136+=100;
    reply[1]=run_case136==1?0xd3:0xd4;
    reply[2]=flags==0x86?0:1;
    reply[3]=0;
    if(run_case136==3&&start_count136){reply[2]|=2;reply[3]=1;}
    if(run_case136==6&&stop_count)observer_count136++;
    reply[4]=(uint8_t)(observer_count136>>24);reply[5]=(uint8_t)(observer_count136>>16);
    reply[6]=(uint8_t)(observer_count136>>8);reply[7]=(uint8_t)observer_count136;
   }else if(tx[0]==0xcf)reply[1]=''')
 edit('platform.c','unsigned op=scenario094==102?', 'unsigned op=scenario094==101?0x70:scenario094==102?')
 edit('platform.c','case NES_ROM_STOP:stop_count++;if(fault!=STOP_FAILED){flags=0;count=0;}break;', 'case NES_ROM_STOP:stop_count++;if(fault!=STOP_FAILED){if(flags==0x86)flags=2;else {flags=0;count=0;}}break;')
 # An injected RDY drop only starts during RUN, not the initial identity read.
 edit('platform.c','if(tx[0]==op){injected094=1;', 'if(tx[0]==op&&(!run_case136||start_count136)){injected094=1;')
 edit('host109.c','#include "nes_checkpoint112.h"','#include "nes_checkpoint112.h"\n#include "nes_run136.h"')
 h=o/'host109.c';s=h.read_text();start=s.index(' unsigned entry_case113=scenario098;');end=s.index(' /* main begins only after base restoration;',start)
 s=s[:start]+''' unsigned entry_case113=scenario098;run_case136=entry_case113;
 entry_card113(70);scenario098=0;
 if(run_case136==4)scenario094=101;
 if(run_case136==5)fault=STOP_FAILED;
 if(run_case136==7)identity_fault=5;
 assert(!nes_menu_diagnostic_marker((const uint8_t*)"NES VERIFY 094 80.nh1"));
 assert(!nes_menu_diagnostic_marker((const uint8_t*)"NES BASE 116.nh1"));
 assert(nes_menu_diagnostic_marker((const uint8_t*)"NES RUN 136.nh1"));
 bool run112=nes_menu_diagnostic_run((const uint8_t*)"NES RUN 136.nh1");
 if(!run112){
  assert(run_case136==1||run_case136==4||run_case136==5||run_case136==7);
  assert(nes_return_failed()&&!irq&&reset_held&&!release097&&configs==1);
  if(run_case136==1||run_case136==7)assert(!start_count136&&!begin_count);
  if(run_case136==4)assert(injected094&&start_count136==1);
  if(run_case136==5)assert(start_count136==1&&stop_count==1&&!nes_run136.stop_ok);
  unsigned c=card_commands096(),edges=card_edges096(),fr=frames;
  assert(!nes_checkpoint112("FORBIDDEN",0,0));
  assert(c==card_commands096()&&edges==card_edges096()&&fr==frames);
  printf("PASS136 terminal case=%u start=%u commands=%u frames=%u\\n",run_case136,start_count136,c,fr);return 0;
 }
 assert(configs==2&&!irq&&reset_held&&stop_count==1&&start_count136==1);
 assert(finishes==1&&check_acks==original_length-16&&nes_run136.stop_ok);
 assert(observe_count136==19);
 if(run_case136==0)assert(nes_run136.passed&&nes_run136.first==100&&nes_run136.last==1600&&nes_run136.stopped==1600);
 else {assert(!nes_run136.passed);assert(nes_run136.error==(run_case136==2?2:3));}
 printf("PASS136 bounded case=%u first=%u last=%u stopped=%u error=%u\\n",run_case136,nes_run136.first,nes_run136.last,nes_run136.stopped,nes_run136.error);
 scenario098=0;
'''+s[end:];h.write_text(s,encoding='utf8',newline='\n')
 # Guard SD writes against RUN: catches checkpoints accidentally placed inside the active interval.
 edit('card.c','DRESULT disk_write(BYTE d,const BYTE *p,DWORD s,UINT n){','extern void assert_not_run136(void);\nDRESULT disk_write(BYTE d,const BYTE *p,DWORD s,UINT n){\n assert_not_run136();')
 with (o/'host109.c').open('a',encoding='utf8') as f:f.write('\nvoid assert_not_run136(void){assert(flags!=0x86);}\n')
 sources=['card.c','host109.c','printf103.c','linked109-css.c','linked112-checkpoint.c']+['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')[-7000:]
 results=[]
 for case in range(8):
  log=o/f'case-{case}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),str(case),'0',*[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  t=log.read_text(errors='replace');assert not r.returncode and 'PASS136' in t,(case,r.returncode,t[-4000:])
  records=(o/'checkpoint-sectors.txt').read_bytes();(o/f'case-{case}-records.txt').write_bytes(records)
  stages=re.findall(rb'stage=([A-Z_]+)',records)
  if case in [0,2,3,6]:
   assert 'PASS109' in t
   for st in [b'RUN_NEXT',b'RUN_STOPPED',b'BASE_DONE',b'MENU_PREPARED']:assert st in stages,st
   (o/f'case-{case}-logical.txt').write_bytes((o/'entry-logical.txt').read_bytes())
  else:assert b'RUN_STOPPED' not in stages and b'BASE_DONE' not in stages
  results.append(dict(case=case,log_sha256=sha(log),records=len(stages)))
 (o/'result.json').write_text(json.dumps(dict(cases=results,actual_mcu_source=True,fpga_response_model=True,physical=False),indent=2)+'\n',encoding='utf8')
 shutil.copy2(__file__,o/'executed-test136.py');print('PASS136',len(results),'actual MCU/model cases')
if __name__=='__main__':main()
