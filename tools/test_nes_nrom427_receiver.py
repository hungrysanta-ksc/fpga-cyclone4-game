# SPDX-License-Identifier: MIT
"""Production 227 receiver parses the first CRC-checked 427 RTL block."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--rtl',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
r=json.loads((a.rtl/'result.json').read_text());block=a.rtl/'nrom427-block.hex';assert r['passed'] and sha(block)==r['geometry_block_sha256']
assert 'PASS NROM427 geometry first block token=0 bytes=' in (a.rtl/'simulation.log').read_text(errors='replace')
src=BASE/'probes/nes-repeat227/arm01/src'
for n in ('nes_native165.c','nes_native165.h','nes_trace166.c','nes_trace166.h'):shutil.copyfile(src/n,d/n)
shutil.copyfile(ROOT/'tests/nes-nrom427/receiver.c',d/'receiver.c');shutil.copyfile(block,d/'block.hex')
gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
for name,cmd in [('build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','receiver.c','nes_native165.c','nes_trace166.c','-o','test.exe']),('test',[str(d/'test.exe'),str(d/'block.hex')])]:
 with(d/(name+'.log')).open('wb') as f:q=subprocess.run(cmd,cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-3000:]
text=(d/'test.log').read_text();assert 'accepted=1' in text
result={'passed':True,'rtl_block_sha256':sha(block),'receiver_sha256':sha(d/'nes_native165.c'),'host_output':text.strip(),'scope':'production receiver parsing first captured RTL block; no complete frame, ARM instruction timing or SNES display'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
