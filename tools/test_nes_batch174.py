# SPDX-License-Identifier: MIT
"""Actual C converter/sink against old byte oracle, capacity and fail-stop cases."""
from pathlib import Path
import argparse,json,subprocess,shutil
from nes_game147 import ROOT,sha
from nes_batch174 import converter,sink,header

def main():
 p=argparse.ArgumentParser()
 for n in ['prior','arm','pixels','out','gcc']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 for n,fn in [('nes_native_video165.c',converter),('nes_native_sink165.c',sink),('nes_native_video165.h',header)]:
  assert (a.arm/'src'/n).read_text()==fn((a.prior/'src'/n).read_text()),n
 for n in ['nes_native165.c','nes_native165.h','nes_native_video165.c','nes_native_video165.h','nes_native_sink165.c','nes_native_sink165.h','nes_trace166.c','nes_trace166.h','nes_sink_trace168.c','nes_sink_trace168.h']:
  shutil.copy2(a.arm/'src'/n,a.out/n)
 (a.out/'reference.c').write_text((a.prior/'src/nes_native_video165.c').read_text().replace('bool nes_native_video165_build(', 'bool reference_build('),newline='\n')
 shutil.copy2(ROOT/'tests/nes-functional/batch174_host.c',a.out/'host.c')
 def run(command,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run(command,cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
  assert r.returncode==0,(label,(a.out/(label+'.log')).read_text(errors='replace')[-4000:])
 run([str(a.gcc),'-std=c11','-Wall','-Wextra','-Werror','-O2','-I.','host.c','reference.c','nes_native165.c','nes_native_video165.c','nes_native_sink165.c','nes_trace166.c','nes_sink_trace168.c','-o','batch.exe'],'compile')
 records=[a.pixels/f'frame{n}/records.hex' for n in [24,25]]
 run([str(a.out/'batch.exe'),*map(str,records)],'test')
 log=(a.out/'test.log').read_text();assert 'PASS BATCH174 cases=9' in log
 result=dict(passed=True,summary=log.strip().splitlines()[-1],cases=log.strip().splitlines()[:-1],
  sources={n.name:sha(n) for n in a.out.glob('*.[ch]')},inputs={str(n):sha(n) for n in records},
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_batch174.py','tools/test_nes_batch174.py','tests/nes-functional/batch174_host.c']},
  scope=__doc__,hardware=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(log)
if __name__=='__main__':main()
