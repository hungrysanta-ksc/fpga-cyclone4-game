# SPDX-License-Identifier: MIT
"""Prepare the exact extended ROM replay; execute run.py under the FLOAT wrapper.

Baseline is private frame165/frame03; collector is deployed prefetch171/map02.
No integrated fill/export/MCU/SNES pacing and no button input or hardware claim.
"""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,VHDL,SV,EXTRA,sha

COLLECTORS=['nes_native_planes165.sv','nes_native_compact_planes165.sv','nes_native_raster_frame165.sv','nes_native_frame165.sv']
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','collector','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii();a.out.mkdir(parents=True)
 files=VHDL+SV+EXTRA+COLLECTORS+['nes_native_ciram165.sv']
 for n in files+['prg.hex','chr.hex']:
  src=(a.collector if n in COLLECTORS else a.baseline)/n
  dst=a.out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 shutil.copy2(ROOT/'tests/nes-functional/admission173_tb.sv',a.out/'native_frame165_tb.sv')
 driver='''from pathlib import Path
import subprocess,json,re,os
O=Path(__file__).resolve().parent
Q=Path('C:/altera_standard/25.1std/questa_fse/win64')
assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
def run(exe,args,name):
 with (O/(name+'.log')).open('wb') as f:p=subprocess.run([str(Q/(exe+'.exe')),*args],cwd=O,stdout=f,stderr=subprocess.STDOUT,timeout=2400)
 t=(O/(name+'.log')).read_text(errors='replace');assert p.returncode==0 and not re.search(r'\\*\\* (Error|Fatal):',t),t[-5000:]
 return t
run('vlib',['work'],'vlib')
'''
 driver+='for i,n in enumerate('+repr(VHDL)+"):run('vcom',['-2008',n],f'vcom-{i}')\n"
 driver+="run('vlog',['-sv','-mfcu',*"+repr(SV+EXTRA+COLLECTORS+['nes_native_ciram165.sv'])+",'native_frame165_tb.sv'],'vlog')\n"
 driver+="s=run('vsim',['-c','work.native_frame165_tb','+FRAMES=60','-do','onerror {quit -code 1}; run -all; quit -f'],'core')\nprint(s[-1800:])\n"
 (a.out/'run.py').write_text(driver)
 pins={n:sha(a.out/n) for n in files+['prg.hex','chr.hex','native_frame165_tb.sv','run.py']}
 (a.out/'inputs.json').write_text(json.dumps(pins,indent=2)+'\n')
 print(json.dumps({'prepared':True,'source_files':len(pins),'executed':False}))
if __name__=='__main__':main()
