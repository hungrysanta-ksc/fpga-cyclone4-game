# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_cf86_session094 import materialize
from nes_menu_diagnostic import host_source,replace
from nes_diag_recovery_checks import function
from nes_mcu_loader import ROOT,sha,run
from build_nes_video_workloads import build

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True)
 p.add_argument('--mutation',choices=['ready','latch','verify-fail','candidate'])
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);materialize(out)
 for n in ['nes_cf86_session094.py','test_nes_cf86_session094.py']:shutil.copy2(ROOT/'tools'/n,out/('executed-'+n))
 header=(ROOT/'tests/nes-functional/mcu_loader_platform.h').read_text()
 header += '\n#define GPIO_I IDR\n#define FPGA_MCU_RDY_REG GPIOA\n#define FPGA_MCU_RDY_BIT 5\n#define BITBAND(r,b) (((r)>>(b))&1u)\n'
 (out/'mcu_loader_platform.h').write_text(header)
 for n in ['config','bits','timer','snes','fpga','fpga_spi','fileops','uart']:(out/(n+'.h')).write_text('#include "mcu_loader_platform.h"\n')
 (out/'memory.h').write_text('#include "mcu_loader_platform.h"\nuint16_t sram_writeblock(void*,uint32_t,uint16_t);\nuint16_t sram_readblock(void*,uint32_t,uint16_t);\n')
 s=host_source();s=s[:s.index('static void test(')]
 s='#include "nes_cf86_session094.h"\n#include "nes_menu_return.h"\nstatic unsigned scenario094,injected094;\nint sd_offload,ff_sd_offload,during_blocktrans;\n'+s
 s=s.replace('fault==ID?0x60:0x61','identity_fault==6?0x68:identity_fault==7?0x85:identity_fault==8?0x87:fault==ID?0x60:0x86')
 s=s.replace('fpga_nlv.bi3','fpga_n86.bi3')
 for name in ['f_open','f_read','f_lseek','f_close','fpga_pgm']:
  old=function(s,name);s=replace(s,old,old.replace('{','{assert(!nes_cf86_failed094());',1))
 s=replace(s,' assert(bits==16||bits==64);frames++;',
 ' if(nes_cf86_failed094()){return;} /* Safe cancellation is not a completed frame. */\n assert(bits==16||bits==64);frames++;')
 s=replace(s,' ns+=(unsigned long long)v*1000;', ''' ns+=(unsigned long long)v*1000;
 if(!injected094&&bits>=9&&!(mock_a.ODR&16)&&(mock_b.ODR&8)&&scenario094>=101&&scenario094<=111){
  unsigned op=scenario094==102?0x67:scenario094==103?0x68:scenario094==104?0x69:scenario094==105?0x64:scenario094==106?0xcf:0x61;
  if(tx[0]==op){injected094=1;
   if(scenario094==107)done=0;
   else if(scenario094==108)irq=1;
   else if(scenario094==109)reset_held=0;
   else if(scenario094==110)sd_offload=1;
   else if(scenario094==111)nes_return_fail(NES_DIAG_TIMER);
   else mock_a.IDR=0;
  }
 }''')
 (out/'platform094.c').write_text(s,encoding='utf-8',newline='\n')
 shutil.copy2(ROOT/'tests/nes-functional/cf86_session094_host.c',out/'host.c')
 if a.mutation:
  name,old,new={'ready':('nes_cf86_session094.c','!BITBAND(FPGA_MCU_RDY_REG->GPIO_I,FPGA_MCU_RDY_BIT)','false'),
    'latch':('nes_cf86_session094.c','if(phase094==FAILED094)return false;','if(phase094==FAILED094){phase094=IDLE094;return true;}'),
    'verify-fail':('nes_rom_verify.c','if(nes_cf86_monitoring094())nes_cf86_fail094();','/* removed */'),
    'candidate':('nes_h1_stm32.c','if(rx[1]!=0x86)','if(false)')}[a.mutation]
  f=out/name;text=f.read_text();assert old in text;f.write_text(text.replace(old,new),encoding='utf-8',newline='\n')
 for n in ['fine_x','banks32']:build(out/n,n)
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
  'nes_rom_spi.c','nes_rom_verify.c','nes_h1_stm32.c','nes_h1_session.c','nes_menu_diagnostic.c','nes_diag_runtime.c','nes_menu_return.c','nes_cf86_session094.c','host.c','-o','host.exe'],out,'compile')
 cases=[('fine_x',i) for i in list(range(38))+list(range(100,112))+list(range(120,132))]+[('banks32',0)]
 if a.mutation:cases=[('fine_x',{'ready':101,'latch':101,'verify-fail':31,'candidate':121}[a.mutation])]
 results=[]
 for fixture,scenario in cases:
  name=fixture+'-'+str(scenario);logpath=out/(name+'.log')
  with logpath.open('wb') as log:r=subprocess.run([out/'host.exe',out/fixture/'mmc3.nes',str(scenario)],stdout=log,stderr=subprocess.STDOUT,timeout=180)
  text=logpath.read_text(errors='replace')
  if a.mutation:
   assert r.returncode!=0 and 'Assertion' in text,text
  else:assert r.returncode==0 and 'PASS094' in text,text
  results.append(dict(case=name,exit=r.returncode,last_line=text.strip().splitlines()[-1],log_sha256=sha(logpath)))
 (out/'result.json').write_text(json.dumps(dict(candidate='NES-CF86-SESSION-094',cases=results,mutation=a.mutation,expected_failures=bool(a.mutation),actual_stm32=False,
  files={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.suffix in ['.c','.h','.py']}),indent=2)+'\n')
 print('PASS094 cases='+str(len(cases))+' mutation='+str(a.mutation))
if __name__=='__main__':main()
