# SPDX-License-Identifier: MIT
"""Actual139 MCU path: frozen context, early STOP, first-vs-stop error separation."""
from pathlib import Path
import argparse,json,shutil,subprocess,re
from nes_fault139 import prepare,edit
from nes_spi_boot import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;prepare(a.baseline,o,'host')
 for n in ['card.c','config097_card.inc','host109.c','platform.c']:
  f=o/n;f.write_text(f.read_text(encoding='utf8').replace('138','139'),encoding='utf8',newline='\n')
 def patch(n,old,new):edit(o,n,old,new)
 patch('platform.c','0xd4:0xd5','0xd5:0xd6')
 patch('platform.c','identity_fault==5?0x59:fault==SPI_ID?0:0x5a','identity_fault==5?0x5a:fault==SPI_ID?0:0x5b')
 patch('platform.c','run_case136>=8&&','run_case136>=8&&run_case136<=15&&')
 patch('platform.c','if(!reset_held)assert(tx[0]==0x70);','if(!reset_held)assert(tx[0]>=0x70&&tx[0]<=0x72);\n if(tx[0]==0x71||tx[0]==0x72){assert(bits==64);return;}')
 patch('platform.c','if(tx[0]==0x70){\n    if(flags',"""if(tx[0]==0x71||tx[0]==0x72){
    const uint64_t ctx=(1ull<<62)|(1ull<<61)|(1ull<<58)|(7ull<<47)|(0x200456ull<<25)|0x8123ull;
    reply[1]=run_case136==16?0xd5:0xd6;reply[2]=run_case136==17?0:1;
    if(tx[0]==0x71)for(unsigned i=0;i<5;i++)reply[3+i]=(uint8_t)(ctx>>(56-8*i));
    else {reply[3]=ctx>>16;reply[4]=ctx>>8;reply[5]=ctx;reply[6]=run_case136==18?2:1;reply[7]=1;}
   }else if(tx[0]==0x70){
    if(flags""")
 patch('platform.c','run_case136==3&&start_count136','(run_case136==3||run_case136>=16)&&start_count136')
 patch('platform.c','run_case136==6&&stop_count','(run_case136==6||run_case136==19)&&stop_count')
 patch('host109.c','||run_case136>=8);','||(run_case136>=8&&run_case136<=18));')
 patch('host109.c','assert(observe_count136==203);','assert(observe_count136==((run_case136==3||run_case136==19)?4:203));')
 patch('host109.c','display_end139-display_begin139>=10000000000ull','((run_case136==3||run_case136==19)?display_end139-display_begin139<1000000000ull:display_end139-display_begin139>=10000000000ull)')
 patch('host109.c','assert(nes_run136.error==(run_case136==2?2:3));','assert(nes_run136.error==(run_case136==2?2:(run_case136==3||run_case136==19)?1:3));\n  if(run_case136==3||run_case136==19){\n   assert(nes_run136.first_error==1&&nes_run136.stop_error==(run_case136==19?3:0));\n   assert(nes_run136.context_valid);\n   uint64_t ctx=((uint64_t)nes_run136.context_hi<<32)|nes_run136.context_lo;\n   assert((ctx&0x1ffffff)==0x8123&&((ctx>>25)&0x3fffff)==0x200456&&((ctx>>47)&255)==7&&((ctx>>55)&255)==0xc8);\n  }')
 patch('host109.c','irq=0;nes_diag_begin();read_entry113();nes_diag_leave();irq=1;', '''irq=0;nes_diag_begin();read_entry113();
 extern unsigned card_report097(char *,unsigned);
 char report139[1024];assert(card_report097(report139,sizeof(report139))>0);
 assert(strstr(report139,"candidate=NES-SCREEN-139\\n"));
 assert(strstr(report139,"run_first_error=")&&strstr(report139,"run_stop_error=")&&strstr(report139,"fault_context_lo="));
 if(run_case136==3||run_case136==19){
  assert(strstr(report139,"run_error=1\\n")&&strstr(report139,"run_first_error=1\\n")&&strstr(report139,"fault_context_valid=1\\n"));
 }
 FILE *reportfile139=fopen("saved-report139.txt","wb");assert(reportfile139);
 assert(fwrite(report139,1,strlen(report139),reportfile139)==strlen(report139));assert(!fclose(reportfile139));
 nes_diag_leave();irq=1;''')
 sources=['card.c','host109.c','printf103.c','linked109-css.c','linked112-checkpoint.c']+['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')[-5000:]
 results=[]
 for case in range(20):
  log=o/f'case-{case}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),str(case),'0',*[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  t=log.read_text(errors='replace');assert not r.returncode and 'PASS136' in t,(case,r.returncode,t[-4000:])
  records=(o/'checkpoint-sectors.txt').read_bytes();(o/f'case-{case}-records.txt').write_bytes(records)
  stages=re.findall(rb'stage=([A-Z_]+)',records)
  if case in [0,2,3,6,19]:
   assert 'PASS109' in t
   for st in [b'DISPLAY_NEXT',b'DISPLAY_STOPPED',b'BASE_DONE',b'MENU_PREPARED']:assert st in stages,st
   (o/f'case-{case}-logical.txt').write_bytes((o/'entry-logical.txt').read_bytes())
   report=(o/'saved-report139.txt').read_text();(o/f'case-{case}-report.txt').write_text(report)
   fields=dict(line.split('=',1) for line in report.splitlines())
   if case in [3,19]:
    context=(int(fields['fault_context_hi'],16)<<32)|int(fields['fault_context_lo'],16)
    assert context&0x1ffffff==0x8123 and (context>>25)&0x3fffff==0x200456 and (context>>47)&255==7
    assert fields['run_stop_error']==('3' if case==19 else '0')
  else:assert b'DISPLAY_STOPPED' not in stages and b'BASE_DONE' not in stages
  results.append(dict(case=case,log_sha256=sha(log),records=len(stages)))
  print('PASS139 host',case,flush=True)
 (o/'result.json').write_text(json.dumps(dict(cases=results,actual_mcu_source=True,fpga_response_model=True,physical=False),indent=2)+'\n',encoding='utf8')
 shutil.copy2(__file__,o/'executed-test139.py')
if __name__=='__main__':main()
