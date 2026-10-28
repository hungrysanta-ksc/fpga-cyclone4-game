# SPDX-License-Identifier: MIT
"""Run the exact 227 FPGA programmer against actual FatFS and modeled pins."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve()
assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
prod=BASE/'probes/nes-repeat227/arm01/src';host=BASE/'probes/nes-run136/evidence/initial/host04'
for f in host.glob('*.h'):shutil.copyfile(f,d/f.name)
for name in ('ff.c','ff.h','ffconf.h','diskio.h'):
 assert sha(host/name)==sha(prod/name);shutil.copyfile(prod/name,d/name)
(d/'unicode').mkdir();shutil.copyfile(prod/'ccsbcs.c',d/'unicode/ccsbcs.c')
s=(prod/'fpga.c').read_text();marker='struct nes_diag_input {FIL file;';assert s.count(marker)==1
(d/'programmer.inc').write_text(s[s.index(marker):],newline='\n')
disk=(ROOT/'tests/nes-nrom408/fat_disk.c').read_text();anchor=' memcpy(media+DATA_SECTOR*512u,file,bytes);'
assert disk.count(anchor)==1
disk=disk.replace(anchor,anchor+'''
 // Independent synthetic config files, outside the ROM's cluster chain.
 word(fat+51*2,0xffff);word(fat+52*2,0xffff);
 uint8_t *base=dir+32,*bad=dir+64;
 memcpy(base,"BASE       ",11);base[11]=0x20;word(base+26,51);dword(base+28,10);
 memcpy(bad,"BAD     BI3",11);bad[11]=0x20;word(bad+26,52);dword(bad+28,3);
 const uint8_t config[]={1,0x5b,0xa4,3,0x9b,0x9b,0x77,0x66,2,1};
 const uint8_t malformed[]={0x5b,0x44,0};
 memcpy(media+(DATA_SECTOR+49)*512u,config,sizeof(config));
 memcpy(media+(DATA_SECTOR+50)*512u,malformed,sizeof(malformed));''')
(d/'fat_disk.c').write_text(disk,newline='\n')
gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
cmd=[gcc,'-std=c99','-O2','-I',str(d),'-I',str(prod),str(d/'ff.c'),str(d/'unicode/ccsbcs.c'),str(d/'fat_disk.c'),str(ROOT/'tests/nes-nrom412/programmer_tb.c'),'-o',str(d/'test.exe')]
for name,command in [('compile',cmd),('test',[str(d/'test.exe')])]:
 with (d/(name+'.log')).open('wb') as f:r=subprocess.run(command,cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-5000:]
assert 'PASS NROM412 actual programmer' in (d/'test.log').read_text()
result={'passed':True,'programmer_source':sha(prod/'fpga.c'),'FatFS':sha(prod/'ff.c'),'test':sha(ROOT/'tests/nes-nrom412/programmer_tb.c'),'scope':'actual 227 programmer and FatFS; synthetic config stream, modeled GPIO/DONE, no real FPGA programming, loader or ARM execution'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
