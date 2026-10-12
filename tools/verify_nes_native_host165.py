# SPDX-License-Identifier: MIT
"""Check host-clock records with a strict receiver and existing pixel consumer."""
from pathlib import Path
import argparse,json,struct
from nes_game147 import ROOT,sha
from nes_native_receiver165 import Receiver
from nes_native_planes165 import decode,PlaneConsumer,reference_planes_rgb
from build_nes_game164 import palette as colors

def main():
 p=argparse.ArgumentParser()
 for n in ['transport','baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 transport=json.loads((a.transport/'result.json').read_bytes());assert transport['passed']
 lut=[bytes((((v>>s)&31)<<3)|(((v>>s)&31)>>2) for s in [0,5,10]) for v in struct.unpack('<64H',colors())]
 consumer=PlaneConsumer();results=[];normal=None
 for case in transport['cases']:
  frame,mode=case['frame'],case['mode'];path=a.transport/f'frame{frame}-mode{mode}.tsv'
  assert sha(path)==case['stream_sha256'];receiver=Receiver();committed=[]
  words=path.read_text().splitlines()
  for text in words:
   if text=='R':receiver.reset();continue
   snapshot=receiver.feed(int(text,16))
   if receiver.state=='complete' and mode not in [3,4]:receiver.prepared(mode!=2)
   if snapshot:committed.append(snapshot)
  assert receiver.state=='idle'
  assert len(committed)==(mode in [0,5,6])
  if not committed:results.append(dict(frame=frame,mode=mode,commits=0));continue
  s=committed[0];tables=s['tables'];groups,objects,exceptions=s['geometry']
  assert len(s['tiles'])==15 and s['bytes']==240
  if mode==5:assert s['generation']==65535
  if mode==6:assert s['generation']==13
  geometry=a.out/f'frame{frame}-mode{mode}.dump'
  geometry.write_text(f'H 1 00 224 {groups} {objects} {exceptions}\n'+''.join(f'{k} {q} {v:016x}\n' for k in range(4) for q,v in tables[k].items()))
  info,events=decode(geometry);assert len(events)==7401
  baseline=[{} for _ in range(7)]
  for text in (a.baseline/f'frame-{frame}.dump').read_text().splitlines()[1:]:
   k,q,v=text.split();baseline[int(k)][int(q)]=int(v,16)
  assert tables==baseline[:6]
  raw=bytes(int(v,16) for v in (a.baseline/'chr.hex').read_text().split())
  assert all(b==raw[t*16:t*16+16] for t,b in s['tiles'].items())
  rows=[]
  for y,v in tables[4].items():
   bank=v>>44&31;rows.append((v>>30&7,v>>36&255,tuple(tables[5][bank*32+i] for i in range(32))))
  rgb=reference_planes_rgb(events,rows,s['tiles'])
  pixels=[int(v,16) for v in (a.baseline/f'game-{frame}.hex').read_text().split()][8*256:232*256]
  assert rgb==b''.join(lut[v&63] for v in pixels)
  # Consumer publication is advanced only for committed normal scenes.
  plan=consumer.prepare(events,rows,s['tiles']) if mode==0 else PlaneConsumer().prepare(events,rows,s['tiles'])
  if mode==0:consumer.commit(plan)
  results.append(dict(frame=frame,mode=mode,commits=1,pixels=len(pixels),host_records=len(words),native_bytes=s['bytes'],snes_payload=plan['payload'],snes_commands=len(plan['writes'])))
  if normal is None:normal=[int(t,16) for t in words]
 # A receiver cannot publish END directly, accept repeated/out-of-order data,
 # mix generations, omit a tile, or accept an unprepared COMMIT.
 rejects=0
 variants=[normal[:2]+normal[1:], [normal[0],normal[2],*normal[3:]],
  [normal[0],normal[1]^(1<<77),*normal[2:]],normal[:-3]+normal[-2:]]
 for stream in variants:
  r=Receiver()
  try:
   for w in stream:
    r.feed(w)
    if r.state=='complete':r.prepared()
  except ValueError:rejects+=1
  else:raise AssertionError('corrupted stream accepted')
 r=Receiver()
 try:
  for w in normal:r.feed(w)
 except ValueError:rejects+=1
 else:raise AssertionError('unprepared COMMIT accepted')
 result=dict(passed=True,cases=results,normal_pixels=sum(c.get('pixels',0) for c in results if c['mode']==0),reset_pixels=sum(c.get('pixels',0) for c in results if c['mode']==5),abort_recovery_pixels=sum(c.get('pixels',0) for c in results if c['mode']==6),receiver_rejects=rejects,
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_native_receiver165.py','tools/verify_nes_native_host165.py']},
  inputs={'transport':sha(a.transport/'result.json'),'baseline':sha(a.baseline/'result.json')},
  scope='Host-clock records decoded and gated by PREPARED/COMMIT in a PC reference; committed scenes feed the existing SNES command reference and match original NES pixels. No new SNES execution or MCU firmware.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
