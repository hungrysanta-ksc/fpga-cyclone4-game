# SPDX-License-Identifier: MIT
"""Actual RTC and runtime, with immutable098 main/native/FatFS integration."""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence098','arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--unit',action='store_true');p.add_argument('--geometry96',action='store_true')
 p.add_argument('--mutation',choices=['poll','time','cleanup','fault','baseline'])
 a=p.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
 shutil.copy2(__file__,o/'executed-driver.py')
 e=a.evidence098.resolve();meta=json.loads((ROOT/'analysis/menu098-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files'];inputs={}
 source=e/('fat32-96-02' if a.geometry96 else 'suite03')
 def write(n,s):(o/n).write_text(s,encoding='utf-8',newline='\n')
 for f in source.rglob('*'):
  if f.is_file() and f.suffix in ['.c','.h','.inc','.packed','.raw','.bin','.nes']:
   key=f.relative_to(e).as_posix();assert sha(f)==pins[key];inputs[key]=sha(f)
   d=o/f.relative_to(source);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
 src=a.arm/'src';rtc=(src/'stm32f4xx/rtc.c').read_text()
 if a.mutation=='baseline':
  key='arm01/src/stm32f4xx/rtc.c';assert sha(e/key)==pins[key];rtc=(e/key).read_text()
 write('rtc099-production.c',rtc);shutil.copy2(src/'nes_diag_runtime.h',o/'nes_diag_runtime.h')
 # Include/MMIO seam only. Actual full RTC function bodies remain verbatim.
 hdr=(src/'stm32f4xx/rtc.h').read_text().replace('struct tm','struct rtc_tm099')
 write('actual-rtc099.h',hdr)
 cmsis=src/'include/arm/ST/STM32F4/stm32f401xc.h'
 write('rtc099-cmsis.h','\n'.join(re.findall(r'^#define RTC_(?:TR|DR|ISR|CR)_\w+[^\n]*',cmsis.read_text(),re.M))+'\n')
 body=re.sub(r'^#include[^\n]*\n','',rtc,flags=re.M).replace('struct tm','struct rtc_tm099')
 for n in ['TR','DR','ISR','CR','BKP0R','BKP2R','WPR']:body=body.replace('RTC->'+n,'(*reg099(R_'+n+'))')
 if a.mutation=='poll':body=once(body,'100, 100000u','100, 0xffffffffu')
 if a.mutation=='time':body=once(body,'100, 100000u','0xffffffffu, 100000u')
 if a.mutation=='cleanup':body=once(body,'BITBAND((*reg099(R_ISR)), RTC_ISR_INIT_Pos) = 0;\n      rtc_lock();','/* cleanup removed */')
 if a.mutation=='fault':body=body.replace('nes_return_fail(NES_DIAG_RTC);','/* fault removed */')
 write('rtc099.inc','#include "actual-rtc099.h"\n#include "rtc099-cmsis.h"\n#include "rtc099_model.h"\n#pragma push_macro("BITBAND")\n#undef BITBAND\n#define BITBAND(r,p) (*alias099(&(r),(p)))\n'+body+'\n#pragma pop_macro("BITBAND")\n')
 shutil.copy2(ROOT/'tests/nes-functional/rtc099_model.h',o/'rtc099_model.h')
 shutil.copy2(ROOT/'tests/nes-functional/rtc099_unit.c',o/'rtc099_unit.c')
 if a.unit:
  # COFF gc-sections still resolves dead externals; retain the complete actual
  # shared guard prefix, omit only the unrelated copy-menu function.
  write('return099-unit.c',(o/'nes_menu_return.c').read_text().split('uint32_t nes_return_copy_menu(')[0])
  sources=['rtc099_unit.c','nes_diag_runtime.c','return099-unit.c']
  cases=[6] if a.mutation in ['poll','baseline'] else [4] if a.mutation=='time' else [5] if a.mutation=='cleanup' else [6] if a.mutation=='fault' else list(range(18))
 else:
  host=(o/'host098.c').read_text()
  host=host.replace('#include "rtc098-enum.inc"','')
  host=host.replace('firstboot,rtc_state,rtc_set098,','firstboot,rtc_set098,')
  start=host.index('static uint8_t rtc_isvalid(');end=host.index('void cic_init(',start)
  host=host[:start]+'#undef srtctime2bcdtime\n#include "rtc099.inc"\n'+host[end:]
  # Win64 DWORD is unsigned long while uint32_t is unsigned int; both 32 bits.
  # Keep production body unchanged behind a host-only spelling adapter.
  host=host.replace('#include "rtc099.inc"','#define get_fattime rtc_fattime099\n#include "rtc099.inc"\n#undef get_fattime\nDWORD get_fattime(void){if(rtc_mode099==7&&menu_bytes098==65536)stall099=1;return rtc_fattime099();}\n')
  host=once(host,'initialize(NONE,1);mock_a.IDR=32;','initialize(NONE,1);mock_a.IDR=32;setup_rtc099(baseline098);')
  host=once(host,'bool ok=false;','''bool ok=false;
 polls099=0;
 if(scenario098==1)regs099[R_BKP0R]=0;
 if(baseline098==1||baseline098==2)stall099=1;
 if(baseline098==3||baseline098==4){stall099=1;scenario096=1010;}
 if(baseline098==5)delay099=7;
 if(baseline098==6){delay099=100;inject099=3;}
 if(baseline098==7)stall099=0; /* report-only RSF failure configured below */
''')
  start=host.index(' if(baseline098){assert(');end=host.index('\n else if(',start)
  host=host[:start]+''' if(baseline098&&baseline098!=5){
  assert(!ok&&blocked098&&nes_return_failed()&&!release097&&!irq&&reset_held);
  assert(nes_diag_status()->error==(baseline098==6?NES_DIAG_SPI:baseline098==7?NES_DIAG_MENU:NES_DIAG_RTC));
  assert(!aliases099[0][RTC_ISR_INIT_Pos]&&regs099[R_WPR]==0);
 }'''+host[end:]
  host=once(host,'assert(rtc_set098==(scenario098==1?2:0)&&pair098==(scenario098==2?1:0));','assert(regs099[R_BKP0R]==(scenario098==1?0:RTC_MAGIC)&&pair098==(scenario098==2?1:0));')
  host=host.replace('PASS098','PASS099')
  write('host099.c',host)
  card=(o/'card.c').read_text();card=re.sub(r'DWORD get_fattime\(void\)\{[^}]+\}','',card)
  write('card.c',card)
  sources=['card.c','host099.c','ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']
  cases=[(13,0),(0,1),(0,7)] if a.geometry96 else [(0,0),(1,0),(0,1),(1,2),(0,3),(1,4),(0,5),(0,6),(0,7)]
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError((o/'compile.log').read_text(errors='replace')[-6000:])
 results=[]
 for i,case in enumerate(cases):
  args=[str(case)] if a.unit else [str(case[0]),str(case[1]),*[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]]
  log=o/f'case-{i}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  text=log.read_text(errors='replace')
  if a.mutation:assert r.returncode!=0 and 'Assertion' in text,text[-3000:]
  else:assert r.returncode==0 and 'PASS099' in text,text[-3000:]
  results.append(dict(case=case,exit=r.returncode,log_sha256=sha(log),last=text.strip().splitlines()[-1]))
 shutil.copy2(__file__,o/'executed-driver.py')
 write('result.json',json.dumps(dict(unit=a.unit,mutation=a.mutation,geometry96=a.geometry96,inputs=inputs,rtc_sha256=sha(o/'rtc099-production.c'),cases=results,physical=False,installable=False),indent=2)+'\n')
 print('PASS099 cases='+str(len(results)))
if __name__=='__main__':main()
