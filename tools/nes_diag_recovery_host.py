# SPDX-License-Identifier: MIT
"""064 actual upper C menu/full SPI capture; SD/programmer/GPIO are mocks.
Together with lower helper tests; never claimed as an actual SD-card run.
"""
from pathlib import Path
import argparse,shutil,json
from nes_diag_recovery import materialize
from nes_menu_diagnostic import host_source
from nes_board_session import platform as session_platform
from nes_mcu_loader import ROOT,sha,run
from build_nes_video_workloads import build

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);p.add_argument('--session',action='store_true');p.add_argument('--reference',type=Path);a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);materialize(out);shutil.copy2(__file__,out/'executed-driver.py')
 s=(session_platform() if a.session else host_source()).replace('062','064')
 s='#include "nes_diag_runtime.h"\nstatic bool native_sd_fault;static unsigned inject_native;\n'+s
 s=s.replace('read_calls++;','read_calls++;if(inject_native&&(inject_native==1||pass==1)){native_sd_fault=true;nes_diag_fail(NES_DIAG_SD_DATA);*got=0;return 1;}')
 s+='''
#include "nes_diag_runtime.h"
static unsigned progress_calls,progress_phases;
uint32_t nes_diag_ticks(void){return getticks();}
void nes_diag_sd_reset(void){native_sd_fault=false;}
bool nes_diag_sd_failed(void){return native_sd_fault;}
void nes_diag_observe(const struct nes_diag_report *r,bool active){
 if(active){assert(!irq&&reset_held&&r->completed<=r->total);progress_calls++;progress_phases|=1u<<r->phase;}
}
bool nes_diag_fpga_pgm(const uint8_t *p){fpga_pgm((uint8_t*)p);return file_res==FR_OK;}
'''
 name='session-platform.c' if a.session else 'sd-platform.c';(out/name).write_text(s,encoding='utf-8',newline='\n')
 host='board_session_host.c' if a.session else 'menu_diagnostic_host.c'
 s=(ROOT/'tests/nes-functional'/host).read_text().replace('062','064')
 if a.session:
  s=s.replace(' assert(begin_count==1',' assert(!nes_diag_active()&&(progress_phases&0x3e)==0x3e&&progress_calls>100);\n assert(begin_count==1')
 else:
  s=s.replace('  assert(safe==(f!=BASE_TOKEN));','  assert(safe==(f!=BASE_TOKEN));\n  assert(nes_diag_active()==!safe);')
  s=s.replace(' assert(sd_regression(argc,argv)==0);',''' assert(sd_regression(argc,argv)==0);
 for(unsigned n=1;n<=2;n++){
  initialize(NONE,1);inject_native=n;struct nes_menu_probe_report candidate;
  assert(!nes_menu_sd_probe("fixture","approved-test-image",original_length==98320,&candidate));
  assert(!irq&&reset_held&&native_sd_fault&&nes_diag_active()&&configs==(n==2)&&!candidate.sd.load.recovery_attempted);
  assert(!candidate.sd.verified&&nes_diag_status()->phase==NES_DIAG_BLOCKED);
 }
 inject_native=0;nes_diag_leave();
 printf("PASS RECOVERY064 native_error_protection=2 no_SD_base_retry=1\\n");''')
 (out/host).write_text(s,encoding='utf-8',newline='\n')
 shutil.copy2(ROOT/'tests/nes-functional/mcu_loader_platform.h',out/'mcu_loader_platform.h')
 for n in ['config','bits','timer','snes','fpga','fpga_spi','fileops','uart']:(out/(n+'.h')).write_text('#include "mcu_loader_platform.h"\n')
 for c in ['fine_x','banks32']:build(out/c,c)
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','nes_rom_spi.c','nes_rom_verify.c','nes_h1_stm32.c','nes_h1_session.c','nes_menu_diagnostic.c','nes_diag_runtime.c',host,'-o','host.exe'],out,'compile')
 log=run([out/'host.exe',out/'fine_x/mmc3.nes',out/'banks32/mmc3.nes',out/('fine_x.trace' if a.session else 'waveform.txt'),out/('banks32.trace' if a.session else 'load-waveform.txt')],out,'host')
 markers=[line for line in log.splitlines() if line.startswith('PASS SESSION C') or line.startswith('PASS MENU064')]
 assert len(markers)==(2 if a.session else 1)
 traces={c:sha(out/(c+'.trace')) for c in ['fine_x','banks32']} if a.session else {}
 if a.reference:
  assert a.session
  for c,h in traces.items():assert h==sha(a.reference/(c+'.trace')),c
 (out/'result.json').write_text(json.dumps(dict(candidate='NES-DIAG-RECOVERY-064',actual_stm32_execution=False,markers=markers,session=a.session,
  traces=traces,reference_identical=bool(a.reference),files={f.name:sha(f) for f in out.iterdir() if f.is_file() and f.suffix in ['.c','.h','.log']}),indent=2)+'\n')
 print('\n'.join(markers))
if __name__=='__main__':main()
