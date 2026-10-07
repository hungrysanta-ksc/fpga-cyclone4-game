# SPDX-License-Identifier: MIT
"""Actual076 classifier/copy/active memory branch; FatFS/SRAM are fault models."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,re
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--src',type=Path,required=True);p.add_argument('--menu',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mutation',choices=['class-crc','copy-crc']);a=p.parse_args()
 assert hashlib.sha256(a.menu.read_bytes()).hexdigest()=='f53b777a0bbe37668cd88cf8c80c5e5a0a60f861f58d1d4d3d9b082e9d1b4325'
 a.out.mkdir(parents=True,exist_ok=False);out=a.out.resolve()
 names=['nes_menu076.c','nes_menu076.h','nes_menu_return.c','nes_menu_return.h','nes_diag_runtime.c','nes_diag_runtime.h','smc.h']
 for n in names:shutil.copy2(a.src/n,out/n)
 def write(n,s):(out/n).write_text(s,encoding='utf-8',newline='\n')
 write('config.h','/* host, no hardware */\n')
 write('fpga_spi.h','\n'.join(re.findall(r'^#define FEAT_.*',(a.src/'fpga_spi.h').read_text(),re.M))+'\n')
 write('fileops.h','''#ifndef FILEOPS_H
#define FILEOPS_H
#include <stdint.h>
typedef unsigned UINT,FRESULT;
typedef struct {uint32_t fsize,fptr;} FIL;
#define f_size(f) ((f)->fsize)
#define FR_OK 0u
#define FA_READ 1u
extern FIL file_handle;extern FRESULT file_res;
FRESULT f_open(FIL *,const char *,unsigned);
FRESULT f_read(FIL *,void *,UINT,UINT *);
FRESULT f_lseek(FIL *,uint32_t);
FRESULT f_close(FIL *);
void file_close(void);
#endif
''')
 write('memory.h','#include <stdint.h>\nuint16_t sram_writeblock(void *,uint32_t,uint16_t);\nuint16_t sram_readblock(void *,uint32_t,uint16_t);\n')
 memory=(a.src/'memory.c').read_text();start=memory.index('  if(nes_diag_active()) {\n    /* The global');end=memory.index('  } else {',start)
 write('active-memory.inc','static unsigned memory_classify(void){\n'+memory[start:end]+'  }\n return 1;\n}\n')
 shutil.copy2(a.src/'memory.c',out/'input-memory.c');shutil.copy2(__file__,out/'executed-driver.py');shutil.copy2(ROOT/'tests/nes-functional/menu076_host.c',out/'host.c')
 if a.mutation:
  n='nes_menu076.c' if a.mutation=='class-crc' else 'nes_menu_return.c';s=(out/n).read_text();old='||(crc^0xffffffffu)!=NES_MENU076_CRC';assert s.count(old)==1;write(n,s.replace(old,''))
 with (out/'compile.log').open('wb') as log:subprocess.run([str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','host.c','nes_menu076.c','nes_menu_return.c','nes_diag_runtime.c','-o','test.exe'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
 with (out/'run.log').open('wb') as log:r=subprocess.run([str(out/'test.exe'),str(a.menu.resolve())],stdout=log,stderr=subprocess.STDOUT,timeout=60)
 text=(out/'run.log').read_text();ok=r.returncode==0 and 'PASS076' in text
 if a.mutation:
  target='!memory_classify()&&nes_return_failed()&&!closes' if a.mutation=='class-crc' else '!nes_return_copy_menu("menu",0,0)&&nes_return_failed()'
  assert not ok and 'Assertion' in text and target in text,text
 else:assert ok,text
 (out/'result.json').write_text(json.dumps(dict(exit=r.returncode,mutation=a.mutation,physical=False,checks=int(re.search(r'checks=(\d+)',text)[1]) if ok else None,inputs={n:hashlib.sha256((a.src/n).read_bytes()).hexdigest() for n in names+['memory.c']}),indent=2)+'\n')
 print(('PASS causal '+a.mutation) if a.mutation else text)
if __name__=='__main__':main()
