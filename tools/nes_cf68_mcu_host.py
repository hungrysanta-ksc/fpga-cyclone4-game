# SPDX-License-Identifier: MIT
"""065 actual upper C menu/full SPI capture; SD/programmer/GPIO are mocks.
Together with lower helper tests; never claimed as an actual SD-card run.
"""
from pathlib import Path
import argparse,shutil,json,re
from nes_cf68_mcu import materialize
from nes_menu_diagnostic import host_source
from nes_board_session import platform as session_platform
from nes_mcu_loader import ROOT,sha,run
from build_nes_video_workloads import build

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);p.add_argument('--session',action='store_true');p.add_argument('--reference',type=Path);p.add_argument('--mutation',choices=['candidate','ready','fault-release']);a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);materialize(out);shutil.copy2(__file__,out/'executed-driver.py')
 shutil.copy2(ROOT/'tools/nes_cf68_mcu.py',out/'executed-materializer.py')
 if a.mutation:
  f=out/'nes_h1_stm32.c';v=f.read_text();old,new={'candidate':('if(rx[1]!=0x68)','if(false)'), 'ready':('if(!nes_return_spi_ready())','if(false)'), 'fault-release':('nes_diag_sd_failed()||nes_return_failed()','nes_diag_sd_failed()')}[a.mutation];assert v.count(old)==1;f.write_text(v.replace(old,new),encoding='utf-8',newline='\n')
 s=(session_platform() if a.session else host_source()).replace('062','069')
 s='#include "nes_diag_runtime.h"\n#include "nes_menu_return.h"\nstatic bool native_sd_fault;static unsigned inject_native,ready_calls,ready_fault;\n'+s
 s=s.replace('read_calls++;','read_calls++;if(inject_native&&(inject_native==1||pass==1)){native_sd_fault=true;nes_diag_fail(NES_DIAG_SD_DATA);*got=0;return 1;}')
 s=s.replace('static void initialize(enum fault f,unsigned enabled) {','static void initialize(enum fault f,unsigned enabled) {\n ready_calls=0;')
 s=s.replace('identity_fault==3?0x44:', 'identity_fault==6?0x61:identity_fault==7?0x67:identity_fault==3?0x44:').replace('fault==ID?0x60:0x61','fault==ID?0x60:0x68')
 s=re.sub(r'\bframes\+\+;', 'assert(ready_calls==1);frames++;',s)
 s=s.replace('fpga_nlv.bi3','fpga_nl8.bi3')
 s+='''
#include "nes_diag_runtime.h"
static unsigned progress_calls,progress_phases;
uint32_t nes_diag_ticks(void){return getticks();}
void nes_diag_sd_reset(void){native_sd_fault=false;}
bool nes_diag_sd_failed(void){return native_sd_fault;}
void nes_diag_observe(const struct nes_diag_report *r,bool active){
 if(active){assert(!irq&&reset_held&&r->completed<=r->total);progress_calls++;progress_phases|=1u<<r->phase;}
}
bool nes_return_spi_ready(void){assert(configs==1&&!irq&&reset_held&&!frames&&mock_b.MODER==mode_before&&mock_spi.CR1==cr1_before);ready_calls++;if(ready_fault){nes_return_fail(NES_DIAG_SPI);return false;}return true;}
uint16_t sram_readblock(void *p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}
uint16_t sram_writeblock(void *p,uint32_t a,uint16_t n){(void)p;(void)a;(void)n;assert(0);return 0;}
bool nes_diag_fpga_pgm(const uint8_t *p){fpga_pgm((uint8_t*)p);return file_res==FR_OK;}
'''
 name='session-platform.c' if a.session else 'sd-platform.c';(out/name).write_text(s,encoding='utf-8',newline='\n')
 host='board_session_host.c' if a.session else 'menu_diagnostic_host.c'
 s=(ROOT/'tests/nes-functional'/host).read_text().replace('062','069').replace('NES-MENU-DIAGNOSTIC-069','NES-CF68-MCU-069')
 if a.session:
  s=s.replace('irq==1&&reset_held','irq==0&&nes_diag_active()&&reset_held')
  s=s.replace(' assert(begin_count==1',' assert(nes_diag_active()&&(progress_phases&0x3e)==0x3e&&progress_calls>100);\n assert(begin_count==1')
 else:
  s=s.replace('irq==enabled&&log_attempts==1','irq==0&&nes_diag_active()&&log_attempts==1')
  s=s.replace('log_attempts==2&&irq==enabled','log_attempts==1&&!nes_diag_active()&&irq==enabled')
  s=s.replace('log_closes==2&&strstr(last_log,"menu_state=RELEASE_BOUNDARY_REACHED")','log_closes==1&&strstr(last_log,"menu_state=PREPARED_RESET_HELD")')
  s=s.replace('  assert(safe==(f!=BASE_TOKEN));','  assert(safe==(f!=BASE_TOKEN));\n  assert(nes_diag_active());')
  s=s.replace(' assert(sd_regression(argc,argv)==0);',''' assert(sd_regression(argc,argv)==0);
 for(unsigned old=6;old<=7;old++){
  initialize(NONE,1);identity_fault=old;struct nes_menu_probe_report r;
  assert(nes_menu_sd_probe("fixture","approved-test-image",original_length==98320,&r));
  assert(r.board_seen&&r.board_id==(old==6?0x61:0x67)&&!begin_count&&!count&&configs==2&&reset_held);
 }
 initialize(NONE,1);identity_fault=0;ready_fault=1;struct nes_menu_probe_report early;
 assert(!nes_menu_sd_probe("fixture","approved-test-image",original_length==98320,&early));
 assert(!frames&&!begin_count&&!count&&configs==1&&!early.board_seen&&!early.sd.load.recovery_attempted&&!irq&&reset_held&&nes_diag_active());
 ready_fault=0;nes_return_reset();nes_diag_leave();
 printf("PASS CF68 extra_old_ids=2 ready_fault_no_GPIO_or_base=1\\n");
 for(unsigned n=1;n<=2;n++){
  initialize(NONE,1);inject_native=n;struct nes_menu_probe_report candidate;
  assert(!nes_menu_sd_probe("fixture","approved-test-image",original_length==98320,&candidate));
  assert(!irq&&reset_held&&native_sd_fault&&nes_diag_active()&&configs==(n==2)&&!candidate.sd.load.recovery_attempted);
  assert(!candidate.sd.verified&&nes_diag_status()->phase==NES_DIAG_BLOCKED);
 }
 inject_native=0;nes_diag_leave();
 printf("PASS RECOVERY069 native_error_protection=2 no_SD_base_retry=1\\n");''')
 (out/host).write_text(s,encoding='utf-8',newline='\n')
 shutil.copy2(ROOT/'tests/nes-functional/mcu_loader_platform.h',out/'mcu_loader_platform.h')
 for n in ['config','bits','timer','snes','fpga','fpga_spi','fileops','uart']:(out/(n+'.h')).write_text('#include "mcu_loader_platform.h"\n')
 (out/'memory.h').write_text('#include "mcu_loader_platform.h"\nuint16_t sram_writeblock(void *,uint32_t,uint16_t);\nuint16_t sram_readblock(void *,uint32_t,uint16_t);\n')
 for c in ['fine_x','banks32']:build(out/c,c)
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','nes_rom_spi.c','nes_rom_verify.c','nes_h1_stm32.c','nes_h1_session.c','nes_menu_diagnostic.c','nes_diag_runtime.c','nes_menu_return.c',host,'-o','host.exe'],out,'compile')
 command=[out/'host.exe',out/'fine_x/mmc3.nes',out/'banks32/mmc3.nes',out/('fine_x.trace' if a.session else 'waveform.txt'),out/('banks32.trace' if a.session else 'load-waveform.txt')]
 if a.mutation:
  import subprocess
  with (out/'host.log').open('wb') as f:cp=subprocess.run([str(x) for x in command],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  log=(out/'host.log').read_text(errors='replace');target={'candidate':'candidate.board_seen&&candidate.board_id==0x60&&begin_count==0&&count==0','ready':'ready_calls==1','fault-release':'!nes_menu_sd_probe'}[a.mutation]
  assert cp.returncode!=0 and target in log,log[-2000:]
  (out/'result.json').write_text(json.dumps(dict(candidate='NES-CF68-MCU-069',mutation=a.mutation,expected_failure=True,assertion=target,files={f.name:sha(f) for f in out.iterdir() if f.is_file() and f.suffix in ['.c','.h','.log']}),indent=2)+'\n');print('PASS expected failure '+a.mutation);return
 log=run(command,out,'host')
 markers=[line for line in log.splitlines() if line.startswith('PASS SESSION C') or line.startswith('PASS MENU069')]
 assert len(markers)==(2 if a.session else 1)
 traces={c:sha(out/(c+'.trace')) for c in ['fine_x','banks32']} if a.session else {}
 if a.reference:
  assert a.session
  for c,h in traces.items():assert h==sha(a.reference/(c+'.trace')),c
 (out/'result.json').write_text(json.dumps(dict(candidate='NES-CF68-MCU-069',actual_stm32_execution=False,markers=markers,session=a.session,
  traces=traces,reference_identical=bool(a.reference),fixtures={c:sha(out/c/'mmc3.nes') for c in ['fine_x','banks32']},waveform_sha256=sha(out/'waveform.txt') if (out/'waveform.txt').exists() else None,load_waveform_sha256=sha(out/'load-waveform.txt') if (out/'load-waveform.txt').exists() else None,files={f.name:sha(f) for f in out.iterdir() if f.is_file() and f.suffix in ['.c','.h','.log']}),indent=2)+'\n')
 print('\n'.join(markers))
if __name__=='__main__':main()
