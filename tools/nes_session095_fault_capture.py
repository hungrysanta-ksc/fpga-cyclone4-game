# SPDX-License-Identifier: MIT
"""Actual094 cancellation/reentry traces, matched to raw lock-loss RTL tests."""
from pathlib import Path
import argparse,json,shutil
from nes_mcu_loader import ROOT,sha
from nes_spi_boot import run
from nes_diag_recovery_checks import function

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);a=p.parse_args();base=a.baseline.resolve();out=a.out.resolve()
 m=json.loads((ROOT/'analysis/session094-verification.json').read_bytes());assert sha(base.parent/'manifest.json')==m['manifest_sha256']
 r=json.loads((base/'result.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 for n,h in r['files'].items():
  assert sha(base/n)==h
  if Path(n).suffix in ['.c','.h']:shutil.copy2(base/n,out/n)
 shutil.copytree(base/'fine_x',out/'fine_x')
 s=(out/'platform094.c').read_text();old=function(s,'record')
 s=s.replace(old,'''static FILE *fault_trace095;
static unsigned old_sck095,old_ss095,fall_samples095,rows095;static bool fault_seen095;
static void record(int expect){
 (void)expect;if(!fault_trace095)return;
 unsigned ss=!!(mock_a.ODR&16),sck=!!(mock_b.ODR&8);int sample=-1;
 if(!ss&&old_ss095)fall_samples095=0;
 if(!ss&&!sck&&old_sck095){if(fall_samples095>=8)sample=!!(mock_b.IDR&16);fall_samples095++;}
 if(injected094&&!fault_seen095){fprintf(fault_trace095,"%llu 1 0 0 0 -1\\n",ns);fault_seen095=true;}
 fprintf(fault_trace095,"%llu 0 %u %u %u %d\\n",ns,ss,sck,!!(mock_b.ODR&32),sample);rows095++;
 old_ss095=ss;old_sck095=sck;
}''');(out/'platform094.c').write_text(s,encoding='utf-8',newline='\n')
 s=(out/'host.c').read_text().replace('assert(argc==3)','assert(argc==4)')
 s=s.replace('struct nes_menu_probe_report r;','fault_trace095=fopen(argv[3],"w");assert(fault_trace095);old_ss095=!!(mock_a.ODR&16);old_sck095=!!(mock_b.ODR&8);\n struct nes_menu_probe_report r;',1)
 s=s.replace(' printf("PASS094 scenario=', ' assert(fault_seen095&&rows095>0);fclose(fault_trace095);fault_trace095=0;\n printf("PASS094 scenario=')
 (out/'host.c').write_text(s,encoding='utf-8',newline='\n')
 production={n:sha(out/n) for n in m['host_arm_identical']};assert production==m['host_arm_identical']
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','nes_rom_spi.c','nes_rom_verify.c','nes_h1_stm32.c','nes_h1_session.c','nes_menu_diagnostic.c','nes_diag_runtime.c','nes_menu_return.c','nes_cf86_session094.c','host.c','-o','host.exe'],out,'compile')
 cases={}
 for case in [101,106]:
  log=run([out/'host.exe',out/'fine_x/mmc3.nes',str(case),out/(str(case)+'.trace')],out,str(case),60);assert 'poisoned=1' in log
  cases[str(case)]=dict(trace_sha256=sha(out/(str(case)+'.trace')),marker=log.strip().splitlines()[-1]);print(cases[str(case)]['marker'])
 shutil.copy2(__file__,out/'executed-fault-capture.py')
 (out/'result.json').write_text(json.dumps(dict(candidate='NES-CF86-FAULT-CAPTURE-095',production_sources=production,cases=cases,guard_ns=0,files={p.name:sha(p) for p in out.iterdir() if p.suffix in ['.c','.h','.py']}),indent=2)+'\n')
if __name__=='__main__':main()
