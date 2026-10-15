# SPDX-License-Identifier: MIT
"""Optimistic SPI floor from archived actual-C/65816 packets; NOT a FPS model."""
from pathlib import Path
import argparse,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
 base=ROOT.parent/'probes/nes-stream181';manifest=json.loads((base/'manifest01.json').read_bytes())
 folder=base/'evidence/test01/normal';frames={};pins={};pending=0;ever=False;bad=0
 for req in sorted(folder.glob('req-*.bin')):
  ack=req.with_name(req.name.replace('req-','ack-'))
  for f in [req,ack]:
   n=f.relative_to(base).as_posix();assert sha(f)==manifest[n],n;pins[n]=sha(f)
  b=req.read_bytes();c=ack.read_bytes();op=b[0];gen=int.from_bytes(b[8:10],'little')
  assert c[1]==op and c[2:10]==b[2:10] and c[10:12]==b'\x65\x9a'
  if c[0]>=0xe0:bad+=1;continue
  f=frames.setdefault(gen,dict(generation=gen,packets=0,request_bytes=0,queue_status=0,displayed=False))
  if not ever:f['queue_status']+=1 # Initial identity/empty-state validation.
  if op in [1,3] and ever:f['queue_status']+=1;pending=0
  if pending==4:f['queue_status']+=1;pending=0 # Best case: all four retired.
  f['packets']+=1;f['request_bytes']+=len(b);pending+=1;ever=True
  if op in [1,3]:f['queue_status']+=1;pending=0
  if op==3:assert c[0]==1;f['displayed']=True
 for f in frames.values():
  n=f['packets'];q=f['queue_status'];b=f['request_bytes']
  f.update(old_calls=3*n,queue_calls=n+q,old_clocked=b+35*n,queue_clocked=b+3*n+20*q)
  for tag in ['old','queue']:f[tag+'_floor_ms']=f[tag+'_clocked']*8/2625000*1000+f[tag+'_calls']*.008
 assert all(f['displayed'] for f in frames.values())
 result=dict(passed=True,frames=list(frames.values()),excluded_error_packets=bad,input_pins=pins,
  assumptions='Producer can reclaim all four slots on each credit poll; one ACK query per barrier. Same recorded packet segmentation. CS spacing8us/transaction; no extra polls or C/SNES work, FPGA->MCU, service, or capture wait. C cost model still uses old packet overhead; future retuning pending.',
  scope=__doc__,script_sha256=sha(Path(__file__)))
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result['frames']))
if __name__=='__main__':main()
