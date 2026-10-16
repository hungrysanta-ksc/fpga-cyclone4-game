# SPDX-License-Identifier: MIT
"""Materialize the production RUN path with planner191/service200/sink195.

Candidate only: board201 epoch/mux and metadata-only ingress are still pending.
Keep the old checked receiver until the paired wire format is implemented.
"""
from pathlib import Path
import argparse,hashlib,json,shutil
from nes_plan191 import prepare as planner
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);pins={}
 def copy(src,name=None):
  shutil.copyfile(src,out/(name or src.name));pins[src.relative_to(BASE).as_posix()]=sha(src)
 for f in (BASE/'probes/nes-bulk195/coupled03/candidate').glob('nes_*'):
  if f.suffix in ('.c','.h','.inc'):copy(f)
 for n in ('nes_native165.c','nes_native165.h','nes_trace166.c','nes_trace166.h'):
  copy(BASE/'probes/nes-paired186/arm01/src'/n)
 for n in ('nes_plan191.h','nes_plan_wire196.h','nes_plan_wire199.h','nes_plan_service200.h','nes_plan_service200.c'):
  copy(ROOT/'src/nes/firmware'/n)
 planner(out/'planner')
 shutil.copyfile(out/'planner/nes_plan191.c',out/'nes_plan191.c')
 # GCC13 enforces the existing implementation's lut[64] parameter bound.
 # Candidate-local declaration repair: preserve the selected191 archive/header.
 f=out/'nes_plan191.h';s=f.read_text();assert s.count('const uint16_t *,')==1
 f.write_text(s.replace('const uint16_t *,','const uint16_t [64],'),encoding='utf8',newline='\n')
 # E1 returns no useful payload. The production DMA already supports TX==RX;
 # retain one259B packet instead of another259B ignored receive stack buffer.
 # Caller packet p remains separate, so last-token copy after io is unchanged.
 f=out/'nes_sink_window184.c';s=f.read_text()
 for old,new in [('uint8_t tx[259],rx[259];','uint8_t tx[259];'),('io(s,tx,rx,n+3)','io(s,tx,tx,n+3)')]:
  assert s.count(old)==1,old;s=s.replace(old,new)
 f.write_text(s,encoding='utf8',newline='\n')
 copy(ROOT/'src/nes/firmware/nes_runtime202.c','nes_native_runtime165.c')
 copy(ROOT/'src/nes/firmware/nes_runtime202.h','nes_native_runtime165.h')
 pins['repository-nes-milestone/tools/nes_plan191.py']=sha(ROOT/'tools/nes_plan191.py')
 pins['repository-nes-milestone/tools/nes_runtime202.py']=sha(Path(__file__))
 r=dict(source_pins=pins,generated={p.name:sha(p) for p in out.iterdir() if p.is_file()},
        old_chr_ingress_retained=True,hardware_package=False)
 (out/'preparation202.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 print(json.dumps(prepare(a.out)))
