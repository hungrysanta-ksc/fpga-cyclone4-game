# SPDX-License-Identifier: MIT
"""Actual embedded legacy streams + bounded080 boot/platform over host IO."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from nes_report080_prepare import PIN
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ['evidence079','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mode',choices=['normal','no-compare','no-final-guard'],default='normal');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);o=a.out.resolve();e=a.evidence079.resolve()
 assert sha(e/'manifest.json')==PIN;m=json.loads((e/'manifest.json').read_bytes())['files'];inputs={}
 def copy(n,target=None):
  k='work/arm-03/source/src/'+n;assert sha(e/k)==m[k];inputs[k]=m[k];shutil.copy2(e/k,o/(target or n))
 for n in ['nes_diag_runtime.c','nes_diag_runtime.h','nes_menu_return.c','nes_menu_return.h','nes_menu076.h','smc.h','nes_sd_inventory.h','nes_sd_fault074.h','rle.c','rle.h','snesboot.h']:copy(n)
 copy('obj-report079/cfgware.h','cfgware.h')
 s=(o/'nes_menu_return.c').read_text();(o/'nes_menu_return.c').write_text(s[:s.index('uint32_t nes_return_copy_menu(')],encoding='utf-8')
 for n in ['nes_report_boot080.c','nes_report_boot080.h','nes_report_decode080.c','nes_report_platform080.c']:shutil.copy2(ROOT/'src/nes/firmware'/n,o/n)
 if a.mode=='no-compare':
  f=o/'nes_report_boot080.c';s=f.read_text();assert s.count('||memcmp(back,b->bytes,n)')==1;f.write_text(s.replace('||memcmp(back,b->bytes,n)',''),encoding='utf-8')
 if a.mode=='no-final-guard':
  f=o/'nes_report_platform080.c';s=f.read_text();assert s.count('if(result==8||nes_return_failed())return false;')==1;f.write_text(s.replace('if(result==8||nes_return_failed())return false;','nes_return_reset(); /* forbidden fault clear */'),encoding='utf-8')
 headers={
 'config.h':'''#ifndef MOCK080_CONFIG
#define MOCK080_CONFIG
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
#include <crtdbg.h>
#endif
struct fake_nvic {uint32_t ISER[8];};
extern struct fake_nvic nvic;
#define NVIC (&nvic)
#define OTG_FS_IRQn 67
#define NVIC_DisableIRQ(x) (nvic.ISER[(x)>>5]&=~(1u<<((x)&31)))
#define __NOP() ((void)0)
#define BITBAND(r,p) read_prog()
#define FPGA_SEND_BYTE_SERIAL(b) send_byte(b)
#define FPGA_DIN_MASK() ((void)0)
#define FPGA_DIN_UNMASK() ((void)0)
unsigned read_prog(void);
void send_byte(uint8_t);
#endif
''',
 'fileops.h':'#include <stdint.h>\nextern int file_res,file_status;\n#define FR_OK 0\nuint8_t file_getc(void);\n',
 'bits.h':'/* GPIO modeled in config */\n',
 'fpga.h':'#include <stdint.h>\n#define FPGA_ROM ((const uint8_t*)"rom")\nvoid fpga_init(void);\nvoid fpga_set_prog_b(uint8_t);\nint fpga_get_initb(void);\nint fpga_get_done(void);\nvoid fpga_postinit(void);\n',
 'fpga_spi.h':'#include <stdint.h>\nvoid set_saveram_mask(uint32_t);\nvoid set_rom_mask(uint32_t);\nvoid set_mapper(uint8_t);\n',
 'memory.h':'#include <stdint.h>\n#define SRAM_MENU_ADDR 0xc00000u\n#define SRAM_CMD_ADDR 0xff1000u\nuint16_t sram_writeblock(void *,uint32_t,uint16_t);\nuint16_t sram_readblock(void *,uint32_t,uint16_t);\n',
 'snes.h':'#include <stdint.h>\nvoid snes_reset(int);\nuint8_t get_snes_reset(void);\n',
 }
 for n,s in headers.items():(o/n).write_text(s,encoding='utf-8')
 shutil.copy2(ROOT/'tests/nes-functional/report_boot080_host.c',o/'host.c');shutil.copy2(__file__,o/'executed-driver.py')
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I.','host.c','rle.c','nes_diag_runtime.c','nes_menu_return.c','nes_report_decode080.c','nes_report_boot080.c','nes_report_platform080.c','-o','host.exe']
 with (o/'compile.log').open('wb') as f:subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (o/'run.log').open('wb') as f:r=subprocess.run([str(o/'host.exe')],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=90)
 log=(o/'run.log').read_text(errors='replace')
 if a.mode=='normal':assert r.returncode==0 and 'PASS080' in log,log[-1500:]
 else:
  needle='!report_boot080()&&held&&nes_return_failed()&&io==n' if a.mode=='no-compare' else '!run_session()&&held&&nes_return_failed()&&io==all_io+4'
  assert r.returncode!=0 and 'Assertion' in log and needle in log,log[-1500:]
 result=dict(mode=a.mode,exit=r.returncode,inputs=inputs,physical=False,files={p.name:sha(p) for p in o.iterdir() if p.is_file()})
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(log[-400:])
if __name__=='__main__':main()
