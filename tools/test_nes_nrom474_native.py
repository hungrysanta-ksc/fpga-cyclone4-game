# SPDX-License-Identifier: MIT
"""Actual474 planner/reference scenes, window safety/quiet timing and wrapper alias tests."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from nes_resident211 import prepare
p=argparse.ArgumentParser();p.add_argument('--arm',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
def run(folder,label,cmd):
 with(folder/(label+'.log')).open('wb') as f:r=subprocess.run(cmd,cwd=folder,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(folder/(label+'.log')).read_text(errors='replace')[-3000:]
 return (folder/(label+'.log')).read_text(errors='replace')
baseflags=[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-DNES_COST471_HOST']
planner=d/'planner';prepare(planner)
for n in ['nes_native165.c','nes_native165.h','nes_native_video165.h','nes_resident211.c','nes_resident211.h','nes_planner211.c','nes_plan191.c','nes_plan191.h','nes_cost471.c','nes_cost471.h']:shutil.copyfile(a.arm/n,planner/n)
run(planner,'build',baseflags+['resident211_host.c','nes_native165.c','nes_trace166.c','nes_resident211.c','nes_plan191.c','nes_planner211.c','nes_cost471.c','reference203.c','-o','host.exe'])
results={'planner':run(planner,'test',[str(planner/'host.exe')]).strip()}
for case in ['window','alias','format']:
 f=d/case;f.mkdir()
 for header in a.arm.glob('*.h'):shutil.copyfile(header,f/header.name)
 for n in ['nes_cost471.c','nes_cost471.h','nes_sink_window184.c','nes_sink_window184.h','nes_budget210.c','nes_budget210.h','nes_plan215.h']:shutil.copyfile(a.arm/n,f/n)
 if case in ['window','alias']:shutil.copyfile(ROOT/'tests/nes-nrom474'/(case+'.c'),f/'test.c')
 else:
  s=(ROOT/'tests/nes-nrom471/cost_format.c').read_text().replace('cost_schema=471','cost_schema=474').replace('PASS471','PASS474')
  s=s.replace(' nes_cost471_end();int n=', ''' for(unsigned i=0;i<3;i++){nes_cost474_waits[i].cycles=UINT64_MAX;nes_cost474_waits[i].calls=nes_cost474_waits[i].progress=nes_cost474_waits[i].quiet=nes_cost474_waits[i].max_cycles=UINT32_MAX;}
 nes_cost474_groups=nes_cost474_reused=UINT32_MAX;
 nes_cost471_end();int n=''');(f/'test.c').write_text(s,encoding='utf8',newline='\n')
 flags=[];sources=['test.c','nes_cost471.c']
 if case=='window':flags=['-DNES_COST474_TEST'];sources+=['nes_sink_window184.c']
 elif case=='format':sources+=['nes_budget210.c']
 else:
  wrapper='#include "nes_cost471.h"\n#include <string.h>\nstruct nes_rom_spi_io {int unused;};\n'
  for n,fn,count in [('nes_native165_bulk.inc','nes_native165_bulk','unsigned count'),('nes_game149_spi.inc','nes_game149_transfer','')]:
   tail=(a.arm/n).read_text().split('bool '+fn+'(',1)[1]
   args='const struct nes_rom_spi_io *io,const uint8_t *tx,uint8_t *rx'+(','+count if count else '')
   wrapper+='static bool '+fn+'_inner471('+args+'){(void)io;(void)tx;memset(rx,0,'+('count' if count else '8')+');return true;}\n'
   wrapper+='bool '+fn+'('+tail
  (f/'wrapper.c').write_text(wrapper,encoding='utf8',newline='\n');sources+=['wrapper.c']
 run(f,'build',baseflags+flags+sources+['-o','test.exe']);results[case]=run(f,'test',[str(f/'test.exe')]).strip()
 # Every derivative test source and raw compiler output is retained.
r={'passed':True,'results':results,'ARM_inputs':{n:sha(a.arm/n) for n in ['nes_planner211.c','nes_native_runtime165.c','nes_sink_window184.c','nes_sink_window184.h','nes_cost471.c','nes_cost471.h','nes_native165_bulk.inc','nes_game149_spi.inc']},'scope':__doc__,'poll_timing_is_model_not_physical':True}
(d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps(results))
