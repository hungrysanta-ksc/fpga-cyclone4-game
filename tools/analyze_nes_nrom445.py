# SPDX-License-Identifier: MIT
"""Independently validate both live 445 geometry streams and displays."""
import argparse,binascii,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.run;r=json.loads((d/'result.json').read_text());assert r['passed'] and not (d/'lua-error.txt').exists();pieces=[]
for f in sorted(d.glob('H-*.req')):
 b=f.read_bytes()
 if b[0]==1 and len(b)>8 and b[8]==0xd1:
  q=(d/(f.stem+'.rsp')).read_bytes();assert len(q)>=4 and binascii.crc_hqx(q[1:-2],65535)==int.from_bytes(q[-2:],'big');pieces.append(q[1:-2])
assert len(pieces)==50;frames=[b''.join(pieces[:25]),b''.join(pieces[25:])];assert all(len(x)==5764 for x in frames) and frames[0][:4]==bytes.fromhex('e0000004') and frames[1][:4]==bytes.fromhex('e0000005')
assert r['consumer']['commits']==2 and r['consumer']['acks']==66 and r['consumer']['retired_chunks']==2
host=(d/'host.log').read_text();rtl=(d/'rtl.log').read_text(errors='replace');assert 'PASS NROM445 live two RUN frames=2' in host and 'gen=4,5' in host and 'tokens=50' in host and 'PASS NROM443 live board display retire STOP' in rtl and 'Errors: 0' in rtl
hashes=[]
for frame in (1,2):
 pixels=(d/f'frame-{frame}.rgb').read_bytes();assert len(pixels)==256*239*3
 for y in range(16,224):
  for x in range(16,240):
   i=(y*256+x)*3;assert (pixels[i:i+3]==bytes(3))==((x+y)%2==0)
 hashes.append(hashlib.sha256(pixels).hexdigest())
result={'passed':True,'live_d1_blocks':len(pieces),'frame_bytes':[len(x) for x in frames],'generations':[4,5],'live_d1_sha256':[hashlib.sha256(x).hexdigest() for x in frames],'display_sha256':hashes,'consumer':r['consumer'],'host':host.strip(),'scope':'two live 227 board captures, 227 RUN host C and 65816 over transaction RPC; seeded loader/PSRAM, no common physical timing or capture-deadline claim'}
a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
