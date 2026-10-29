# SPDX-License-Identifier: MIT
"""Replay actual RTL frame blocks in production receiver; D3 reply is modeled."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--rtl',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
r=json.loads((a.rtl/'result.json').read_text());block=a.rtl/'nrom429-blocks.txt';assert r['passed'] and sha(block)==r['blocks_sha256']
src=BASE/'probes/nes-repeat227/arm01/src'
for n in ('nes_native165.c','nes_native165.h','nes_trace166.c','nes_trace166.h'):shutil.copyfile(src/n,d/n)
shutil.copyfile(ROOT/'tests/nes-nrom429/receiver.c',d/'receiver.c');shutil.copyfile(block,d/'blocks.txt')
gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
for name,cmd in [('build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','receiver.c','nes_native165.c','nes_trace166.c','-o','test.exe']),('test',[str(d/'test.exe'),str(d/'blocks.txt')])]:
 with(d/(name+'.log')).open('wb') as f:q=subprocess.run(cmd,cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-3000:]
text=(d/'test.log').read_text();assert 'PASS 227 receiver committed' in text
result={'passed':True,'rtl_blocks_sha256':sha(block),'receiver_sha256':sha(d/'nes_native165.c'),'host_output':text.strip(),'scope':'actual RTL block replay through production receiver; D3 response modeled, no live ARM timing or SNES display'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
