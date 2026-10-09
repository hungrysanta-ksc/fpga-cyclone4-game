# SPDX-License-Identifier: MIT
"""CF86 registered reader at sixteen-cycle70ns at168MHz: pin/reset/CDC phase matrix."""
from pathlib import Path
import argparse,json,re,os,shutil,subprocess,hashlib
from nes_reset124 import materialize
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--baseline',type=Path) # Shared FLOAT launcher argument; unused.
 a=p.parse_args();o=a.out.resolve();assert str(o).isascii() and not o.exists()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 o.mkdir();shutil.copy2(__file__,o/'executed-driver.py')
 for n in ['src/nes/diagnostic/nes_diag_safe_rom_physical.sv','tests/nes-functional/rom_physical_model.sv','tests/nes-functional/rom_physical_tb.sv']:shutil.copy2(ROOT/n,o/Path(n).name)
 shutil.copy2(o/'nes_diag_safe_rom_physical.sv',o/'nes_rom_physical.sv')
 materialize(o,'unit')
 f=o/'rom_physical_tb.sv';s=f.read_text();s=s.replace('module rom_physical_tb;','module rom_physical_tb #(parameter realtime ACCESS122=70.0);').replace('nes_rom_physical dut(.*);',"nes_rom_physical #(.READ_CYCLES(16)) dut(.check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.check_ready(),.check_response(),.check_response_address(),.check_data(),.*);").replace('rom_physical_model memory(.*);','rom_physical_model #(.ACCESS_NS(ACCESS122)) memory(.*);').replace('pin_cycles==3','pin_cycles==17').replace('#5.952381','#2.9761905');s=s.replace('endmodule',(ROOT/'tests/nes-functional/safe122_monitor.svh').read_text()+'\nendmodule');f.write_text(s)
 s=s.replace('  $display("PASS PHYSICAL', '  check(setup_checks122>=completed && hold_checks122>=completed);\n  $display("SAFE122 setup=%0d hold=%0d",setup_checks122,hold_checks122);\n  $display("PASS PHYSICAL')
 f.write_text(s)
 shutil.copy2(ROOT/'tests/nes-functional/safe122_monitor.svh',o/'safe122_monitor.svh')
 m=dict(candidate='NES-DOMAIN-RESET-124-UNIT',passed=False,sources={p.name:sha(p) for p in o.iterdir()},cases=[],read_cycles=16,normal_access_ns=70,negative_access_ns=110,scope='16 phases,registered safe reader read-only mode pin correctness/reset/clock-stop; CHECK ownership switching and board electrical timing not proven')
 def save():(o/'result.json').write_text(json.dumps(m,indent=2)+'\n')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert r.returncode==0,label
 save();run('vlib',['work'],'vlib');run('vlog',['-sv','nes_rom_physical.sv','rom_physical_model.sv','rom_physical_tb.sv'],'vlog')
 for phase in range(0,6000,375):
  label='phase-'+str(phase);run('vsim',['-c','rom_physical_tb','+PHASE_PS='+str(phase),'-do','onerror {quit -code 1}; run -all; quit -f'],label)
  log=(o/(label+'.log')).read_text();match=re.search(r'PASS PHYSICAL checks=(\d+) accepted=(\d+) completed=(\d+) canceled=(\d+) pins=(\d+) latency=(\d+)..(\d+) phase_ps=(\d+)',log)
  assert match and '** Fatal:' not in log,label
  row=dict(zip(['checks','accepted','completed','canceled','pins','min_clocks','max_clocks','phase_ps'],map(int,match.groups())))
  monitor=re.search(r'SAFE122 setup=(\d+) hold=(\d+)',log);assert monitor,label
  row.update(setup_checks=int(monitor[1]),hold_checks=int(monitor[2]))
  assert row['setup_checks']>=row['completed'] and row['hold_checks']>=row['completed']
  m['cases'].append(row);save()
 run('vsim',['-c','rom_physical_tb','-gACCESS122=110.0','+PHASE_PS=3500','-do','onerror {quit -code 1}; run -all; quit -f'],'late110')
 log=(o/'late110.log').read_text();assert '** Fatal: PHYSICAL check' in log and 'PASS PHYSICAL' not in log
 # Causal control: cancel the post-sample hold without shortening access time.
 # The external hold monitor must reject it even if the sampled byte was valid.
 original=(o/'nes_rom_physical.sv').read_text()
 before='else if(state==HOLD)reading_active<=0;'
 assert original.count(before)==1
 mutation=original.replace(before,'else if(state==HOLD || (state==ACTIVE && remaining==1))reading_active<=0;')
 (o/'negative-no-hold.sv').write_text(mutation)
 run('vlog',['-sv','negative-no-hold.sv'],'negative-no-hold-compile')
 run('vsim',['-c','rom_physical_tb','+PHASE_PS=3500','-do','onerror {quit -code 1}; run -all; quit -f'],'negative-no-hold')
 log=(o/'negative-no-hold.log').read_text();assert '** Fatal: SAFE122 hold interval' in log and 'PASS PHYSICAL' not in log
 m.update(passed=True,negative110_rejected=True,negative_hold_rejected=True,negative_source_sha256=sha(o/'negative-no-hold.sv'));save();print('PASS122 16phase safe pin/reset/CDC +110ns and no-hold negatives')
if __name__=='__main__':main()
