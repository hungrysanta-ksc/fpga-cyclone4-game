# SPDX-License-Identifier: MIT
"""Actual145 MCU path: balanced report budget plus20 retained RUN/STOP/fault cases."""
from pathlib import Path
import argparse,json,shutil,subprocess,re
from nes_screen145 import prepare
from nes_spi_boot import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;prepare(a.baseline,o,'host')
 sources=['card.c','host109.c','printf103.c','linked109-css.c','linked112-checkpoint.c']+['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')[-5000:]
 results=[]
 for case in range(21):
  log=o/f'case-{case}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),str(case),'0',*[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  t=log.read_text(errors='replace');assert not r.returncode and 'PASS136' in t,(case,r.returncode,t[-4000:])
  records=(o/'checkpoint-sectors.txt').read_bytes();(o/f'case-{case}-records.txt').write_bytes(records)
  stages=re.findall(rb'stage=([A-Z_]+)',records)
  if case in [0,2,3,6,19,20]:
   assert 'PASS109' in t
   for st in [b'DISPLAY_NEXT',b'DISPLAY_STOPPED',b'BASE_DONE',b'MENU_PREPARED']:assert st in stages,st
   (o/f'case-{case}-logical.txt').write_bytes((o/'entry-logical.txt').read_bytes())
   report=(o/'saved-report145.txt').read_text();(o/f'case-{case}-report.txt').write_text(report)
   fields=dict(line.split('=',1) for line in report.splitlines())
   if case in [0,2,6,20]:assert fields['screen_phase_mask']=='8' and fields['screen_stage']=='99',fields
   if case in [3,19]:
    context=(int(fields['fault_context_hi'],16)<<32)|int(fields['fault_context_lo'],16)
    assert context&0x1ffffff==0x8123 and (context>>25)&0x3fffff==0x200456 and (context>>47)&255==7
    assert fields['run_stop_error']==('3' if case==19 else '0')
  else:assert b'DISPLAY_STOPPED' not in stages and b'BASE_DONE' not in stages
  results.append(dict(case=case,log_sha256=sha(log),records=len(stages)))
  print('PASS145 host',case,flush=True)
 (o/'result.json').write_text(json.dumps(dict(cases=results,actual_mcu_source=True,fpga_response_model=True,physical=False),indent=2)+'\n',encoding='utf8')
 shutil.copy2(__file__,o/'executed-test145.py')
if __name__=='__main__':main()
