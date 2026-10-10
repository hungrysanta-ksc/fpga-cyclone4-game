# SPDX-License-Identifier: MIT
"""Replay139 hardware boundary with bounded flight delays and140 ACK location.

The full-core bench uses139 IDs; only reader behavior changes between runs.
Selected140 production ID constants and identical functional sources are audited
separately. This is a digital delay model, not SDF or measured board timing.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_spi_boot import ROOT,sha
from nes_functional import VHDL
from nes_response140 import prepare

def fold_model(s):
 s=re.sub(r'^`timescale[^\n]*\n','',s)
 s=s.replace('parameter integer READ_CYCLES=16, EARLY_ACK=0, parameter real REQ_DELAY=5.0, ACK_DELAY=8.0','parameter integer READ_CYCLES=3')
 s=re.sub(r' wire request_flight,ack_flight;[^\n]*\n','',s)
 s=s.replace('request_flight','request_toggle').replace('ack_flight','ack_toggle')
 s=s.replace('EARLY_ACK && !owner_check','!owner_check')
 s=s.replace('else if(!EARLY_ACK)ack_toggle<=request_sync[1];','')
 return canonical(s)

def canonical(s):return re.sub(r'\s+','',re.sub(r'//[^\n]*','',s))

def summarize(unit,full,nominal=None):
 phases=[]
 for i in range(12):
  log=(unit/f'case{i:02d}.log').read_text()
  m=re.search(r'RESULT140 phase=([\d.]+) faults=([01]{5})',log);assert m and '** Fatal:' not in log
  bits=int(m[2],2);assert bits & 15==0
  phases.append(dict(phase_ns=float(m[1]),old_margin_fault=bool(bits&16)))
 old=(full/'early0.log').read_text();new=(full/'early1.log').read_text()
 assert 'FIRST140 sample=123028 context=440181c30800e184' in old and '** Fatal:' in old
 assert 'PASS140 trace' in new and '** Fatal:' not in new and 'FINAL140 samples=198527 error= 0' in new
 frames={}
 if nominal:
  for f in nominal.glob('frame-*.hex'):
   assert f.read_bytes()==(full/f.name).read_bytes(),f.name
   frames[f.name]=dict(bytes=f.stat().st_size,pixels=len(f.read_text().splitlines()),sha256=sha(f))
 return dict(passed=True,phases=phases,old_fault_phases=sum(x['old_margin_fault'] for x in phases),new_fault_phases=0,full_old_hardware_signature_matched=True,full_new_samples=198527,full_simulation_ns=67160943.105,nominal_frame_comparison=frames,request_delay_ns=5,ack_delay_ns=8,clock_half_ns=23.28,clock_phase_ns=3.5,physical=False,delays_measured=False,sdf=False)

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists();o.mkdir()
 assert os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
 production=o/'production';prepare(a.baseline,production,'fit')
 e=a.baseline/'nes-fault139/evidence/fit02'
 names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(e/'board.qsf').read_text())
 for n in names+['prg.hex','chr.hex','screen-program.hex']:
  dst=o/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,dst)
 model=(ROOT/'tests/nes-functional/response140_reader_model.sv').read_text()
 assert fold_model(model)==canonical((production/'nes_rom_physical.sv').read_text())
 (o/'nes_rom_physical.sv').write_text(model)
 for n in ['response140_tb.sv','response140_boundary_tb.sv','run133_pll_model.sv']:shutil.copy2(ROOT/'tests/nes-functional'/n,o/n)
 shutil.copy2(a.baseline/'nes-fault139/evidence/rtl01/rom_boot_model.sv',o/'rom_boot_model.sv')
 def run(t,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(t+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  if t!='vsim':assert not r.returncode,label
 run('vlib',['work'],'vlib')
 run('vlog',['-sv','nes_rom_service.sv','nes_rom_physical.sv','response140_boundary_tb.sv'],'unit-compile')
 for i in range(12):run('vsim',['-c','unit140_tb',f'+PHASE={i*.5}','-do','onerror {quit -code 1}; run -all; quit -f'],f'case{i:02d}')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 sv=[n for n in names if n not in VHDL and n not in ['nes_clock_pll123.v','fxpak_nes_screen137_top.sv','nes_screen_bus137.sv']]
 run('vlog',['-sv','-mfcu',*sv,'run133_pll_model.sv','nes_screen_bus137.sv','fxpak_nes_screen137_top.sv','rom_boot_model.sv','response140_tb.sv'],'full-compile')
 for early in [0,1]:
  run('vsim',['-c','response140_tb',f'-gEARLY={early}','-do','onerror {quit -code 1}; run -all; quit -f'],f'early{early}')
  shutil.copy2(o/'boundary-trace.txt',o/f'boundary-early{early}.txt')
 result=summarize(o,o);(o/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
