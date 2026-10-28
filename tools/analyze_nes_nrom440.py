# SPDX-License-Identifier: MIT
"""Independently check and summarize the 440 live SPI/65816 evidence."""
import argparse,binascii,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);p.add_argument('--reference',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.run
r=json.loads((d/'result.json').read_text());assert r['passed'] and not (d/'lua-error.txt').exists();pieces=[]
for f in sorted(d.glob('H-*.req')):
 b=f.read_bytes()
 if b[0]==1 and len(b)>8 and b[8]==0xd1:
  q=(d/(f.stem+'.rsp')).read_bytes();assert len(q)>=4 and binascii.crc_hqx(q[1:-2],65535)==int.from_bytes(q[-2:],'big');pieces.append(q[1:-2])
raw=b''.join(pieces);expected=b''.join(bytes.fromhex(line.split()[2]) for line in a.reference.read_text().splitlines());assert len(pieces)==25 and len(raw)==5764 and raw==expected
assert r['consumer']['commits']==1 and r['consumer']['acks']==33 and r['consumer']['retired_chunks']==1
host=(d/'host.log').read_text();rtl=(d/'rtl.log').read_text(errors='replace');assert 'PASS NROM440 live RUN frames=1' in host and 'PASS NROM440 live board capture queue display retire' in rtl and 'Errors: 0' in rtl
pixels=(d/'frame-1.rgb').read_bytes();assert len(pixels)==256*239*3
for y in range(16,224):
 for x in range(16,240):
  i=(y*256+x)*3;assert (pixels[i:i+3]==bytes(3))==((x+y)%2==0)
result={'passed':True,'live_d1_blocks':len(pieces),'live_d1_bytes':len(raw),'live_d1_sha256':hashlib.sha256(raw).hexdigest(),'matches_independent_429_capture':True,'frame_sha256':hashlib.sha256(pixels).hexdigest(),'consumer':r['consumer'],'host':host.strip(),'scope':'live 227 board/NES core RTL, host 227 RUN and 65816 emulator over transaction RPC; seeded PSRAM/verified loader and no common timing or physical claim'}
a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
