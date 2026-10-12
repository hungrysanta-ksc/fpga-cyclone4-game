# SPDX-License-Identifier: MIT
"""Old/new loader comparison: all state codes, command priorities, timed writes."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_state165 import transform
from test_nes_drain165 import bench as old_bench

def bench():
 s=old_bench().replace('state<9','state<16').replace('rem_case<128','rem_case<6')
 s=s.replace('if(state==6 && !failed)continue;','// Include FAILED with fault clear and all unused state encodings.')
 s=s.replace('remaining=rem_case;','remaining=rem_case==0?0:rem_case==1?1:rem_case==2?2:rem_case==3?22:rem_case==4?64:127;')
 s=s.replace('integer checks=0;','integer checks=0;reg sequential=0;integer sequences=0;')
 regs='state remaining chr32 loaded_bytes count_complete fault error_code chip lane byte_hold load_address release_reset'.split()
 pins='load_ready loaded run_enable check_loaded load_pin_data load_drive load_1ce load_2ce load_oe load_we load_bhe load_ble'.split()
 compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"STATE165 sequential {n}");' for n in regs+pins)
 extra='''
 always @(posedge mem_clk or posedge reset)begin
  #0.001;if(sequential)begin
'''+compare+'''
  end
 end
 task tick;@(negedge mem_clk);#0.01;endtask
 task clear_commands;begin load_begin=0;load_valid=0;load_end=0;start=0;stop=0;commands_blocked=0;end endtask
 task fresh;begin
  tick();clear_commands();reset=1;repeat(3)tick();reset=0;repeat(4)tick();
  load_begin=1;tick();load_begin=0;tick();
  if(!dut.load_ready)$fatal(1,"STATE165 initial ready");
 end endtask
'''
 s=s.replace(' initial begin\n  repeat(4)',extra+' initial begin\n  repeat(4)',1)
 old='  $display("PASS131 DIFF one_step_cases=%0d counts_at_0_totalminus1_total=1",checks);$finish;'
 assert s.count(old)==1
 seq='''
  // Seeded one-step enumeration is followed by actual BEGIN/byte/phase sequences.
  sequential=1;
  for(integer action=0;action<8;action++)for(integer phase=0;phase<132;phase++)begin
   fresh();load_data=phase^8'ha5;load_valid=1;tick();load_valid=0;
   repeat(phase)tick();
   case(action)
    0:stop=1;
    1:load_begin=1;
    2:load_end=1;
    3:start=1;
    4:begin load_begin=1;load_end=1;end
    5:begin commands_blocked=1;load_begin=1;load_end=1;start=1;load_valid=1;end
    6:reset=1;
    7:load_valid=1;
   endcase
   tick();clear_commands();reset=0;repeat(140)tick();sequences++;
  end
  $display("PASS STATE165 states=%0d sequences=%0d",checks,sequences);$finish;
'''
 return s.replace(old,seq)

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_loader.sv').read_text();new=(a.prepared/'nes_rom_loader.sv').read_text();assert new==transform(old)
 a.out.mkdir();(a.out/'candidate.sv').write_text(new)
 (a.out/'reference.sv').write_text(old.replace('module nes_rom_loader #','module nes_rom_loader_reference #',1))
 (a.out/'state165_tb.sv').write_text(bench())
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert '** Fatal: DIFF131' in log and 'PASS STATE165' not in log,(label,log[-2000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2000:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv','candidate.sv','reference.sv','state165_tb.sv'],'compile')
 args=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f']
 log=run('vsim',args,'equivalence');assert 'PASS STATE165 states=294912 sequences=1056' in log
 wrong=new.replace('WRITE,HOLD:begin\n    if(fault', 'WRITE,HOLD:begin\n    if(stop)state<=FAILED;\n    else if(fault')
 assert wrong!=new;(a.out/'wrong-stop.sv').write_text(wrong)
 run('vlog',['-sv','wrong-stop.sv'],'negative-compile');run('vsim',args,'negative',True)
 r=dict(passed=True,states=294912,sequences=1056,all_state_codes=16,remaining_cases=[0,1,2,22,64,127],wrong_stop_rejected=True,
  source_sha256=sha(a.prepared/'nes_rom_loader.sv'),reference_sha256=sha(a.baseline/'nes_rom_loader.sv'),
  scope='One-step seeded old-register/pin comparison, followed by actual single-byte writes with eight command/reset actions over132 phases. Not whole-ROM load or gameplay.',
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_state165.py','tools/test_nes_state165.py','tools/test_nes_drain165.py','tests/nes-functional/counter131_diff_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
