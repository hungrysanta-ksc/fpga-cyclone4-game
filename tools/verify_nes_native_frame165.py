# SPDX-License-Identifier: MIT
"""Check joined actual-core queries against old core pixels and pair evidence."""
from pathlib import Path
import argparse,json,struct
from collections import defaultdict
from nes_game147 import ROOT,sha
from nes_native_planes165 import decode,unpack,PlaneConsumer,reference_planes_rgb
from build_nes_game164 import palette as colors

def main():
 p=argparse.ArgumentParser()
 for n in ['core','baseline','planes','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 states=[]
 for line in (a.core/'states.tsv').read_text().splitlines():
  v=line.split();states.append([int(s,16) if i==3 else int(s) for i,s in enumerate(v)])
 assert len(states)==20 and [v[:2] for v in states]==[[i,i] for i in range(1,21)]
 assert all(v[2]==(v[1]>=12) for v in states),states
 old_rows=defaultdict(dict)
 for line in (a.baseline/'rows.tsv').read_text().splitlines():
  g,y,x,m,v=line.split();v=int(v,16)
  old_rows[int(g)][int(y)]=(int(x),int(m,16),tuple(v>>(i*6)&63 for i in range(32)))
 # The observer must not change even the rejected, display-disabled frames.
 for i in range(1,21):assert (a.core/f'game-{i}.hex').read_bytes()==(a.baseline/f'game-{i}.hex').read_bytes(),i
 raw=bytes(int(v,16) for v in (a.baseline/'chr.hex').read_text().split())
 lut=[bytes((((v>>s)&31)<<3)|(((v>>s)&31)>>2) for s in [0,5,10]) for v in struct.unpack('<64H',colors())]
 consumer=PlaneConsumer();results=[]
 for frame in range(12,21):
  lines=(a.core/f'frame-{frame}.dump').read_text().splitlines();tables=[{} for _ in range(7)]
  for line in lines[1:]:
   k,q,v=line.split();k=int(k);q=int(q);assert q not in tables[k];tables[k][q]=int(v,16)
  assert set(tables[4])==set(range(224)) and set(tables[6])==set(range(8192))
  geometry=a.out/f'geometry-{frame}.dump'
  geometry.write_text('\n'.join([lines[0]]+[s for s in lines[1:] if int(s.split()[0])<4])+'\n')
  info,words=decode(geometry);assert info['valid'] and info['error']==0 and len(words)==7401
  old=(a.planes/f'frame-{frame}-mode-0.dump').read_text().splitlines()
  assert geometry.read_text().splitlines()==old,(frame,'joined geometry differs from verified pair replay')
  rows=[]
  for y,v in sorted(tables[4].items()):
   assert v>>49==0;bank=v>>44&31
   row=(v>>30&7,v>>36&255,tuple(tables[5][bank*32+i] for i in range(32)))
   assert row==old_rows[frame][y],(frame,y,'joined row/palette')
   rows.append(row)
  expected_set=defaultdict(int)
  for w in words:
   f,_=unpack(w);expected_set[f.tile]|=2 if f.obj else 1
  assert {k:v for k,v in tables[6].items() if v}==dict(expected_set),(frame,'required physical tiles')
  tiles={t:raw[t*16:t*16+16] for t in expected_set}
  rgb=reference_planes_rgb(words,rows,tiles)
  pixels=[int(v,16) for v in (a.core/f'game-{frame}.hex').read_text().split()][8*256:232*256]
  assert rgb==b''.join(lut[v&63] for v in pixels),(frame,'actual joined PPU pixels')
  plan=consumer.prepare(words,rows,tiles)
  # Commit the PC shadow only after this complete generation passes. This is
  # a reference allocation/budget result, not an implemented hardware ACK.
  consumer.commit(plan)
  info.update(frame=frame,generation=states[frame-1][0],scroll_seen=states[frame-1][4],events=len(words),pixels=57344,
   required_tiles=len(tiles),complete_chr_bytes=len(tiles)*16,derived_patterns=plan['derived_patterns'])
  results.append(info)
 result=dict(passed=True,unchanged_core_frames=20,valid_frames=9,pixels=9*57344,cases=results,
  rejected_display_disabled_frames=11,states=states,
  public_sources={'tools/verify_nes_native_frame165.py':sha(ROOT/'tools/verify_nes_native_frame165.py')},
  inputs={'core_result':sha(a.core/'result.json'),'baseline_result':sha(a.baseline/'result.json'),'planes_result':sha(a.planes/'result.json')},
  scope='Direct actual-core joined geometry/raster/required-set queries reconstruct PPU pixels. CHR bytes supplied by private ROM to PC reference, not a hardware fill or host transport.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
