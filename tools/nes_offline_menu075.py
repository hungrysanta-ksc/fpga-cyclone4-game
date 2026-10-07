# SPDX-License-Identifier: MIT
"""Run actual smc_id/sgb_id on received menu; guarded variant is HOST ONLY."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
from nes_diag_recovery_checks import function
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):assert s.count(a)==1,a;return s.replace(a,b,1)
def main():
 p=argparse.ArgumentParser();p.add_argument('--platform',type=Path,required=True);p.add_argument('--menu',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 assert sha(a.menu)=='f53b777a0bbe37668cd88cf8c80c5e5a0a60f861f58d1d4d3d9b082e9d1b4325'
 a.out.mkdir(parents=True,exist_ok=False);out=a.out.resolve();src=a.platform.resolve()
 def write(n,s):(out/n).write_text(s,encoding='utf-8',newline='\n')
 pins={n:sha(src/n) for n in ['smc.c','smc.h','sgb.c','sgb.h','fpga.h','fpga_spi.h','memory.c']}
 for n in pins:shutil.copy2(src/n,out/('input-'+n))
 for n in ['smc.h','sgb.h']:shutil.copy2(src/n,out/n)
 write('fileops.h','#include <stdint.h>\n#include <stdio.h>\nstruct file_mock {uint32_t fsize;};extern struct file_mock file_handle;extern unsigned file_res;uint32_t file_readblock(void *,uint32_t,unsigned);typedef unsigned UINT;\n')
 write('cfg.h','typedef struct {unsigned cx4_speed,gsu_speed,sgb_bios_version,sgb_volume_boost,sgb_enh_override,sgb_spr_increase,sgb_clock_fix;} cfg_t;\n')
 write('config.h','#include <stdint.h>\n#include <stdio.h>\n#define FPGA_CONF_EXT "bi3"\n')
 write('snes.h','#define MENU_ERR_NOIMPL 3\n')
 for n in ['uart.h','memory.h']:write(n,'/* no hardware execution */\n')
 for n,pattern in [('fpga.h',r'^#define FPGA_\w+ .*'),('fpga_spi.h',r'^#define FEAT_.*')]:
  write(n,'\n'.join(re.findall(pattern,(src/n).read_text(),re.M))+'\n')
 smc=(src/'smc.c').read_text();write('smc-actual.c',smc)
 sgb=(src/'sgb.c').read_text();start=sgb.index('void sgb_id(')
 # Keep original notice and exact full function, omit unrelated launch code.
 write('sgb-id.c',sgb[:sgb.index('#include')]+'''#include "fileops.h"
#include "config.h"
#include "smc.h"
#include "sgb.h"
#include "cfg.h"
#include <string.h>
#include <strings.h>
extern cfg_t CFG;
sgb_romprops_t sgb_romprops;char SGBFW[30],SGBSR[30];
uint32_t crc32_update(uint32_t,uint8_t);
'''+function(sgb[start:],'sgb_id'))
 memory=(src/'memory.c').read_text();m=re.search(r'if\(nes_diag_active\(\)&&\((nes_return_failed\(\).*?)\)\)\{nes_return_fail\(NES_DIAG_MENU\);return 0;\}',memory)
 assert m and 'romprops.header.carttype>2' in m[1]
 write('actual-return-gate.inc','static unsigned actual_return_rejected(uint32_t filesize){return '+m[1]+';}\n')
 guarded=once(smc,'uint8_t ext_coprocessor=0;','uint8_t ext_coprocessor=0, found_header=0;')
 guarded=once(guarded,'      score_idx=num;','      found_header=1;\n      score_idx=num;')
 guarded=once(guarded,'  if(score_idx & 1) {','  if(!found_header){props->error=MENU_ERR_NOIMPL;return;}\n  if(score_idx & 1) {')
 guarded=once(guarded,'  file_readblock(header, hdr_addr[score_idx] + file_offset, sizeof(snes_header_t));','  if(file_readblock(header, hdr_addr[score_idx] + file_offset, sizeof(snes_header_t))!=sizeof(snes_header_t)||file_res){props->error=MENU_ERR_NOIMPL;return;}\n  if(header->ramsize>21||header->expramsize>21){props->error=MENU_ERR_NOIMPL;return;}')
 guarded=once(guarded,'  uint8_t reset_inst;','  uint8_t reset_inst=0;')
 guarded=once(guarded,'  file_readblock(&reset_inst, file_addr + file_offset, 1);','  if(file_readblock(&reset_inst, file_addr + file_offset, 1)!=1||file_res)return 0;')
 write('smc-guarded.c',guarded)
 shutil.copy2(ROOT/'tests/nes-functional/offline_menu075_host.c',out/'host.c');shutil.copy2(__file__,out/'executed-driver.py')
 results={}
 for name,flags in [('actual',[]),('guarded',['-DGUARDED_CLASSIFIER'])]:
  with (out/(name+'-compile.log')).open('wb') as log:
   subprocess.run([str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-error=implicit-fallthrough','-Wno-format','-I.',*flags,'host.c','smc-'+name+'.c','sgb-id.c','-o',name+'.exe'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
  with (out/(name+'.log')).open('wb') as log:r=subprocess.run([str(out/(name+'.exe')),str(a.menu.resolve())],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=30)
  text=(out/(name+'.log')).read_text();assert r.returncode==0 and 'current_gate=REJECT' in text and 'PASS075' in text,text
  results[name]=dict(checks=int(re.search(r'checks=(\d+)',text)[1]),exit=r.returncode)
 write('result.json',json.dumps(dict(menu_sha256=sha(a.menu),sources=pins,results=results,physical=False,production_modified=False),indent=2)+'\n')
 print('PASS075 actual menu rejected by current carttype gate; '+json.dumps(results))
if __name__=='__main__':main()
