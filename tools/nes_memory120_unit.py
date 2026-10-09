# SPDX-License-Identifier: MIT
"""Focused pin/CDC phase matrix for eight-cycle70ns read candidate."""
from pathlib import Path
import argparse,json,re,os,shutil,subprocess
from nes_spi_boot import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--baseline',type=Path) # Shared FLOAT launcher argument; unused.
 a=p.parse_args();o=a.out.resolve();assert str(o).isascii() and not o.exists()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 o.mkdir()
 for n in ['src/nes/nes_rom_physical.sv','tests/nes-functional/rom_physical_model.sv','tests/nes-functional/rom_physical_tb.sv']:shutil.copy2(ROOT/n,o/Path(n).name)
 f=o/'rom_physical_tb.sv';s=f.read_text();s=s.replace('module rom_physical_tb;','module rom_physical_tb #(parameter realtime ACCESS120=70.0);').replace('nes_rom_physical dut(.*);','nes_rom_physical #(.READ_CYCLES(8)) dut(.*);').replace('rom_physical_model memory(.*);','rom_physical_model #(.ACCESS_NS(ACCESS120)) memory(.*);').replace('pin_cycles==3','pin_cycles==8');f.write_text(s)
 m=dict(candidate='NES-MEMORY-120-UNIT',passed=False,sources={p.name:sha(p) for p in o.iterdir()},cases=[],read_cycles=8,normal_access_ns=70,negative_access_ns=110,scope='16 phases,read-only pin correctness/reset/clock-stop; no board electrical proof')
 def save():(o/'result.json').write_text(json.dumps(m,indent=2)+'\n')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,label
 save();run('vlib',['work'],'vlib');run('vlog',['-sv','nes_rom_physical.sv','rom_physical_model.sv','rom_physical_tb.sv'],'vlog')
 for phase in range(0,12000,750):
  label='phase-'+str(phase);run('vsim',['-c','rom_physical_tb','+PHASE_PS='+str(phase),'-do','onerror {quit -code 1}; run -all; quit -f'],label)
  log=(o/(label+'.log')).read_text();match=re.search(r'PASS PHYSICAL checks=(\d+) accepted=(\d+) completed=(\d+) canceled=(\d+) pins=(\d+) latency=(\d+)..(\d+) phase_ps=(\d+)',log)
  assert match and '** Fatal:' not in log,label
  m['cases'].append(dict(zip(['checks','accepted','completed','canceled','pins','min_clocks','max_clocks','phase_ps'],map(int,match.groups()))));save()
 run('vsim',['-c','rom_physical_tb','-gACCESS120=110.0','+PHASE_PS=3500','-do','onerror {quit -code 1}; run -all; quit -f'],'late110')
 log=(o/'late110.log').read_text();assert '** Fatal: PHYSICAL check' in log and 'PASS PHYSICAL' not in log
 m.update(passed=True,negative110_rejected=True);save();print('PASS120 16phase pin/reset/CDC cases +110ns negative')
if __name__=='__main__':main()
