# SPDX-License-Identifier: MIT
"""Actual MCU/SD/guard/return code; FPGA replies and board/timer MMIO modeled."""
from pathlib import Path
import argparse,json,shutil,subprocess,re
from nes_display138 import adapt,fixture
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.baseline/'nes-run136/evidence';o=a.out;assert not o.exists();o.mkdir(parents=True)
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/run136-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 for n,h in pins.items():
  if n.startswith('host05/') and Path(n).suffix in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:
   assert sha(e/n)==h;d=o/n[len('host05/'):];d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d)
 adapt(o,a.baseline);(o/'fixture.nes').write_bytes(fixture(a.baseline))
 def edit(n,old,new):
  f=o/n;f.write_text(once(f.read_text(encoding='utf8'),old,new),encoding='utf8',newline='\n')
 for n in ['card.c','config097_card.inc','host109.c']:
  f=o/n;s=f.read_text(encoding='utf8')
  for x,y in [('NES136','NES138'),('NES RUN 136.nh1','NES SCREEN 138.nh1'),('nes-progress-136','nes-progress-138'),('nes-run-last-136','nes-screen-last-138'),('run136.nes','screen138.nes'),('fpga_n136.bi3','fpga_n138.bi3')]:s=s.replace(x,y)
  f.write_text(s,encoding='utf8',newline='\n')
 edit('platform.c','0xd3:0xd4','0xd4:0xd5');edit('platform.c','identity_fault==5?0x54:fault==SPI_ID?0:0x59','identity_fault==5?0x59:fault==SPI_ID?0:0x5a')
 edit('platform.c','static unsigned run_case136,','static unsigned display_releases138,display_holds138,display_fault138;\nstatic unsigned long long display_begin138,display_end138;\nstatic unsigned run_case136,')
 edit('platform.c','ns+=(unsigned long long)v*1000;', '''ns+=(unsigned long long)v*1000;
 if(display_releases138&&!reset_held&&!display_fault138&&run_case136>=8&&(run_case136==14||observe_count136>=2)){
  display_fault138=1;
  switch(run_case136){
   case 8:reset_held=1;mock_a.IDR&=~1u;break;
   case 9:irq=1;break;
   case 10:sd_offload=1;break;
   case 11:nes_return_log_allow(true);break;
   case 12:done=0;break;
   case 13:nes_return_fail(NES_DIAG_TIMER);break;
   case 14:reset_held=1;mock_a.IDR&=~1u;break;
   case 15:nes_cf86_finish094();break;
  }
 }''')
 edit('platform.c','case NES_ROM_STOP:stop_count++;','case NES_ROM_STOP:assert(reset_held);stop_count++;')
 edit('platform.c','assert(!irq && reset_held);','assert(!irq && (reset_held||(display_releases138&&!display_holds138)));')
 edit('platform.c','if(tx[0]==0x70){assert(bits==64);','if(!reset_held)assert(tx[0]==0x70);\n if(tx[0]==0x70){assert(bits==64);')
 edit('host109.c','if(!v){assert(!irq&&!nes_return_failed());release097++;', '''if(configs==1){
  if(!v){display_releases138++;display_begin138=ns;assert(start_count136==1&&flags==0x86&&!irq&&!nes_return_failed());}
  else if(display_releases138&&!display_holds138){display_holds138++;display_end138=ns;}
 }
 if(!v){assert(!irq&&!nes_return_failed());if(configs!=1)release097++;''')
 # Avoid historical case5 menu-corruption setup: this case tests STOP rejection.
 edit('host109.c','if(scenario098==5)menu097[100]^=1;','/*138 Case5 is STOP rejection, not menu corruption. */')
 edit('host109.c','run_case136==1||run_case136==4||run_case136==5||run_case136==7','run_case136==1||run_case136==4||run_case136==5||run_case136==7||run_case136>=8')
 edit('host109.c','if(run_case136==1||run_case136==7)assert(!start_count136&&!begin_count);','if(run_case136==1||run_case136==7)assert(!start_count136&&!begin_count&&!display_releases138);\n  else assert(display_releases138==1&&display_holds138==1);')
 edit('host109.c','assert(observe_count136==19);','assert(observe_count136==203);\n assert(display_releases138==1&&display_holds138==1&&display_end138-display_begin138>=10000000000ull);')
 edit('host109.c','nes_run136.last==1600&&nes_run136.stopped==1600','nes_run136.last==20000&&nes_run136.stopped==20000')
 edit('host109.c','void assert_not_run136(void){assert(flags!=0x86);}','void assert_not_run136(void){assert(flags!=0x86&&(!display_releases138||display_holds138));}')
 sources=['card.c','host109.c','printf103.c','linked109-css.c','linked112-checkpoint.c']+['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')[-5000:]
 results=[]
 for case in range(16):
  log=o/f'case-{case}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),str(case),'0',*[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  t=log.read_text(errors='replace');assert not r.returncode and 'PASS136' in t,(case,r.returncode,t[-4000:])
  records=(o/'checkpoint-sectors.txt').read_bytes();(o/f'case-{case}-records.txt').write_bytes(records)
  stages=re.findall(rb'stage=([A-Z_]+)',records)
  if case in [0,2,3,6]:
   assert 'PASS109' in t
   for st in [b'DISPLAY_NEXT',b'DISPLAY_STOPPED',b'BASE_DONE',b'MENU_PREPARED']:assert st in stages,st
   (o/f'case-{case}-logical.txt').write_bytes((o/'entry-logical.txt').read_bytes())
  else:assert b'DISPLAY_STOPPED' not in stages and b'BASE_DONE' not in stages
  results.append(dict(case=case,log_sha256=sha(log),records=len(stages)))
  print('PASS138 host',case,flush=True)
 (o/'result.json').write_text(json.dumps(dict(cases=results,actual_mcu_source=True,fpga_response_model=True,physical=False),indent=2)+'\n',encoding='utf8')
 shutil.copy2(__file__,o/'executed-test138.py')
if __name__=='__main__':main()
