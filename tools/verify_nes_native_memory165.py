# SPDX-License-Identifier: MIT
"""Check shared-reader CHR bytes and unchanged actual-core pixels privately."""
from pathlib import Path
import argparse,json,struct
from collections import defaultdict
from nes_game147 import ROOT,sha
from nes_native_planes165 import decode,unpack,reference_planes_rgb
from build_nes_game164 import palette as colors

def main():
 p=argparse.ArgumentParser()
 for n in ['core','baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 current=json.loads((a.core/'result.json').read_bytes());assert current['passed'] and current['frames']==20
 states=[[int(s,16) if i==3 else int(s) for i,s in enumerate(line.split())] for line in (a.core/'states.tsv').read_text().splitlines()]
 assert [v[0] for v in states]==list(range(1,len(states)+1))
 assert [v[1] for v in states]==list(range(1,13))+[14,16,18,20],states
 assert all(v[2]==(v[1]>=12) for v in states)
 for i in range(1,21):assert (a.core/f'game-{i}.hex').read_bytes()==(a.baseline/f'game-{i}.hex').read_bytes(),i
 fills=[list(map(int,line.split())) for line in (a.core/'fills.tsv').read_text().splitlines()]
 actual=defaultdict(dict)
 for line in (a.core/'bytes.tsv').read_text().splitlines():
  g,t,l,b,k=line.split();g,t,l,k=map(int,[g,t,l,k]);b=int(b,16)
  assert 0<=l<16 and (t,l) not in actual[g];actual[g][t,l]=(b,k)
 assert [f[:2] for f in fills]==[s[:2] for s in states if s[2]]
 raw=bytes(int(v,16) for v in (a.baseline/'chr.hex').read_text().split())
 lut=[bytes((((v>>s)&31)<<3)|(((v>>s)&31)>>2) for s in [0,5,10]) for v in struct.unpack('<64H',colors())]
 cases=[]
 for state,fill in zip([s for s in states if s[2]],fills):
  generation,frame=state[:2];assert fill[2:5]==[1,0,240] and fill[6]<=7 and fill[5]<262144
  lines=(a.core/f'frame-{frame}.dump').read_text().splitlines()
  assert lines==(a.baseline/f'frame-{frame}.dump').read_text().splitlines(),(frame,'geometry/raster/required set changed')
  tables=[{} for _ in range(7)]
  for line in lines[1:]:
   k,q,v=line.split();k=int(k);q=int(q);assert q not in tables[k];tables[k][q]=int(v,16)
  geometry=a.out/f'geometry-{frame}.dump'
  geometry.write_text('\n'.join([lines[0]]+[s for s in lines[1:] if int(s.split()[0])<4])+'\n')
  info,words=decode(geometry);assert info['valid'] and info['error']==0 and len(words)==7401
  required=defaultdict(int)
  for w in words:
   f,_=unpack(w);required[f.tile]|=2 if f.obj else 1
  assert set(tables[6])==set(range(8192))
  assert {t:k for t,k in tables[6].items() if k}==dict(required)
  assert set(actual[generation])=={(t,l) for t in required for l in range(16)}
  tiles={}
  for t,k in required.items():
   assert all(actual[generation][t,l][1]==k for l in range(16))
   tiles[t]=bytes(actual[generation][t,l][0] for l in range(16))
   assert tiles[t]==raw[t*16:t*16+16]
  rows=[]
  assert set(tables[4])==set(range(224))
  for y,v in sorted(tables[4].items()):
   assert v>>49==0;bank=v>>44&31
   rows.append((v>>30&7,v>>36&255,tuple(tables[5][bank*32+i] for i in range(32))))
  rgb=reference_planes_rgb(words,rows,tiles)
  pixels=[int(v,16) for v in (a.core/f'game-{frame}.hex').read_text().split()][8*256:232*256]
  assert rgb==b''.join(lut[v&63] for v in pixels)
  cases.append(dict(generation=generation,frame=frame,tiles=len(tiles),bytes=fill[4],cycles=fill[5],maximum_read_nes_edges=fill[6],pixels=len(pixels)))
 assert set(actual)=={f[0] for f in fills}
 result=dict(passed=True,unchanged_core_frames=20,filled_frames=len(cases),pixels=sum(c['pixels'] for c in cases),
  bytes=sum(c['bytes'] for c in cases),cases=cases,states=states,
  public_sources={'tools/verify_nes_native_memory165.py':sha(ROOT/'tools/verify_nes_native_memory165.py')},
  inputs={'core_result':sha(a.core/'result.json'),'baseline_result':sha(a.baseline/'result.json')},
  scope='Actual shared-reader bytes reconstruct five accepted boot scenes exactly. Full diagnostic readback holds each lease across the following frame; this deliberate test overhead is not production FPS. No buttons, first-level, host/SNES or board proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
