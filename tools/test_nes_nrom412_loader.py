# SPDX-License-Identifier: MIT
"""Bind 227 loader and programmer using FatFS, modeled SPI/PSRAM and GPIO."""
import argparse
import sys
from pathlib import Path
from nes_delta231 import BASE,ROOT

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
out=a.out.resolve();assert not out.exists() and out.as_posix().isascii()
def once(s,old,new):
 assert s.count(old)==1,(old,s.count(old));return s.replace(old,new)
src=(ROOT/'tests/nes-nrom408/full_tb.c').read_text()
src=once(src,'struct diagnostic {unsigned error;};','struct diagnostic {unsigned error,phase;};')
src=once(src,'static FATFS fatfs;','static FATFS fatfs;\nstatic FIL *rom_file;')
src=once(src,' opens++;\n if(scenario==MUTATE_THIRD', ' if(!strcmp(path,"nrom.nes")){opens++;rom_file=f;}\n if(scenario==MUTATE_THIRD')
src=once(src,'static FRESULT nrom_close(FIL *f){closes++;return f_close(f);}', 'static FRESULT nrom_close(FIL *f){if(f==rom_file)closes++;return f_close(f);}')
src=once(src,'static void nes_diag_progress(int s,uint32_t a,uint32_t b){(void)s;(void)a;(void)b;}', 'static void nes_diag_progress(int s,uint32_t a,uint32_t b){diagnostic.phase=s;(void)a;(void)b;}')
fpga=(BASE/'probes/nes-repeat227/arm01/src/fpga.c').read_text();mark='struct nes_diag_input {FIL file;';assert fpga.count(mark)==1
programmer=fpga[fpga.index(mark):]
mock=r'''
enum nes_diag_error {NES_DIAG_FPGA_OPEN=20,NES_DIAG_FPGA_PROG,NES_DIAG_FPGA_INIT,NES_DIAG_FPGA_DONE,NES_DIAG_FPGA_READ,NES_DIAG_FPGA_FORMAT,NES_DIAG_FPGA_LIMIT,NES_DIAG_FPGA_CLOSE};
struct nes_diag_wait {unsigned polls;};
static struct diagnostic *nes_diag_status(void);
static struct nes_diag_wait nes_diag_wait_start(unsigned a,unsigned b){(void)a;(void)b;return (struct nes_diag_wait){0};}
static bool nes_diag_wait_step(struct nes_diag_wait *w){return ++w->polls<400;}
static void nes_diag_fail(enum nes_diag_error e){diagnostic.error=e;}
static FRESULT file_res;static uint8_t gbc_spi_pacing;static const uint8_t *fpga_config;
static unsigned prog_pin,done_pin,pin_mask,clock_count,programmed;
#define FPGA_PROGBREG 0
#define FPGA_PROGBBIT 0
#define BITBAND(v,b) (prog_pin)
#define FPGA_DIN_MASK() (pin_mask=1)
#define FPGA_DIN_UNMASK() (pin_mask=0)
#define FPGA_SEND_BYTE_SERIAL(v) do {assert(pin_mask);(void)(v);programmed++;} while(0)
#define CCLK() do {if(++clock_count==3 && !(scenario==BASE_FAILURE && config_count==2))done_pin=1;} while(0)
#define RLE_ESC 0x9b
#define RLE_RUN 0x5b
#define RLE_RUNLONG 0x77
static void fpga_init(void){config_count++;clock_count=programmed=0;}
static void fpga_postinit(void){assert(programmed==263);}
static void fpga_set_prog_b(int v){prog_pin=v;if(!v)done_pin=0;}
static int fpga_get_initb(void){return prog_pin;}
static int fpga_get_done(void){return done_pin;}
'''
src=once(src,'static bool nes_diag_fpga_pgm(const uint8_t *p){(void)p;config_count++;return !(scenario==BASE_FAILURE&&config_count==2);}',mock+programmer)
generated=out.parent/(out.name+'-loader.c');generated.write_text(src,newline='\n')
disk=(ROOT/'tests/nes-nrom408/fat_disk.c').read_text();anchor=' memcpy(media+DATA_SECTOR*512u,file,bytes);'
disk=once(disk,anchor,anchor+'''
 word(fat+51*2,0xffff);
 uint8_t *base=dir+32,*image=dir+64;
 memcpy(base,"BASE       ",11);base[11]=0x20;word(base+26,51);dword(base+28,10);
 memcpy(image,"NROM    BI3",11);image[11]=0x20;word(image+26,51);dword(image+28,10);
 const uint8_t config[]={1,0x5b,0xa4,3,0x9b,0x9b,0x77,0x66,2,1};
 memcpy(media+(DATA_SECTOR+49)*512u,config,sizeof(config));''')
diskpath=out.parent/(out.name+'-disk.c');diskpath.write_text(disk,newline='\n')
runner=(ROOT/'tools/test_nes_nrom408_fatfs.py').read_text()
runner=once(runner,"str(tests/'full_tb.c')",'str(Path('+repr(str(generated))+'))')
runner=once(runner,"sha(tests/'full_tb.c')",'sha(Path('+repr(str(generated))+'))')
runner=once(runner,"str(tests/'fat_disk.c')",'str(Path('+repr(str(diskpath))+'))')
runner=once(runner,"sha(tests/'fat_disk.c')",'sha(Path('+repr(str(diskpath))+'))')
runner=once(runner,"'scope':'full generated 227 loader + byte-identical 227 FatFS on synthetic FAT16, modeled SPI/PSRAM and run/base, no FPGA RTL cosimulation or physical hardware'", "'scope':'actual loader and programmer + actual FatFS; synthetic FPGA bitstream and modeled GPIO/SPI/PSRAM/run, no FPGA RTL cosimulation or ARM execution'")
sys.argv=['test_nes_nrom408_fatfs.py','--build',str(a.build),'--out',str(out)]
exec(compile(runner,str(ROOT/'tools/test_nes_nrom408_fatfs.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom408_fatfs.py')})
