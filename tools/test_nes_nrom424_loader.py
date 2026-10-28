# SPDX-License-Identifier: MIT
"""Use the exact 424 ROM in actual 414 loader/programmer/run host fixture."""
import argparse,json,sys
from pathlib import Path
from nes_delta231 import ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--fixture',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
out=a.out.resolve();assert out.as_posix().isascii() and not out.exists()
def once(s,x,y):assert s.count(x)==1,(x,s.count(x));return s.replace(x,y)
raw=a.rom.read_bytes();assert len(raw)==24592 and raw[:6]==b'NES\x1a\x01\x01'
src=(a.fixture/'run03-loader.c').read_text()
src=once(src,'#include <stdint.h>','#include <stdint.h>\nstatic const uint8_t fixture424[]={'+','.join(map(str,raw))+'};')
old=" filedata[0]='N';filedata[1]='E';filedata[2]='S';filedata[3]=0x1a;filedata[4]=1;filedata[5]=1;\n for(uint32_t i=16;i<sizeof(filedata);i++)filedata[i]=(uint8_t)(i^(i>>8)^0xa5);"
src=once(src,old,' memcpy(filedata,fixture424,sizeof(filedata));')
generated=out.parent/(out.name+'-loader.c');generated.write_text(src,newline='\n')
disk=(a.fixture/'loader01-disk.c').resolve();assert disk.is_file()
runner=(ROOT/'tools/test_nes_nrom408_fatfs.py').read_text()
runner=once(runner,"for q in host.glob('*.h'):shutil.copyfile(q,d/q.name)","for q in host.glob('*.h'):shutil.copyfile(q,d/q.name)\nshutil.copyfile(prod/'nes_run136.h',d/'nes_run136.h')")
runner=once(runner,"str(tests/'full_tb.c')",'str(Path('+repr(str(generated))+'))')
runner=once(runner,"sha(tests/'full_tb.c')",'sha(Path('+repr(str(generated))+'))')
runner=once(runner,"str(tests/'fat_disk.c')",'str(Path('+repr(str(disk))+'))')
runner=once(runner,"sha(tests/'fat_disk.c')",'sha(Path('+repr(str(disk))+'))')
sys.argv=['test_nes_nrom408_fatfs.py','--build',str(a.build),'--out',str(out)]
exec(compile(runner,str(ROOT/'tools/test_nes_nrom408_fatfs.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom408_fatfs.py')})
result=json.loads((out/'result.json').read_text());result['fixture_rom_sha256']=sha(a.rom)
result['scope']='424 ROM with actual loader/FatFS/programmer/run136 host C; modeled native, observer, GPIO, SPI and PSRAM; not FPGA cosimulation or actual controller'
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
