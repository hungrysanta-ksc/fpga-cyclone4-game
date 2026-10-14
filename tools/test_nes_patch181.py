# SPDX-License-Identifier: MIT
"""Bounded row RAM lifecycle; explicitly not live-collector integration."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1]
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 assert not a.out.exists();a.out.mkdir(parents=True)
 files=['src/nes/video/nes_patch_rows181.sv','tests/nes-functional/patch_rows181_tb.sv'];pins={}
 for n in files:shutil.copy2(ROOT/n,a.out/Path(n).name);pins[n]=H(ROOT/n)
 def call(exe,args):
  with (a.out/(exe+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  text=(a.out/(exe+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-4000:]
  return text
 call('vlib',['work']);call('vlog',['-sv',*[Path(n).name for n in files]])
 text=call('vsim',['-c','work.patch_rows181_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
 assert 'PASS PATCH181 cases=9 exact_pixels=2560' in text
 result=dict(passed=True,cases=9,exact_pixels=2560,sources=pins,raw_rows_sha256=H(a.out/'captured-rows.txt'),public_sources={'tools/test_nes_patch181.py':H(Path(__file__))},integrated_with_live_game=False,fit=False,hardware=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print('PASS PATCH181 cases=9 exact_pixels=2560')
if __name__=='__main__':main()
