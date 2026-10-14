# SPDX-License-Identifier: MIT
"""Actual C173 runtime: replay captured producer packets and validate timing split."""
from pathlib import Path
import argparse,json,subprocess,shutil
from nes_game147 import ROOT,sha
from build_nes_game164 import palette

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','trace','out','gcc']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);src=a.arm/'src'
 modules=['nes_native165','nes_native_video165','nes_native_sink165','nes_sink_spi165','nes_native_runtime165','nes_trace166','nes_sink_trace168','nes_sink_io170']
 pins={}
 for n in modules:
  for ext in ['c','h']:
   f=src/(n+'.'+ext);shutil.copy2(f,a.out/f.name);pins[f.name]=sha(f)
 s=(ROOT/'tests/nes-functional/native_runtime165_host.c').read_text()
 s=s.replace('#include <assert.h>','#include <assert.h>\n#include "nes_trace166.h"')
 s=s.replace('  at=packets=', '  memset(&nes_trace166,0,sizeof(nes_trace166));\n  at=packets=')
 s=s.replace('  if(mode<2){assert(','''  if(mode<2){assert(sizeof(nes_trace166)==40);
   assert(nes_trace166.receive_ticks>0 && nes_trace166.build_ticks>0 && nes_trace166.seal_ticks>0);
   assert(nes_trace166.last_display_tick==(uint32_t)(tick-run.started));
   assert(nes_trace166.last_display_tick==nes_trace166.receive_ticks+nes_trace166.build_ticks+nes_trace166.seal_ticks);
   assert(nes_trace166.begins==1 && nes_trace166.ends==1 && nes_trace166.commits==1 && !nes_trace166.aborts);
   assert(''')
 (a.out/'test.c').write_text(s,encoding='utf-8')
 shutil.copy2(a.trace,a.out/'native-transactions.txt');(a.out/'palette.bin').write_bytes(palette())
 def run(cmd,name):
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run([str(v) for v in cmd],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  assert r.returncode==0,(a.out/(name+'.log')).read_text(errors='replace')[-3500:]
 run([a.gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','test.c',*[n+'.c' for n in modules],'-o','profile.exe'],'build')
 run([a.out.resolve()/'profile.exe','native-transactions.txt','palette.bin'],'run')
 r={'passed':True,'cases':10,'timing_split_and_tick_wrap_verified':True,'trace_bytes':40,'source_sha256':pins,'captured_trace_sha256':sha(a.trace),'public_sources':{'tools/test_nes_profile173.py':sha(Path(__file__))},'scope':'actual C receiver/runtime/converter with captured producer bytes and synthetic sink ACK; no hardware FPS claim'}
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print((a.out/'run.log').read_text())
if __name__=='__main__':main()
