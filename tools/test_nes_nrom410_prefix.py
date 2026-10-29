# SPDX-License-Identifier: MIT
"""Bounded DPI connection test: loader/FatFS to actual FPGA, 16 bytes only."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from nes_delta231 import BASE, ROOT, sha

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--limit',type=int,default=16)
a=p.parse_args();d=a.out.resolve();build=a.build.resolve()
assert 0<a.limit<=16384
assert d.as_posix().isascii() and not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
d.mkdir(parents=True)
prod=BASE/'probes/nes-repeat227/arm01/src';board=BASE/'probes/nes-repeat227/asm02';host=BASE/'probes/nes-run136/evidence/initial/host04'
for f in host.glob('*.h'):shutil.copyfile(f,d/f.name)
for n in ('ff.c','ff.h','ffconf.h','diskio.h'):
 assert sha(host/n)==sha(prod/n);shutil.copyfile(prod/n,d/n)
(d/'unicode').mkdir();shutil.copyfile(prod/'ccsbcs.c',d/'unicode/ccsbcs.c')
s=(build/'nes_h1_stm32.c').read_text()
(d/'full408.inc').write_text(s[s.index('static uint32_t load_crc('):s.index('\nbool nes_mcu_load_probe(')]+'\n'+s[s.index('static bool sd_query('):s.index('\n\n#include "nes_cf86_session094.h"')]+'\n'+s[s.index('bool nes_menu_sd_probe('):],newline='\n')
source=(ROOT/'tests/nes-nrom408/full_tb.c').read_text()
source=source[:source.index('bool nes_game149_transfer(')]+r'''
#include <windows.h>
static HANDLE request_sem,response_sem,worker;
static uint64_t request_frame,response_frame;
static volatile int done,worker_code;
static unsigned sent_data;
bool nes_game149_transfer(const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8]){
 (void)io;if(sticky)return false;
 if(tx[0]==NES_ROM_DATA && sent_data==TEST_LIMIT)return false;
 if(tx[0]==NES_ROM_DATA)sent_data++;
 request_frame=0;for(int i=0;i<8;i++)request_frame=(request_frame<<8)|tx[i];
 ReleaseSemaphore(request_sem,1,0);
 if(WaitForSingleObject(response_sem,30000)!=WAIT_OBJECT_0)return false;
 for(int i=7;i>=0;i--){rx[i]=(uint8_t)response_frame;response_frame>>=8;}
 return true;
}
''' + source[source.index('static void fresh('):source.index('int main(void)')]+r'''
static DWORD WINAPI execute(LPVOID unused){
 (void)unused;struct nes_menu_probe_report p;fresh(OK);
 bool safe=nes_menu_sd_probe("nrom.nes","nrom.bi3",false,&p);
 worker_code=(safe || p.sd.verified || sent_data!=TEST_LIMIT || !sticky || irq_count!=0);
 done=1;ReleaseSemaphore(request_sem,1,0);return 0;
}
__declspec(dllexport) void start_worker(void){
 request_sem=CreateSemaphoreA(0,0,1,0);response_sem=CreateSemaphoreA(0,0,1,0);
 worker=CreateThread(0,0,execute,0,0,0);
}
__declspec(dllexport) int next_request(uint64_t *tx){
 if(WaitForSingleObject(request_sem,30000)!=WAIT_OBJECT_0)return -1;
 if(done)return 0;*tx=request_frame;return 1;
}
__declspec(dllexport) void submit_response(uint64_t rx){response_frame=rx;ReleaseSemaphore(response_sem,1,0);}
__declspec(dllexport) int worker_result(void){return worker_code;}
'''
(d/'bridge.c').write_text(source,newline='\n')
shutil.copyfile(build/'nes_rom_spi.sv',d/'candidate.sv')
for n in ('nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv'):shutil.copyfile(board/n,d/n)
shutil.copyfile(ROOT/'tests/nes-nrom410/prefix_tb.sv',d/'prefix_tb.sv')
questa=Path('C:/altera_standard/25.1std/questa_fse');gcc=questa/'gcc-7.4.0-mingw64vc16/bin/gcc.exe';bin=questa/'win64'
steps=[('compile',[str(gcc),'-shared','-std=c99','-O2','-Wno-unused-function','-DNROM_USE_FATFS',f'-DTEST_LIMIT={a.limit}','-I',str(d),'-I',str(build),'-I',str(prod),str(d/'ff.c'),str(d/'unicode/ccsbcs.c'),str(build/'nes_rom_verify.c'),str(prod/'nes_rom_spi.c'),str(build/'nes_nrom406.c'),str(ROOT/'tests/nes-nrom408/fat_disk.c'),str(d/'bridge.c'),'-o',str(d/'bridge.dll')]),('vlib',[str(bin/'vlib.exe'),'work']),('vlog',[str(bin/'vlog.exe'),'-sv',f'+define+TEST_LIMIT={a.limit}','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','prefix_tb.sv']),('simulation',[str(bin/'vsim.exe'),'-c','-sv_lib','bridge','work.prefix_tb','-do','onerror {quit -code 1};run -all;quit -f'])]
for label,cmd in steps:
 with (d/(label+'.log')).open('wb') as f:r=subprocess.run(cmd,cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(d/(label+'.log')).read_text(errors='replace')[-5000:]
log=(d/'simulation.log').read_text(errors='replace')
assert f'PASS NROM410 real C/FatFS to real RTL prefix bytes={a.limit}' in log and 'Errors: 0, Warnings: 0' in log,log[-5000:]
result={'passed':True,'prefix_bytes':a.limit,'scope':'deliberately aborted before full load, actual 227 loader/FatFS host C to actual FPGA SPI/boot/loader and PSRAM pin model; no complete CRC/readback/START/STOP/base recovery or ARM execution', 'bench':sha(d/'prefix_tb.sv'),'bridge':sha(d/'bridge.c'),'SPI':sha(build/'nes_rom_spi.sv')}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
