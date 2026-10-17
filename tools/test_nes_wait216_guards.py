# SPDX-License-Identifier: MIT
"""216 execution watchdog guards plus205 partial-publication regression."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_board204 import ROOT,BASE,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert str(a.out).isascii() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 pins={};files=[ROOT/'src/nes/rtl/nes_tile205.sv',ROOT/'tests/nes-functional/wait216_guards_tb.sv',ROOT/'tests/nes-functional/tile_stream205_tb.sv']
 files += [BASE/'probes/nes-board205/source01'/n for n in ['nes_tile_bulk193.sv','nes_native_mailbox165.sv','nes_bulk_aperture188.sv','nes_domain_reset124.sv']]
 for f in files:shutil.copyfile(f,a.out/f.name);pins[str(f)]=sha(f)
 qb=Path('C:/altera_standard/25.1std/questa_fse/win64')
 def run(tool,args,name):
  with (a.out/(name+'.log')).open('wb') as log:r=subprocess.run([str(qb/(tool+'.exe')),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-6000:];return t
 run('vlib',['work'],'vlib');run('vlog',['-sv',*[f.name for f in files]],'vlog')
 outputs={}
 for n,expected in [('wait216_guards_tb','PASS WAIT216 GUARDS checks=9'),('tile_stream205_tb','PASS STREAM205 checks=22')]:
  outputs[n]=run('vsim',['-c','work.'+n,'-do','onerror {quit -code 1}; run -all; quit -f'],n)
  assert expected in outputs[n],outputs[n]
 outputs['internal']=run('vsim',['-c','work.wait216_guards_tb','-gEXTERNAL=0','-do','onerror {quit -code 1}; run -all; quit -f'],'internal')
 assert 'PASS WAIT216 GUARDS checks=9' in outputs['internal']
 r=dict(passed=True,source_pins=pins,public_sha=sha(Path(__file__)),outputs=outputs,physical=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS WAIT216 guards9x2 partial22')
if __name__=='__main__':main()
