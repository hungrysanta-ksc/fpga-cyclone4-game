# SPDX-License-Identifier: MIT
"""Real APU/DMA write restore; filtering/CDC and board-tested DAC pin timing."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 sources={}
 for n in ['rtl/bus_savestates.vhd','rtl/regs_savestates.sv','rtl/apu.sv','rtl/nes.v','nes_dac162.sv']:
  d=a.out/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.prepared/n,d);sources[n]=sha(d)
 nes=(a.prepared/'rtl/nes.v').read_text();gate=re.search(r'\.CS\s+\((.*)\), //162',nes)[1];assert gate=='apu_cs'
 (a.out/'dma.sv').write_text(nes[:nes.index('module NES(')])
 for kind in ['apu','audio']:
  s=(ROOT/f'tests/nes-functional/game162_{kind}_tb.sv').read_text().replace('GATE_FROM_ACTUAL_NES',gate)
  (a.out/f'{kind}_tb.sv').write_text(s)
 gbc=(ROOT/'src/fpga/gbc_dac_psram.sv').read_text();sources['gbc_reference']=sha(ROOT/'src/fpga/gbc_dac_psram.sv')
 ref=gbc[gbc.index(' reg[8:0]divider;'):].replace('mute_sync[1]?16\'b0:(lrck?dac_sample_l:dac_sample_r)','mono')
 (a.out/'reference.sv').write_text('module dac_gbc_reference(input wire clk_dac,reset,input wire [15:0] mono,output wire DAC_MCLK,DAC_LRCK,DAC_SDOUT);\nwire [1:0] dac_reset_pipe={2{reset}};\n'+ref)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:];return s
 run('vlib',['work'],'vlib');run('vcom',['-2008','rtl/bus_savestates.vhd'],'vcom')
 (a.out/'imports.sv').write_text('import regs_savestates::*;\n')
 run('vlog',['-sv','-mfcu','rtl/regs_savestates.sv','imports.sv','rtl/apu.sv','dma.sv','nes_dac162.sv','reference.sv','apu_tb.sv','audio_tb.sv'],'vlog')
 results={}
 for label,top,args in [('apu','apu162_tb',[]),('audio84','audio162_tb',[]),('audio-phase','audio162_tb',['-gDAC_HALF=6.125'])]:
  s=run('vsim',['-c','work.'+top,*args,'-do','onerror {quit -code 1}; run -all; quit -f'],label)
  assert 'PASS162' in s;results[label]=re.search(r'PASS162.*',s)[0];print(results[label],flush=True)
 (a.out/'result.json').write_text(json.dumps(dict(passed=True,sources=sources,results=results,physical=False,scope='Actual APU/DMA modules, gate from prepared NES; DMC byte response modeled, not full game or PSRAM arbitration. Independent filter/CDC checks and unchanged GBC formatter pin comparison; no analog audio quality proof.'),indent=2)+'\n')
if __name__=='__main__':main()
