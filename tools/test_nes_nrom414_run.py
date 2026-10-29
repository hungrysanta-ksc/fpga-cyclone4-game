# SPDX-License-Identifier: MIT
"""Actual run136 with actual 412 loader/programmer, modeled native/observer."""
import argparse
import sys
from pathlib import Path
from nes_delta231 import BASE,ROOT

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--fixture',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
out=a.out.resolve();assert not out.exists() and out.as_posix().isascii()
def once(s,old,new):
 assert s.count(old)==1,(old,s.count(old));return s.replace(old,new)
src=(a.fixture/'loader01-loader.c').read_text()
start=src.index('static bool identify136(',src.index('#include "full408.inc"'))
end=src.index('bool nes_game149_transfer(',start)
run=(a.build/'nes_run136.inc').read_text()
run=once(run,'#include "nes_runtime_board165.inc"',r'''
// Explicitly modeled native execution: only exercise run136 orchestration.
static bool native_session165(const struct nes_rom_spi_io *io,uint32_t epoch){
 (void)io;(void)epoch;nes_run136.first=1;nes_run136.last=2;return true;
}
static bool nes_display_leave146(void){return true;}
''')
src=src[:start]+run+'\n'+src[end:]
anchor=' uint8_t check[8];nes_rom_spi_frame(check,tx[0],at,tx[4]);assert(!memcmp(check,tx,8));'
src=once(src,anchor,r'''
 if(tx[0]==0x70 || tx[0]==0x73 || tx[0]==0x76 || tx[0]==0x77){
  memset(rx,0,8);
  if(tx[0]==0x70){rx[1]=0xe5;rx[2]=1;rx[7]=start_count?2:0;}
  if(tx[0]==0x73){rx[1]=0xe6;rx[7]=2;}
  if(tx[0]==0x76){rx[1]=0xe5;rx[7]=1;}
  if(tx[0]==0x77){rx[1]=0xe5;rx[5]=1;rx[6]=96;rx[7]=3;}
  return true;
 }
'''+anchor)
src=once(src,'assert(safe&&p.sd.verified&&p.sd.load.base_restored&&p.sd.load.stop_ok);', '''assert(safe&&p.sd.verified&&p.sd.load.base_restored&&p.sd.load.stop_ok);
   assert(nes_run136.start_sent && nes_run136.stop_ok && nes_run136.passed &&
          nes_run136.screen_valid && nes_run136.pad_valid && nes_run136.history_valid &&
          nes_run136.first==1 && nes_run136.last==2 && nes_run136.stopped==2);''')
generated=out.parent/(out.name+'-loader.c');generated.write_text(src,newline='\n')
disk=(a.fixture/'loader01-disk.c').resolve();assert disk.is_file()
runner=(ROOT/'tools/test_nes_nrom408_fatfs.py').read_text()
runner=once(runner,"for q in host.glob('*.h'):shutil.copyfile(q,d/q.name)","for q in host.glob('*.h'):shutil.copyfile(q,d/q.name)\nshutil.copyfile(prod/'nes_run136.h',d/'nes_run136.h')")
runner=once(runner,"str(tests/'full_tb.c')",'str(Path('+repr(str(generated))+'))')
runner=once(runner,"sha(tests/'full_tb.c')",'sha(Path('+repr(str(generated))+'))')
runner=once(runner,"str(tests/'fat_disk.c')",'str(Path('+repr(str(disk))+'))')
runner=once(runner,"sha(tests/'fat_disk.c')",'sha(Path('+repr(str(disk))+'))')
runner=once(runner,"'scope':'full generated 227 loader + byte-identical 227 FatFS on synthetic FAT16, modeled SPI/PSRAM and run/base, no FPGA RTL cosimulation or physical hardware'", "'scope':'actual loader, programmer, run136 and FatFS host C; synthetic disk, modeled native session, observer, GPIO, SPI and PSRAM; no RTL cosimulation or ARM execution'")
sys.argv=['test_nes_nrom408_fatfs.py','--build',str(a.build),'--out',str(out)]
exec(compile(runner,str(ROOT/'tools/test_nes_nrom408_fatfs.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom408_fatfs.py')})
