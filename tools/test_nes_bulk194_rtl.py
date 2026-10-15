# SPDX-License-Identifier: MIT
"""Actual193 producer/control194/188 aperture and candidate8KiB sink ROM bus."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','client','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 pins={};names=[];board=ROOT.parent/'probes/nes-window184-coupled/evidence/route02'
 inputs=[board/n for n in ('nes_domain_reset124.sv','nes_native_mailbox165.sv')]
 inputs+=[ROOT/'src/nes/rtl'/n for n in ('nes_tile_bulk193.sv','nes_bulk_aperture188.sv','nes_bulk_control194.sv')]
 inputs+=[ROOT/'src/nes/diagnostic/nes_sink_bus165.sv',ROOT/'tests/nes-functional/bulk_control194_tb.sv']
 for f in inputs:shutil.copyfile(f,a.out/f.name);names.append(f.name);pins[f.relative_to(ROOT.parent).as_posix()]=sha(f)
 shutil.copyfile(a.client/'sink-program.hex',a.out/'sink-program.hex')
 def run(tool,args):
  with (a.out/(tool+'.log')).open('wb') as log:
   r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(a.out/(tool+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:];return s
 run('vlib',['work']);run('vlog',['-sv',*names]);s=run('vsim',['-c','work.bulk_control194_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
 m=re.search(r'PASS CONTROL194 checks=(\d+) retires=(\d+) rejected=(\d+)',s);assert m
 r=dict(passed=True,checks=int(m[1]),retires=int(m[2]),rejected=int(m[3]),source_pins=pins,rom_sha256=sha(a.client/'sink-program.hex'),scope=__doc__,physical=False,actual_snes_cpu=False,new_fit=False)
 # Use the old4KiB ROM for a full-address differential default test.
 shutil.copyfile(a.out/'vsim.log',a.out/'control.log')
 source=board/'nes_sink_bus165.sv';pins[source.relative_to(ROOT.parent).as_posix()]=sha(source)
 (a.out/'reference.sv').write_text(source.read_text().replace('module nes_sink_bus165(', 'module nes_sink_bus165_reference('),encoding='utf8')
 source=ROOT/'tests/nes-functional/bulk_rom194_default_tb.sv';pins[source.relative_to(ROOT.parent).as_posix()]=sha(source);shutil.copyfile(source,a.out/source.name)
 shutil.copyfile(a.out/'sink-program.hex',a.out/'candidate-program.hex')
 shutil.copyfile(board/'sink-program.hex',a.out/'sink-program.hex');r['default_rom_sha256']=sha(board/'sink-program.hex')
 run('vlog',['-sv','reference.sv',source.name]);s=run('vsim',['-c','work.bulk_rom194_default_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
 assert 'PASS DEFAULT194 reads=33024' in s;r['default_differential_reads']=33024
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in r.items() if k!='source_pins'}))
if __name__=='__main__':main()
