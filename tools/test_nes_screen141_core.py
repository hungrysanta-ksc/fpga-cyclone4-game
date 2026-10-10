# SPDX-License-Identifier: MIT
"""Reproduce140's first fault and check141 actual consumers under delayed ACK.

Delays are digital stress parameters, not measured board flight or SDF.
The fixture is seeded; this does not repeat the 80KiB SPI upload test.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_functional import VHDL
from nes_screen141 import prepare
from nes_screen141_models import prepare_models

def summarize(o):
 phases=[]
 for i in range(12):
  t=(o/f'unit-{i}.log').read_text()
  m=re.search(r'RESULT141 phase=([\d.]+) faults=([01]{5})',t)
  assert m and '** Fatal:' not in t
  bits=int(m[2],2);assert bits&12==0
  phases.append(dict(phase_ns=float(m[1]),old_fault=bool(bits&2),new_fault=False))
 old=(o/'core-1-3.5.log').read_text()
 assert 'PASS141 CACHE checks=74' in (o/'cache.log').read_text()
 assert 'FIRST141 sample=123028 context=440181c30800e184' in old and '** Fatal:' in old
 cases=[]
 for phase in [3.5,0,11.25]:
  n=f'core-0-{phase}';t=(o/(n+'.log')).read_text()
  m=re.search(r'PASS141 checks=(\d+) actualCPU=(\d+) openbus=(\d+)',t)
  assert m and '** Fatal:' not in t and 'FIRST141' not in t
  assert int(m[2])>90000 and int(m[3])>90000
  frames={f.name:dict(sha256=sha(f),pixels=len(f.read_text().splitlines())) for f in o.glob(n+'-frame-*.hex')}
  assert any(v['pixels']==61440 for v in frames.values())
  cases.append(dict(phase_ns=phase,checks=int(m[1]),cpu_reads=int(m[2]),final_bus_captures=int(m[3]),frames=frames))
 return dict(passed=True,phases=phases,old_signature_reproduced=True,cases=cases,request_delay_ns=5,full_ack_delay_ns=12,boundary_ack_delay_ns=16,physical=False,sdf=False,delays_measured=False)

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists()
 assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
 prepare(a.baseline,o,'fit');prepare_models(o)
 names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(o/'board.qsf').read_text())
 for n,d in [('screen141_tb.sv','screen141_tb.sv'),('screen141_boundary_tb.sv','unit141_tb.sv'),('run133_pll_model.sv','run133_pll_model.sv'),('screen141_cache_tb.sv','screen141_cache_tb.sv')]:shutil.copy2(ROOT/'tests/nes-functional'/n,o/d)
 e=a.baseline/'nes-response140/evidence'
 pins=json.loads((e/'manifest.json').read_bytes())['files'];assert sha(e/'full01/rom_boot_model.sv')==pins['full01/rom_boot_model.sv']
 shutil.copy2(e/'full01/rom_boot_model.sv',o/'rom_boot_model.sv')
 def run(tool,args,n,negative=False):
  with (o/(n+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  t=(o/(n+'.log')).read_text(errors='replace')
  if negative:assert '** Fatal:' in t,n
  else:assert r.returncode==0 and '** Fatal:' not in t,n
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 sv=[n for n in names if n not in VHDL and n not in ['nes_clock_pll123.v','fxpak_nes_screen137_top.sv','nes_screen_bus137.sv']]
 run('vlog',['-sv','-mfcu',*sv,'run133_pll_model.sv','nes_screen_bus137.sv','fxpak_nes_screen137_top.sv','rom_boot_model.sv','screen141_tb.sv','unit141_tb.sv','screen141_cache_tb.sv'],'compile')
 do='onerror {quit -code 1}; run -all; quit -f'
 run('vsim',['-c','screen141_cache_tb','-do',do],'cache')
 for i in range(12):run('vsim',['-c','unit140_tb',f'+PHASE={i*.5}','-do',do],f'unit-{i}')
 original_service=(o/'nes_rom_service.sv').read_bytes()
 for legacy,phase in [(1,3.5),(0,3.5),(0,0),(0,11.25)]:
  name=f'core-{legacy}-{phase}'
  #140 control disables all three functional deltas; never change the selected fit.
  old_service=e/'fit01/nes_rom_service.sv'
  assert sha(old_service)==pins['fit01/nes_rom_service.sv']
  (o/'nes_rom_service.sv').write_bytes(old_service.read_bytes() if legacy else original_service)
  run('vlog',['-sv','nes_rom_service.sv'],name+'-service-compile')
  run('vsim',['-c','screen141_tb',f'-gLEGACY={legacy}',f'-gCAPTURE={0 if legacy else 1}',f'-gACK={16 if legacy else 12}',f'+PHASE={phase}','-do',do],name,bool(legacy))
  for f in list(o.glob('frame-*.hex'))+[o/'boundary-trace.txt']:shutil.copy2(f,o/(name+'-'+f.name))
 (o/'nes_rom_service.sv').write_bytes(original_service)
 result=summarize(o);(o/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
