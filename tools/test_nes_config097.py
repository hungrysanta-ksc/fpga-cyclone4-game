# SPDX-License-Identifier: MIT
"""Execute final094 C with actual FatFS/native SD/config/READY functions.

Private final094 ARM evidence is required. Card pins, configuration pins,
SPI responder, startup state and elapsed time remain host models.
"""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_diag_recovery_checks import function
from nes_spi_boot import ROOT,sha
from nes_cf68_pair_preflight import decode

def replace(s,a,b):
 assert s.count(a)==1,a
 return s.replace(a,b)

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence094','assembly097','base-image','menu','out','gcc']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--scenario',type=int,default=0);p.add_argument('--case',default='fine_x',choices=['fine_x','banks32']);p.add_argument('--suite',action='store_true')
 p.add_argument('--mutation',choices=['sd-crc','config-run','ready-wait','failed-latch','menu-crc','menu-copy','report-permission'])
 p.add_argument('--fat32',action='store_true');p.add_argument('--sdsc',action='store_true')
 a=p.parse_args();e=a.evidence094.resolve();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 assembly=json.loads((a.assembly097/'result.json').read_bytes())
 assert sha(a.assembly097/'fpga_n86.bi3')==assembly['packed_sha256'] and sha(a.assembly097/'output_files/board.rbf')==assembly['rbf_sha256']
 assert sha(a.base_image)=='eff3f675c93a0209caf4987d72e0f277492c3dddc2b4c2aff334a667b4dbfbc7'
 assert sha(a.menu)=='f53b777a0bbe37668cd88cf8c80c5e5a0a60f861f58d1d4d3d9b082e9d1b4325'
 for source,name in [(a.assembly097/'fpga_n86.bi3','diag.packed'),(a.assembly097/'output_files/board.rbf','diag.raw'),(a.base_image,'base.packed'),(a.menu,'menu.bin')]:shutil.copy2(source,o/name)
 (o/'base.raw').write_bytes(decode((o/'base.packed').read_bytes()))
 assert decode((o/'diag.packed').read_bytes())==(o/'diag.raw').read_bytes()
 meta=json.loads((ROOT/'analysis/session094-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];inputs={}
 def copy(n,target=None):
  k='arm04/src/'+n;assert sha(e/k)==pins[k],k;inputs[k]=pins[k]
  f=o/(target or n);f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/k,f);return f
 names=['ff.c','ff.h','ffconf.h','integer.h','diskio.h','nes_diag_runtime.c','nes_diag_runtime.h',
 'nes_menu_return.c','nes_menu_return.h','nes_menu076.h','nes_menu076.c','nes_cf86_session094.c','nes_cf86_session094.h',
 'nes_h1_stm32.c','nes_h1_stm32.h','nes_h1_session.c','nes_h1_session.h','nes_rom_spi.c','nes_rom_spi.h',
 'nes_rom_verify.c','nes_rom_verify.h','nes_menu_diagnostic.c','nes_menu_diagnostic.h','nes_menu_probe.h',
 'nes_mcu_loader.h','nes_sd_readback.h','rle.h','smc.h']
 for n in names:copy(n)
 copy('ccsbcs.c','unicode/ccsbcs.c')
 native=copy('stm32f4xx/sdnative.c','input-sdnative.c').read_text()
 selected=['nes_diag_sd_error','nes_diag_sd_reset','nes_diag_sd_failed','sdn_status',
 'wiggle_fast_pos','wiggle_fast_neg','wiggle_fast_neg1','wiggle_fast_pos1','get_and_check_datacrc',
 'wait_busy','send_command_fast','make_crc7','cmd_fast','send_datablock','nes_diag_sd_response',
 'nes_diag_sd_read','sdn_read','nes_return_sd_write','sdn_write','sdn_ioctl']
 bodies=[]
 for n in selected:
  m=re.search(r'^(?:static inline void|static void|static bool|static DRESULT|int|void|bool|DRESULT|DSTATUS) '+n+r'\([^;{}]*\)\s*\{',native,re.M);assert m,n
  bodies.append(function(native[m.start():],n))
 (o/'native.inc').write_text(''.join(bodies),encoding='utf-8')
 card=(ROOT/'tests/nes-functional/report_session078_host.c').read_text();card=card[:card.index('static void reset_case(')]
 for line in ['#include "nes_sd_inventory.h"\n','#include "nes_sd_inventory_log073.h"\n'] :card=card.replace(line,'')
 for n in ['nes_diag_ticks','nes_diag_observe','sdinv_fault_stage','sdn_status','sram_writeblock','sram_readblock','nes_menu_crc076']:
  card=card.replace(function(card,n),'')
 card=card.replace('static int during_blocktrans;','int during_blocktrans;')
 card=card.replace('static unsigned tick_div,tick_origin,first_fault_stage,first_fault_command,first_fault_rises;','')
 card=card.replace('4096','32768')
 card=replace(card,'static void start_response(void){','static void start_response(void){\n stage=menu_stage097?menu_stage097:nes_diag_status()->phase;\n if(target_phase096==stage&&++phase_commands096==target_index096)fault_at=(fault==END_BAD||fault==BUSY_FOREVER)?write_commands+1:commands+1;')
 card=replace(card,'static void set_pin(unsigned pin,unsigned value){','static void set_pin(unsigned pin,unsigned value){\n native_edge096(pin,value);')
 init_guard='if(nes_diag_active()){nes_diag_sd_error(NES_DIAG_SD_STATE);return STA_NOINIT;}'
 assert init_guard in function(native,'sdn_initialize')
 card=replace(card,'DSTATUS disk_initialize(BYTE d){assert(!d);return 0;}',
 '''DSTATUS disk_initialize(BYTE d){assert(!d);if(setup096)return 0;
 /* Exact active077 rejection; card initialization itself is outside this session. */
 if(nes_diag_active()){nes_diag_sd_error(NES_DIAG_SD_STATE);return STA_NOINIT;}
 assert(0);return STA_NOINIT;}
 ''')
 card=replace(card,'DSTATUS disk_status(BYTE d){assert(!d);return 0;}','DSTATUS disk_status(BYTE d){return sdn_status(d);}')
 card=card.replace('static unsigned fault,fault_at,command_fault,busy_clocks,wp,card=1,ccs=1;',
 'static unsigned fault,fault_at,command_fault,busy_clocks,wp,card=1,ccs=1;\nstatic unsigned setup096,target_phase096,target_index096,phase_commands096,menu_stage097;')
 card='#include "config097_bridge.h"\n'+card+'\n#include "config097_card.inc"\n'
 (o/'card.c').write_text(card,encoding='utf-8')
 platform=(e/'host04/platform094.c').read_text();assert sha(e/'host04/platform094.c')==pins['host04/platform094.c']
 inputs['host04/platform094.c']=sha(e/'host04/platform094.c')
 platform=platform.replace('int sd_offload,ff_sd_offload,during_blocktrans;','extern int sd_offload,ff_sd_offload,during_blocktrans;')
 for n in ['f_open','f_read','f_lseek','f_close','f_write','fpga_pgm'] :platform=platform.replace(function(platform,n),'')
 platform=platform.replace('FRESULT file_res;','int file_res;')
 platform=replace(platform,'tick_t getticks(void){return (tick_t)(ns/10000000);}','tick_t getticks(void){return clock096();}')
 platform=platform.replace('&&closes==2','')
 platform=replace(platform,'void snes_reset(int asserted){assert(asserted==1);reset_held=1;}','void snes_reset(int asserted){if(!asserted)assert(!nes_return_failed()&&!irq);reset_held=asserted;}')
 # C trace responder is retained, but no longer implements file operations.
 (o/'platform.c').write_text(platform,encoding='utf-8')
 h=(e/'host04/mcu_loader_platform.h').read_text();assert sha(e/'host04/mcu_loader_platform.h')==pins['host04/mcu_loader_platform.h']
 inputs['host04/mcu_loader_platform.h']=sha(e/'host04/mcu_loader_platform.h')
 for line in ['typedef unsigned UINT;','typedef unsigned FRESULT;','typedef struct {unsigned fsize,pos;} FIL;',
 '#define FR_OK 0u','#define FA_READ 1u','#define FA_WRITE 2u','#define FA_CREATE_ALWAYS 8u','#define f_size(f) ((f)->fsize)']:
  h=replace(h,line,'')
 h=h.replace('extern FRESULT file_res;','extern int file_res;')
 h=re.sub(r'^FRESULT f_.*\n','',h,flags=re.M)
 h=h.replace('#include <stdio.h>','#include <stdio.h>\n#include "ff.h"')
 h=h.replace('#define BITBAND(r,b) (((r)>>(b))&1u)','#define BITBAND(r,b) input096((r),(b))\nunsigned input096(unsigned,unsigned);')
 h+='\n#define SPI_SR_TXE_Pos 1\n#define SPI_SR_BSY_Pos 7\n#define FPGA_PROGBREG GPIOA\n#define FPGA_PROGBBIT 6\nextern FIL file_handle;\nuint32_t clock096(void);\n'
 raw=copy('fpga_spi.h','input-fpga_spi.h').read_text();feature=re.search(r'^#define FEAT_SRTC.*$',raw,re.M);assert feature;h+=feature[0]+'\n'
 (o/'mcu_loader_platform.h').write_text(h,encoding='utf-8')
 for n in ['config','bits','timer','snes','fpga','fpga_spi','fileops','uart']:(o/(n+'.h')).write_text('#include "mcu_loader_platform.h"\n')
 (o/'memory.h').write_text('#include "mcu_loader_platform.h"\nuint16_t sram_writeblock(void*,uint32_t,uint16_t);\nuint16_t sram_readblock(void*,uint32_t,uint16_t);\n')
 raw=copy('memory.c','input-memory.c').read_text()
 start=raw.index('  if(nes_diag_active()) {\n    /* The global');end=raw.index('  } else {',start)
 (o/'classify.inc').write_text('static unsigned memory_classify097(void){\n'+raw[start:end]+'  }\nreturn 1;\n}\n',encoding='utf-8')
 copy('main.c','input-main.c')
 raw=copy('fpga.c','input-fpga.c').read_text();config=raw[raw.index('struct nes_diag_input {'):]
 (o/'config.inc').write_text(config,encoding='utf-8')
 raw=copy('stm32f4xx/spi.c','input-spi.c').read_text()
 (o/'ready.inc').write_text(function(raw,'nes_return_spi_wait')+function(raw,'nes_return_spi_ready'),encoding='utf-8')
 if a.mutation:
  name,old,new={'sd-crc':('native.inc','if(bad){state=CMD_RSP;nes_diag_sd_error(NES_DIAG_SD_CRC);return CRC_ERROR;}','if(false){state=CMD_RSP;nes_diag_sd_error(NES_DIAG_SD_CRC);return CRC_ERROR;}'),
   'config-run':('config.inc','remaining=(uint32_t)(lo|(hi<<8));','remaining=1u+(uint32_t)(lo|(hi<<8));'),
   'ready-wait':('ready.inc','while(!BITBAND(FPGA_MCU_RDY_REG->GPIO_I,FPGA_MCU_RDY_BIT)){','while(false){'),
   'menu-crc':('nes_menu076.c','||(crc^0xffffffffu)!=NES_MENU076_CRC',''),
   'menu-copy':('nes_menu_return.c','||memcmp(data,verify,n)',''),
   'report-permission':('nes_menu_diagnostic.c','nes_return_log_allow(true);save_report','save_report'),
   'failed-latch':('nes_cf86_session094.c','if(phase094!=IDLE094||!owner094())','if(phase094==FAILED094)phase094=IDLE094;\n if(phase094!=IDLE094||!owner094())')}[a.mutation]
  f=o/name;f.write_text(replace(f.read_text(),old,new),encoding='utf-8')
 for n in ['config097_bridge.h','config097_card.inc','config097_host.c']:
  shutil.copy2(ROOT/'tests/nes-functional'/n,o/n);inputs['public/'+n]=sha(o/n)
 fixture=e/'host04'/a.case/'mmc3.nes';assert sha(fixture)==pins['host04/'+a.case+'/mmc3.nes'];shutil.copy2(fixture,o/'fixture.nes')
 inputs['fixture_sha256']=sha(fixture)
 shutil.copy2(__file__,o/'executed-driver.py')
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-ffunction-sections','-fdata-sections','-I.',
 'card.c','config097_host.c','ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c','-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT,check=True)
 cases=[]
 def execute(scenario,index=1):
  name=str(scenario)+'-'+str(index);logpath=o/(name+'.log')
  with logpath.open('wb') as f:r=subprocess.run([str(o/'host.exe'),str(o/'fixture.nes'),str(scenario),str(index),str(int(a.fat32)+2*int(a.sdsc)),*[str(o/n) for n in ['diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  log=logpath.read_text(errors='replace')
  if a.mutation:assert r.returncode!=0 and 'Assertion' in log,log[-4000:]
  else:assert r.returncode==0 and 'PASS097' in log,log[-4000:]
  cases.append(dict(name=name,marker=log.strip().splitlines()[-1],log_sha256=sha(logpath)));return log
 log=execute(a.scenario)
 if a.suite:
  phases={int(p):int(n) for p,n in re.findall(r'PHASE097 phase=(\d+) commands=(\d+)',log)}
  kinds={int(p):[int(k) for k in raw.split(',') if k] for p,raw in re.findall(r'KIND097 phase=(\d+) kinds=([0-9,]+)',log)}
  for phase,n in phases.items():
   if phase not in [2,5,6,7,8]:continue
   for kind in ([1,2,3,5,6,7] if phase==8 else [2,3,6,7]):
    indexes=[i+1 for i,k in enumerate(kinds[phase]) if (k==24 if kind in [1,5] else k==17 if kind in [3,7] else True)]
    assert indexes
    for index in sorted({indexes[0],indexes[(len(indexes)-1)//2],indexes[-1]}):execute(phase*100+kind,index)
  for scenario in list(range(1001,1014))+list(range(1101,1109)):execute(scenario)
 result=dict(image_inputs={n:dict(bytes=(o/n).stat().st_size,sha256=sha(o/n)) for n in ['diag.packed','diag.raw','base.packed','base.raw','menu.bin']},assembly_sha256=sha(a.assembly097/'result.json'),inputs=inputs,scenario=a.scenario,case=a.case,fat32=a.fat32,sdsc=a.sdsc,cases=cases,mutation=a.mutation,expected_failure=bool(a.mutation),production_changed=bool(a.mutation),actual_native_sd=True,physical=False,files={f.relative_to(o).as_posix():sha(f) for f in o.rglob('*') if f.is_file()})
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS097 cases='+str(len(cases)))
if __name__=='__main__':main()
