# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,subprocess,shutil,os
from nes_ncr1_live import ROOT,sha,put

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 assert str(out).isascii() and not out.exists();out.mkdir()
 for src in [ROOT/'src/nes/nes_ncr1_ppu_tap.sv',ROOT/'tests/nes-functional/ncr1_tap_tb.sv']:shutil.copy2(src,out/src.name)
 for tool,args in [('vlib',['work']),('vlog',['-sv','nes_ncr1_ppu_tap.sv','ncr1_tap_tb.sv']),('vsim',['-c','ncr1_tap_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (out/(tool+'.log')).open('wb') as f:cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  assert cp.returncode==0,tool
 log=(out/'vsim.log').read_text(errors='replace');m=re.search(r'PASS TAP CHECKS=(\d+)',log);assert m and int(m[1])==20 and not re.search(r'\*\* (?:Fatal|Error):',log)
 result={'candidate':'NES-R2-NCR1-LIVE-047','tap_checks':20,'passed':True,'source_sha256':sha(out/'nes_ncr1_ppu_tap.sv'),'testbench_sha256':sha(out/'ncr1_tap_tb.sv')}
 put(out/'result.json',json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
