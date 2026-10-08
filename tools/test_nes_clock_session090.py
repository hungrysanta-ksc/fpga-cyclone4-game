# SPDX-License-Identifier: MIT
"""One production090 session, pinned084 actual native SD/FatFS/mini/runtime.
Only GPIO/card/CRC assembly/SRAM/time are modeled; no hardware claim.
"""
from pathlib import Path
import argparse,json,re,shutil
from nes_spi_boot import ROOT,put,run,sha
from check_nes_clock_report090 import check as check_text
PIN='1a43873e74e8a5cc888d099874d9ff17caa6959b4b12ffdd53a9d0987100a3d5'
PIN089='9f1a6a39c0b1d39b725d6f85a04653736ab77a06091986e398a85d1102914018'
def replace(s,a,b):assert s.count(a)==1,a;return s.replace(a,b)
def fun(s,name,new):
 m=re.search(r'^(?:static )?(?:bool|void|int|unsigned|uint8_t) '+name+r'\([^;{}]*\)\s*\{',s,re.M);assert m,name
 start=m.start();i=m.end();depth=1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[:start]+new+s[i:]
def main():
 p=argparse.ArgumentParser()
 for n in ['out','evidence084','evidence089','gcc']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mutation',choices=['skip-reader','clear-reader-fault','skip-readback','skip-rehold'])
 a=p.parse_args();o=a.out.resolve();e=a.evidence084.resolve();e89=a.evidence089.resolve();assert str(o).isascii()
 assert sha(e/'manifest.json')==PIN and sha(e89/'manifest.json')==PIN089;o.mkdir(parents=True,exist_ok=False)
 pins=json.loads((e/'manifest.json').read_bytes())['files'];inputs={};prefix='work/normal-05/'
 for n,h in pins.items():
  if n.startswith(prefix) and Path(n).suffix in ['.c','.h','.inc'] and not n.endswith(('timer-host.c','input-timer.c')):
   assert sha(e/n)==h;dest=o/n[len(prefix):];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,dest);inputs[n]=h
 for n in ['nes_clock_config089.c','nes_clock_config089.h','nes_clock_reader088.c','nes_clock_reader088.h','nes_clock_platform090.c','nes_clock_report090.h','nes_clock_text090.c']:shutil.copy2(ROOT/'src/nes/firmware'/n,o/n)
 m89=json.loads((e89/'manifest.json').read_bytes())['files']
 for n,target in [('asm01/clock089_payload.h','clock089_payload.h'),('asm01/output_files/board.rbf','clock087.rbf')]:
  assert sha(e89/n)==m89[n];shutil.copy2(e89/n,o/target)
 q=o/'nes_sd_inventory_log.c';put(q,replace(q.read_text(),'/HW084','/HW090'))
 q=o/'config.h';s=q.read_text();s=replace(s,'#define BITBAND(r,p) read_prog()','#define BITBAND(r,p) ((p)==4?model_input():read_prog())')
 add='''
struct gpio088 {uint32_t MODER,ODR,IDR;};struct spi088 {uint32_t CR1,SR;};
extern struct gpio088 gpio_b,gpio_ss;extern struct spi088 spi;
#define GPIOB (&gpio_b)
#define FPGA_SSREG (&gpio_ss)
#define FPGA_SSBIT 0
#define FPGA_PROGBBIT 1
#define SPI1 (&spi)
#define SPI_SR_BSY 128u
#define SPI_SR_TXE 2u
#define SPI_CR1_SPE 64u
void model_set(struct gpio088 *,unsigned,unsigned);unsigned model_input(void);void model_cclk(void);
#define CCLK() model_cclk()
'''
 put(q,s+add);put(o/'bits.h','#define SET_BIT(r,p) model_set(r,p,1)\n#define CLEAR_BIT(r,p) model_set(r,p,0)\n')
 q=o/'fpga.h';put(q,q.read_text()+'void fpga_set_cclk(uint8_t);\n')
 # Extend the original084 platform hardware seams; production remains actual.
 q=o/'platform-model.h';s=q.read_text().replace('report_session084','report_session090')
 s=replace(s,'bool report_session090(void);','bool report_session090(void);\n#include "probe-model.h"')
 s=fun(s,'snes_reset','''void snes_reset(int n){
 if(!n){
  assert(!nes_return_failed()&&snes_boot_configured&&!nvic.ISER[2]);
  assert(stage>=1&&stage<=9);release_mask|=1u<<stage;
  if(stage==1){
   assert(!nes_return_log_allowed());
   if(!clock_marker){assert(clock_cycle==1&&!init_commands&&row(8,"STEP 1A OBSERVE CLOCK"));clock_marker=1;}
   else if(!init_commands){assert(clock_cycle==3&&marker_mask==0&&row(8,"STEP 1B INIT SD"));marker_mask=1;}
   else if(marker_mask==1){assert(init_commands==17&&!commands&&row(8,"STEP 1C MOUNT FAT"));marker_mask=3;}
   else{assert(marker_mask==3&&commands&&fatfs.fs_type&&row(8,"STEP 1D FIND SPACE"));marker_mask=7;}
  }else if(stage<9)assert(nes_return_log_allowed());else assert(!nes_return_log_allowed());
 }
 held=(unsigned)n;
}''')
 s=fun(s,'fpga_init','''void fpga_init(void){assert(held&&!nes_return_failed()&&!commands&&!init_commands&&!fatfs.fs_type);clock_cycle++;assert(clock_cycle<=3);sent=clock_extra=0;}''')
 s=fun(s,'fpga_set_prog_b','void fpga_set_prog_b(uint8_t n){if(nes_return_failed())assert(!n);prog=n;}')
 s=fun(s,'fpga_get_initb','int fpga_get_initb(void){if(clock_cycle==2&&clock_status_fail&&sent>=clock_status_fail)return 0;return pinfault==2?0:(int)prog;}')
 s=fun(s,'fpga_get_done','int fpga_get_done(void){if(clock_cycle==2)return !clock_done_fail&&sent==510856&&clock_extra>=3;return pinfault==3?1:pinfault==4?0:sent==153544;}')
 s=fun(s,'send_byte','''void send_byte(uint8_t n){
 assert(held&&!nes_return_failed());
 if(clock_cycle==2){assert(sent<510856&&n==clock_raw[sent]);}else assert(sent<153544&&n==golden_mini[sent]);
 sent++;clock_us++;
}''')
 s=fun(s,'fpga_postinit','void fpga_postinit(void){assert(fpga_get_done());postinit++;configured=1;if(clock_cycle==2)clock_epoch=clock_us;}')
 old=s[s.index('bool nes_return_delay('):s.index('static bool touch(')]
 new=old.replace('if(!ms){assert(n==2&&held&&stage==1);assert(marker_mask==1);init_delays++;', '''if(!ms&&clock_cycle==2){assert(held&&stage==1&&!init_commands);if(clock_delay_fail){nes_return_fail(NES_DIAG_TIMER);return false;}clock_us+=n;}
 else if(!ms){assert(n==2&&held&&stage==1);assert(marker_mask==1);init_delays++;''').replace('assert(held&&sent==153544);','assert(held&&(sent==153544||sent==510856));clock_us+=1000;')
 s=replace(s,old,new);s=s.replace('marker_delay_fail==marker_mask','marker_delay_fail==(marker_mask?marker_mask:8)');s=s.replace('assert(held&&configured&&!nes_return_failed()&&!nvic.ISER[2]);io++;','assert(held&&configured&&clock_cycle!=2&&!nes_return_failed()&&!nvic.ISER[2]);io++;')
 put(q,s)
 q=o/'host.c';s=q.read_text();s=replace(s,'tick_origin+display_ticks+(tick_div?rises/tick_div:0)','tick_origin+display_ticks+(uint32_t)(clock_us/10000)+(tick_div?rises/tick_div:0)');put(q,s)
 # Keep only the existing power-on/card fixture initializer, then new090 tests.
 q=o/'session-tests.h';s=q.read_text();s=s[:s.index('static unsigned rd16')];s=replace(s,'static void reset_case(unsigned fat32,unsigned hc){','static void reset_case(unsigned fat32,unsigned hc){\n reset_clock090();')
 put(q,s+(ROOT/'tests/nes-functional/clock_session090_cases.h').read_text())
 shutil.copy2(ROOT/'tests/nes-functional/clock_session090_probe.h',o/'probe-model.h')
 if a.mutation:
  q=o/'nes_clock_platform090.c';s=q.read_text()
  if a.mutation=='skip-reader':s=replace(s,'!nes_clock_collect088(&report090)','false')
  if a.mutation=='clear-reader-fault':s=replace(s,'!nes_clock_collect088(&report090)||nes_return_failed()','(!nes_clock_collect088(&report090)?(nes_return_reset(),report090.result=CLOCK088_NO_PROGRESS,0):0)')
  if a.mutation=='skip-rehold':s=replace(s,' snes_reset(1);\n if(!get_snes_reset()', ' /* missing RESET rehold */\n if(!get_snes_reset()')
  put(q,s)
  if a.mutation=='skip-readback':q=o/'nes_sd_inventory_log.c';put(q,replace(q.read_text(),'memcmp(data,report+pos,n)','0'))
 shutil.copy2(__file__,o/'executed-driver.py')
 names=['host.c','ff.c','unicode/ccsbcs.c','rle.c','nes_diag_runtime.c','nes_menu_return.c','nes_sd_inventory_log.c','nes_report_checkpoint079.c','nes_report_disk081.c','nes_report_boot080.c','nes_report_decode080.c','nes_report_space084.c','nes_clock_config089.c','nes_clock_reader088.c','nes_clock_platform090.c','nes_clock_text090.c']
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-O2','-Wall','-Wextra','-Wno-format','-I.',*names,'-Wl,--wrap=nes_return_io_step','-Wl,--wrap=nes_return_log_allow','-o','host.exe'],o,'compile')
 try:log=run([o/'host.exe'],o,'host',300)
 except RuntimeError:
  if not a.mutation:raise
  log=(o/'host.log').read_text(errors='replace')
 if a.mutation:
  expected={'skip-reader':'report_session090()','clear-reader-fault':'!report_session090()','skip-readback':'TXT SAVE FAILED','skip-rehold':'report_session090()'}[a.mutation]
  assert 'Assertion' in log and expected in log,log[-1500:];result=dict(mutation=a.mutation,expected_failure=expected)
 else:
  m=re.search(r'PASS CLOCK_SESSION090 checks=(\d+)',log);assert m,log[-2000:]
  reports=[check_text(f) for f in sorted(o.glob('saved-*.txt'))];assert len(reports)==16
  result=dict(checks=int(m[1]),reports=reports,normal_rows=re.findall(r'NORMAL090[^\r\n]+',log))
 result.update(inputs=inputs,production={n:sha(o/n) for n in names if n!='host.c'},hardware=False,installable=False)
 put(o/'result.json',json.dumps(result,indent=2)+'\n');print(log[-2000:],flush=True)
if __name__=='__main__':main()
