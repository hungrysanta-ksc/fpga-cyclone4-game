# SPDX-License-Identifier: MIT
"""077 full CMD24/write/status/busy edge model; no physical execution."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
from nes_diag_recovery_checks import function
ROOT=Path(__file__).resolve().parents[1]
def adapt(raw):
 old='  wiggle_fast_neg(4);';assert raw.count(old)==1
 raw=raw.replace(old,'  wiggle_fast_neg(nes_diag_active()?8:4);',1)
 old='  wiggle_fast_neg(2);\n  wait_busy();';assert raw.count(old)==1
 return raw.replace(old,'  if(nes_diag_active()&&!BITBAND(SD_DAT0REG->GPIO_I, SD_DAT0BIT)){nes_diag_sd_error(NES_DIAG_SD_RESPONSE);return;}\n'+old,1)
def main():
 p=argparse.ArgumentParser();p.add_argument('--src',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);out=a.out.resolve();raw=(a.src/'stm32f4xx/sdnative.c').read_text()
 shutil.copy2(a.src/'stm32f4xx/sdnative.c',out/'input-sdnative.c');shutil.copy2(__file__,out/'executed-driver.py')
 for n in ['nes_diag_runtime.c','nes_diag_runtime.h']:shutil.copy2(a.src/n,out/n)
 shutil.copy2(ROOT/'tests/nes-functional/sd_response077_host.c',out/'host.c')
 results={}
 for mode in ['baseline','candidate','no-end','short-tail']:
  s=raw if mode=='baseline' else adapt(raw)
  if mode=='no-end':s=s.replace('  if(nes_diag_active()&&!BITBAND(SD_DAT0REG->GPIO_I, SD_DAT0BIT)){nes_diag_sd_error(NES_DIAG_SD_RESPONSE);return;}\n','')
  if mode=='short-tail':s=s.replace('wiggle_fast_neg(nes_diag_active()?8:4)','wiggle_fast_neg(4)')
  (out/(mode+'-sdnative.c')).write_text(s,encoding='utf-8',newline='\n')
  names=['wiggle_fast_pos','wiggle_fast_neg','wiggle_fast_neg1','wiggle_fast_pos1','wait_busy','send_command_fast','make_crc7','cmd_fast','send_datablock','nes_diag_sd_response','nes_return_sd_write']
  bodies=[]
  for name in names:
   m=re.search(r'^(?:static inline void|static bool|static DRESULT|int|void) '+name+r'\(',s,re.M);assert m,name;bodies.append(function(s[m.start():],name))
  (out/'functions.inc').write_text(s[:s.index('#include')]+''.join(bodies),encoding='utf-8',newline='\n')
  shutil.copy2(out/'functions.inc',out/(mode+'-functions.inc'))
  with (out/(mode+'-compile.log')).open('wb') as f:subprocess.run([str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-error=implicit-fallthrough','-DCANDIDATE='+str(int(mode!='baseline')),'host.c','nes_diag_runtime.c','-o',mode+'.exe'],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
  with (out/(mode+'.log')).open('wb') as f:r=subprocess.run([str(out/(mode+'.exe'))],stdout=f,stderr=subprocess.STDOUT,timeout=60)
  log=(out/(mode+'.log')).read_text()
  if mode in ['baseline','candidate']:assert r.returncode==0 and 'PASS077' in log,log
  else:assert r.returncode!=0 and 'Assertion' in log and ('NES_DIAG_SD_RESPONSE' if mode=='no-end' else 'tail>=8') in log,log
  results[mode]=dict(checks=int(re.search(r'checks=(\d+)',log)[1]) if r.returncode==0 else None,exit=r.returncode)
 (out/'result.json').write_text(json.dumps(dict(results=results,source_sha256=hashlib.sha256((a.src/'stm32f4xx/sdnative.c').read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256((out/'candidate-sdnative.c').read_bytes()).hexdigest(),physical=False),indent=2)+'\n',encoding='utf-8')
 print(json.dumps(results))
if __name__=='__main__':main()
