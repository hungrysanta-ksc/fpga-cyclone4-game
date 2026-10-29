# SPDX-License-Identifier: MIT
"""Feed 429 RTL geometry to the exact 227 resident planner; host model only."""
import argparse,collections,json,shutil,struct,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--rtl',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
r=json.loads((a.rtl/'result.json').read_text());assert r['passed'] and r['blocks_sha256']==sha(a.rtl/'nrom429-blocks.txt') and r['fixture_sha256']==sha(a.rom)
src=BASE/'probes/nes-repeat227/arm01/src'
for n in ('nes_native165.c','nes_native165.h','nes_trace166.c','nes_trace166.h','nes_planner211.c','nes_resident211.c','nes_resident211.h','nes_plan191.h','nes_native_video165.h','nes_palette165.inc'):shutil.copyfile(src/n,d/n)
shutil.copyfile(ROOT/'tests/nes-nrom430/planner.c',d/'planner.c');shutil.copyfile(a.rtl/'nrom429-blocks.txt',d/'blocks.txt')
gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
for name,cmd in [('build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','planner.c','nes_native165.c','nes_trace166.c','nes_planner211.c','nes_resident211.c','-o','test.exe']),('test',[str(d/'test.exe'),'blocks.txt'])]:
 with(d/(name+'.log')).open('wb') as f:q=subprocess.run(cmd,cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-3000:]
text=(d/'test.log').read_text();assert 'PASS 227 plan generation=4 records=1404 blocks=25 plans=2 bg=2 obj=0 groups=28 hdma=11' in text
raw=(d/'plans.bin').read_bytes();assert len(raw)==80
zero=struct.unpack('<HHHBB16B8H',raw[:40]);tile=struct.unpack('<HHHBB16B8H',raw[40:]);assert zero[:5]==(4,0,0,2,0) and tile[:5]==(4,1,1,0,255)
assert tile[5:21]==tuple(v for n in range(8) for v in (n,n)) and tile[21:]==(65535,)*8
rom=a.rom.read_bytes();assert len(rom)==24592 and rom[16400+16:16400+24]==bytes([0xaa,0x55]*4) and rom[16400+24:16400+32]==bytes(8)
words=struct.unpack('<2048H',(d/'map.bin').read_bytes());slots=collections.Counter(v&1023 for v in words);assert slots=={0:1124,1:924}
result={'passed':True,'rtl_blocks_sha256':sha(a.rtl/'nrom429-blocks.txt'),'rom_sha256':sha(a.rom),'planner_sha256':sha(d/'nes_planner211.c'),'host_output':text.strip(),'map_sha256':sha(d/'map.bin'),'plans_sha256':sha(d/'plans.bin'),'slots':dict(slots),'scope':'227 planner on actual RTL geometry, synthetic D3 and host plan sink; CHR references checked against fixture, not real FPGA tile service, 65816 execution, timing or hardware'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
