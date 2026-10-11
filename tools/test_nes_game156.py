# SPDX-License-Identifier: MIT
"""Short changed-boundary tests: real APU connection and real pad/SPI ring."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 e=a.baseline/'nes-game155/evidence/asm';sources={}
 for n in ['rtl/bus_savestates.vhd','rtl/regs_savestates.sv','rtl/apu.sv','rtl/nes.v','nes_game_pad150.sv','nes_run_observer134.sv','nes_pad_trace156.sv']:
  dst=a.out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.prepared/n,dst);sources[n]=sha(dst)
 old=(e/'rtl/nes.v').read_text();new=(a.prepared/'rtl/nes.v').read_text()
 assert new.replace(".CS             (apu_cs && (cpu_rnw || addr[4:0]==5'h17)), //156 channel-write isolation; frame counter/read path retained",'.CS             (apu_cs),')==old
 (a.out/'pad155.sv').write_text((e/'nes_game_pad150.sv').read_text().replace('module nes_game_pad150','module nes_game_pad155'))
 (a.out/'dma.sv').write_text(new[:new.index('module NES(')])
 # The gate is extracted from the actual prepared NES instance, not reimplemented.
 gate=re.search(r'\.CS\s+\((.*)\), //156',new)[1]
 template=(ROOT/'tests/nes-functional/game156_apu_tb.sv').read_text().replace('GATE_FROM_ACTUAL_NES',gate)
 (a.out/'apu156_tb.sv').write_text(template)
 shutil.copy2(ROOT/'tests/nes-functional/game156_trace_tb.sv',a.out/'trace156_tb.sv')
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:];return s
 run('vlib',['work'],'vlib');run('vcom',['-2008','rtl/bus_savestates.vhd'],'vcom')
 (a.out/'imports.sv').write_text('import regs_savestates::*;\n')
 run('vlog',['-sv','-mfcu','rtl/regs_savestates.sv','imports.sv','rtl/apu.sv','dma.sv','apu156_tb.sv','nes_game_pad150.sv','pad155.sv','nes_pad_trace156.sv','nes_run_observer134.sv','trace156_tb.sv'],'vlog')
 for top in ['apu156_tb','trace156_tb']:
  s=run('vsim',['-c','work.'+top,'-do','onerror {quit -code 1}; run -all; quit -f'],top);assert 'PASS156' in s
 s=run('vsim',['-c','work.trace156_tb','-gHALF_CLOCK=23.280423','-gSCK_HALF=190','-do','onerror {quit -code 1}; run -all; quit -f'],'trace-nominal-clock');assert 'PASS156' in s
 result=dict(passed=True,sources=sources,testbenches={n:sha(a.out/n) for n in ['apu156_tb.sv','trace156_tb.sv']},actual_nes_only_gate_change=True,physical=False,scope='Actual APU/DMA modules with gate extracted from NES instance; no full game. Actual pad vs155 all256 bytes, completed read trace and actual observer SPI/ring/STOP. Trace clocks10ns/46.560846ns;SPI half100ns/190ns.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS156 APU/pad trace boundary tests')
if __name__=='__main__':main()
