# SPDX-License-Identifier: MIT
import argparse,shutil,subprocess,json
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--new-blocks',required=True,type=Path);p.add_argument('--old-blocks',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
prod=BASE/'probes/nes-nrom418/arm01/src'
for n in ['nes_native165.h','nes_trace166.h','nes_trace166.c']:shutil.copyfile(prod/n,d/n)
shutil.copyfile(prod/'nes_native165.c',d/'reference.c');shutil.copyfile(a.source,d/'nes_native165.c');shutil.copyfile(ROOT/'tests/nes-nrom471/compare.c',d/'compare.c')
gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
def run(label,args):
 with (d/(label+'.log')).open('wb') as f:r=subprocess.run(args,cwd=d,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(d/(label+'.log')).read_text(errors='replace')[-2000:]
names=['nes_native165_reset','nes_native165_packet','nes_native165_poll','nes_native165_prepare','nes_native165_consumed','nes_native181_pixels']
run('ref-build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror',*['-D'+n+'='+n+'_ref' for n in names],'-c','reference.c','-o','reference.o'])
run('build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','compare.c','nes_native165.c','nes_trace166.c','reference.o','-o','compare.exe'])
run('compare',[str(d/'compare.exe'),str(a.old_blocks.resolve()),str(a.new_blocks.resolve())]);r={'passed':True,'receiver_sha256':sha(a.source),'old_blocks_sha256':sha(a.old_blocks),'new_blocks_sha256':sha(a.new_blocks),'output':(d/'compare.log').read_text().strip()};(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
