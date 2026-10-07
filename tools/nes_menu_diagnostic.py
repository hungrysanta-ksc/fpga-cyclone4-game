# SPDX-License-Identifier: MIT
"""062 manual menu integration derived from frozen060; no installable image."""
from pathlib import Path
import argparse, json, shutil
from nes_sd_readback import source as source060, materialize as materialize060
from nes_mcu_loader import ROOT, FW, sha, run, source as source056
from build_nes_video_workloads import build

def replace(s,old,new,count=1):
 assert s.count(old)==count,repr(old)
 return s.replace(old,new)

def source():
 prefix=source056()
 s=source060()
 assert s.startswith(prefix)
 s=s[len(prefix):]
 s=replace(s,'bool nes_sd_readback_probe(const char *path,const char *image,struct nes_sd_readback_report *report)',
  'bool nes_menu_sd_probe(const char *path,const char *image,bool expected_chr32,struct nes_menu_probe_report *candidate)')
 s=replace(s,' struct nes_mcu_load_report *r=report?&report->load:0;',
  ' struct nes_sd_readback_report *report=candidate?&candidate->sd:0;\n struct nes_mcu_load_report *r=report?&report->load:0;')
 s=replace(s,' memset(report,0,sizeof(*report));',' memset(candidate,0,sizeof(*candidate));')
 s=replace(s,' r->chr_32k=header[5]==4;',
  ' r->chr_32k=header[5]==4;\n if(r->chr_32k!=expected_chr32){r->result=NES_MCU_LOAD_HEADER;goto cleanup;}')
 s=replace(s,'#include "nes_sd_readback.h"','#include "nes_menu_probe.h"')
 needle=' for(unsigned i=0;i<2;i++) {\n  uint8_t tx[2]'
 s=replace(s,needle,''' {
  uint8_t tx[2]={0xcf,0},rx[2]={0};
  if(!slow_transaction(0,tx,rx,2)){r->result=NES_MCU_LOAD_ID;goto cleanup;}
  candidate->board_seen=true;candidate->board_id=rx[1];
  if(rx[1]!=0x61){r->result=NES_MCU_LOAD_ID;goto cleanup;}
 }
'''+needle)
 return prefix+s

def materialize(out):
 materialize060(out)
 (out/'nes_h1_stm32.c').write_text(source(),encoding='utf-8',newline='\n')
 (out/'nes_menu_probe.h').write_text('''/* SPDX-License-Identifier: MIT */
#ifndef NES_MENU_PROBE_H
#define NES_MENU_PROBE_H
#include "nes_sd_readback.h"
struct nes_menu_probe_report {struct nes_sd_readback_report sd;bool board_seen;uint8_t board_id;};
bool nes_menu_sd_probe(const char *,const char *,bool,struct nes_menu_probe_report *);
#endif
''',encoding='utf-8',newline='\n')
 for n in ['nes_menu_diagnostic.c','nes_menu_diagnostic.h']:shutil.copy2(FW/n,out/n)

def main_source(s):
 s=replace(s,'#include "nes_h1_stm32.h"','#include "nes_h1_stm32.h"\n#include "nes_menu_diagnostic.h"')
 needle='          if(nes_h1_is_marker(file_lfn)) {'
 s=replace(s,needle,'''          if(nes_menu_diagnostic_marker(file_lfn)) {
            if(!nes_menu_diagnostic_run(file_lfn)) {
              led_panic(LED_PANIC_FPGA_NOCONF);
              for(;;); /* RESET remains held on unsafe recovery. */
            }
            goto nes_h1_reload_menu;
          }
'''+needle,3)
 s=replace(s,'    load_rom((uint8_t*)MENU_FILENAME, SRAM_MENU_ADDR, 0);',
  '    uint32_t nes_menu_size=load_rom((uint8_t*)MENU_FILENAME, SRAM_MENU_ADDR, 0);')
 s=replace(s,'    cfg_save();\n    snes_reset(0);','''    cfg_save();
    if(!nes_menu_diagnostic_prepared(nes_menu_size!=0 && sram_reliable())) {
      led_panic(LED_PANIC_FPGA_NOCONF);
      for(;;); /* Do not release RESET after failed menu preparation. */
    }
    snes_reset(0);
    nes_menu_diagnostic_released();''')
 return s

def host_source():
 s=(ROOT/'tests/nes-functional/sd_readback_host.c').read_text()
 s=replace(s,'#include "nes_sd_readback.h"','#include "nes_menu_probe.h"\n#include "nes_menu_diagnostic.h"')
 s=replace(s,'assert(tx[0]==0xf0||tx[0]==0xf1)','assert(tx[0]==0xcf||tx[0]==0xf0||tx[0]==0xf1)')
 s=replace(s,'if(tx[0]==0xf0)reply[1]=fault==ID?0:0xa5;',
  'if(tx[0]==0xcf)reply[1]=identity_fault==3?0x44:identity_fault==4?0:fault==ID?0x60:0x61;\n   else if(tx[0]==0xf0)reply[1]=identity_fault==1?0:0xa5;')
 s=replace(s,'else if(tx[0]==0xf1)reply[1]=0x44;', 'else if(tx[0]==0xf1)reply[1]=identity_fault==2?0:0x44;')
 s=replace(s,'reply[1]=fault==SPI_ID?0:0x59;', 'reply[1]=identity_fault==5?0x54:fault==SPI_ID?0:0x59;')
 s=replace(s,'struct nes_sd_readback_report report;struct nes_mcu_load_report *r=&report.load;',
  'struct nes_menu_probe_report candidate;struct nes_sd_readback_report *rp=&candidate.sd;struct nes_mcu_load_report *r=&rp->load;')
 s=replace(s,'nes_sd_readback_probe("fixture","approved-test-image",&report)','nes_menu_sd_probe("fixture","approved-test-image",original_length==98320,&candidate)')
 s=s.replace('report.','rp->')
 s=s.replace('struct nes_sd_readback_report r;', 'struct nes_menu_probe_report r;')
 s=s.replace('nes_sd_readback_probe("fixture","approved-test-image",&r)', 'nes_menu_sd_probe("fixture","approved-test-image",original_length==98320,&r)')
 s=s.replace('r.load.', 'r.sd.load.')
 s=replace(s,'int main(int argc,char **argv)', 'int sd_regression(int argc,char **argv)')
 s=replace(s,' assert(r->result==expected&&reset_held',
  ' if(f==ID)assert(candidate.board_seen&&candidate.board_id==0x60&&begin_count==0&&count==0);\n assert(r->result==expected&&reset_held')
 s=replace(s,'"approved-test-image") == 0','"approved-test-image") == 0 || strcmp((const char *)path,"/sd2snes/fpga_nlv.bi3")==0')
 s=replace(s,'!strcmp(path,"fixture")','(!strcmp(path,"fixture")||!strcmp(path,"/sd2snes/nes/fine_x.nes")||!strcmp(path,"/sd2snes/nes/banks32.nes"))')
 # Logging uses a separate local FIL; failures must not alter diagnostic outcome.
 s=replace(s,'static enum fault fault;', '''static enum fault fault;
static bool logging;static unsigned identity_fault,log_fault,log_attempts,log_closes;static char last_log[640];''')
 s=replace(s,' assert(mode==FA_READ &&', ''' if(mode==(FA_CREATE_ALWAYS|FA_WRITE)) {
  assert(!irq&&(configs==0||configs==2)&&mock_b.MODER==mode_before&&mock_spi.CR1==cr1_before);
  assert(!strcmp(path,"/sd2snes/nes-verify-last-062.txt"));
  log_attempts++;logging=log_fault!=1;return log_fault==1?1:FR_OK;
 }
 assert(mode==FA_READ &&''')
 s=replace(s,'FRESULT f_close(FIL *f){(void)f;assert(!irq);',
  'FRESULT f_close(FIL *f){(void)f;assert(!irq);if(logging){logging=false;log_closes++;return log_fault==4?1:FR_OK;}')
 s=replace(s,'FRESULT f_write(FIL *f,const void *p,UINT n,UINT *got){(void)f;(void)p;(void)n;(void)got;assert(0);return 1;}',
 '''FRESULT f_write(FIL *f,const void *p,UINT n,UINT *got){(void)f;assert(logging&&!irq&&n<sizeof(last_log));memcpy(last_log,p,n);last_log[n]=0;*got=n-(log_fault==3);return log_fault==2?1:FR_OK;}''')
 return s

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True)
 p.add_argument('--mutation',choices=['candidate','menu-release'])
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 shutil.copy2(__file__,out/'executed-driver.py');materialize(out)
 (out/'sd-platform.c').write_text(host_source(),encoding='utf-8',newline='\n')
 shutil.copy2(ROOT/'tests/nes-functional/menu_diagnostic_host.c',out/'menu_diagnostic_host.c')
 shutil.copy2(ROOT/'tests/nes-functional/mcu_loader_platform.h',out/'mcu_loader_platform.h')
 for n in ['config','bits','timer','snes','fpga','fpga_spi','fileops','uart']:(out/(n+'.h')).write_text('#include "mcu_loader_platform.h"\n')
 if a.mutation:
  f=out/('nes_h1_stm32.c' if a.mutation=='candidate' else 'nes_menu_diagnostic.c');s=f.read_text()
  s=replace(s,'if(rx[1]!=0x61)' if a.mutation=='candidate' else 'if(!safe_to_reload||!menu_ok)',
   'if(false)' if a.mutation=='candidate' else 'if(!safe_to_reload||(!menu_ok&&false))')
  f.write_text(s,encoding='utf-8',newline='\n')
 fixtures={c:build(out/c,c) for c in ['fine_x','banks32']}
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
  'nes_rom_spi.c','nes_rom_verify.c','nes_h1_stm32.c','nes_h1_session.c','nes_menu_diagnostic.c','menu_diagnostic_host.c','-o','host.exe'],out,'compile')
 command=[out/'host.exe',out/'fine_x/mmc3.nes',out/'banks32/mmc3.nes',out/'waveform.txt',out/'load-waveform.txt']
 import subprocess
 with (out/'host.log').open('wb') as f:cp=subprocess.run([str(x) for x in command],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 log=(out/'host.log').read_text(errors='replace')
 if a.mutation:
  target='candidate.board_seen&&candidate.board_id==0x60&&begin_count==0&&count==0' if a.mutation=='candidate' else '!nes_menu_diagnostic_prepared(false)'
  assert cp.returncode!=0 and target in log
  marker='PASS expected failure '+a.mutation
 else:
  assert cp.returncode==0,log[-2500:]
  marker='PASS MENU062 regression=41 input_rejections=18 menu_sessions=16 no_START=1'
  assert marker in log
 result=dict(candidate='NES-MENU-DIAGNOSTIC-062',host_model_pass=not a.mutation,mutation=a.mutation,
  expected_failure_verified=bool(a.mutation),actual_stm32_execution=False,marker=marker,exit_code=cp.returncode,
  files={f.name:sha(f) for f in sorted(out.iterdir()) if f.suffix in ['.c','.h','.log']},
  fixtures={c:m['sha256'] for c,m in fixtures.items()},waveform_sha256=sha(out/'waveform.txt') if (out/'waveform.txt').exists() else None,
  load_waveform_sha256=sha(out/'load-waveform.txt') if (out/'load-waveform.txt').exists() else None,driver_sha256=sha(out/'executed-driver.py'))
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(marker)

if __name__=='__main__':main()
