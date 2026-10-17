# SPDX-License-Identifier: MIT
"""Actual219/220 loader differential: commands, timed writes, prior codes, blocks."""
from pathlib import Path
import argparse,json,os,re,subprocess,shutil
from nes_status220 import ROOT,BASE,sha,transform
from test_nes_retire219 import connected

RESET='''`timescale 1ns/1ps
module reset220_tb;
 reg mem_clk=0,reset=0,commands_blocked=0;
 reg load_begin=0,load_valid=0,load_end=0,start=0,stop=0,load_chr32=0;
 reg [7:0] load_data=8'ha5;
 nes_rom_loader dut(.mem_clk(mem_clk),.reset(reset),.commands_blocked(commands_blocked),.load_begin(load_begin),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_chr32(load_chr32),.load_data(load_data));
 nes_rom_loader_reference refdut(.mem_clk(mem_clk),.reset(reset),.commands_blocked(commands_blocked),.load_begin(load_begin),.load_valid(load_valid),.load_end(load_end),.start(start),.stop(stop),.load_chr32(load_chr32),.load_data(load_data));
 integer checks=0;
 task compare_status;begin
  if(dut.run_enable!==refdut.run_enable)$fatal(1,"RESET220 status");
  if(dut.active_reset && dut.phase!==16'b1)$fatal(1,"RESET220 IDLE invariant");
  if(dut.active_reset && dut.run_enable)$fatal(1,"RESET220 reset RUN");
  if(dut.state!==refdut.state)$fatal(1,"RESET220 state");
  checks++;
 end endtask
 task tick;begin #1;mem_clk=1;#0.01;compare_status();#1;mem_clk=0;end endtask
 initial begin
  for(integer st=0;st<16;st++)for(integer c=0;c<64;c++)for(integer bl=0;bl<2;bl++)begin
   reset=0;dut.release_reset=0;refdut.release_reset=0;
   dut.phase=16'b1<<st;refdut.phase=16'b1<<st;
   dut.fault=0;refdut.fault=0;
   {load_begin,load_valid,load_end,start,stop,load_chr32}=c;commands_blocked=bl;
   #0.1;compare_status();reset=1;
   #0.01;compare_status();#5;compare_status(); // no memory clock
   reset=0;#0.1;compare_status();#5;compare_status(); // stopped release
   repeat(4)tick();
  end
  $display("PASS RESET220 cases=2048 checks=%0d",checks);$finish;
 end
endmodule
'''

def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--reuse-positive',type=Path)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=BASE/'probes/nes-retire219/source02/nes_rom_loader.sv';new=BASE/'probes/nes-status220/source01/nes_rom_loader.sv'
 ref=old.read_text();candidate=new.read_text();assert candidate==transform(ref)
 (a.out/'reference.sv').write_text(ref.replace('module nes_rom_loader #','module nes_rom_loader_reference #'),encoding='utf8')
 (a.out/'candidate.sv').write_text(candidate,encoding='utf8')
 (a.out/'reset_tb.sv').write_text(RESET)
 (a.out/'connected_tb.sv').write_text(connected())
 for n in ['nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((new.parent/n).read_bytes())
 (a.out/'reference_spi.sv').write_text((new.parent/'nes_rom_spi.sv').read_text().replace('module nes_rom_spi_check(','module baseline_check165(',1))
 b=BASE/'probes/nes-board206/test01/loader/bench.sv';s=b.read_text()
 # The inherited state sweep seeds code0. Add all16 prior code values and
 # both blocked levels to check hold/clear behavior, including unreachable codes.
 anchor='  sequential=0;\n  for(integer v=0;v<524288;v++)begin'
 assert s.count(anchor)==1
 extra='''  sequential=0;
  for(integer st=0;st<16;st++)for(integer c=0;c<64;c++)
  for(integer prior=0;prior<16;prior++)for(integer blocked=0;blocked<2;blocked++)
  for(integer complete=0;complete<2;complete++)for(integer sticky=0;sticky<2;sticky++)begin
   @(negedge mem_clk);clear_commands();
   {load_begin,load_valid,load_end,start,stop,load_chr32}=c;
   commands_blocked=blocked;
   dut.phase=16'b1<<st;refdut.phase=16'b1<<st;
   dut.error_code=prior;refdut.error_code=prior;
   dut.fault=sticky;refdut.fault=sticky;
   dut.count_complete=complete;refdut.count_complete=complete;
   @(posedge mem_clk);#0.01;
   if(dut.error_code!==refdut.error_code)$fatal(1,"CODE217 st=%0d cmd=%0d prior=%0d block=%0d complete=%0d fault=%0d actual=%0d expected=%0d",st,c,prior,blocked,complete,sticky,dut.error_code,refdut.error_code);
  end
  @(negedge mem_clk);clear_commands();commands_blocked=0;
'''
 s=s.replace(anchor,extra+anchor).replace('#20000000;','#40000000;')
 s=s.replace('exhaustive=524288"','exhaustive=524288 codes=131072"')
 (a.out/'bench.sv').write_text(s,encoding='utf8')
 reused={}
 if a.reuse_positive:
  for f in a.out.glob('*.sv'):assert f.read_text()==(a.reuse_positive/f.name).read_text(),f.name
 def run(tool,args,label,negative=False):
  if a.reuse_positive and label in ['equivalence','reset','wire']:
   oldlog=a.reuse_positive/(label+'.log');reused[str(oldlog)]=sha(oldlog);shutil.copyfile(oldlog,a.out/(label+'.log'));code=0
  else:
   with (a.out/(label+'.log')).open('wb') as f:
    r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
   code=r.returncode
  t=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert re.search(r'\*\* Fatal: (DIFF131|CODE217|DIRECTSTATE165 onehot)',t) and 'PASS STATE165' not in t,t[-3000:]
  else:assert code==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-4000:]
  return t
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','bench.sv','reset_tb.sv','nes_rom_spi.sv','reference_spi.sv','nes_rom_boot.sv','nes_rom_physical.sv','connected_tb.sv'],'vlog')
 args=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f']
 t=run('vsim',args,'equivalence');assert 'states=294912 sequences=1056 exhaustive=524288 codes=131072' in t
 resetlog=run('vsim',['-c','reset220_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'reset')
 assert 'PASS RESET220 cases=2048 checks=18432' in resetlog
 wire=run('vsim',['-c','tag165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'wire')
 assert 'wire_bits=14016' in wire and 'acks=7 corruptions=19 cancels=72 overlaps=2' in wire
 for label,bad in [('state',candidate.replace('assign run_enable=!fault && phase[RUN];','assign run_enable=!fault && (phase[RUN] || phase[READY]);')),('stop',candidate.replace('!stop && load_end && !load_valid && count_complete','load_end && !load_valid && count_complete'))]:
  assert bad!=candidate;badfile='wrong-'+label+'.sv';(a.out/badfile).write_text(bad,encoding='utf8')
  run('vlog',['-sv',badfile],label+'-compile');run('vsim',args,label+'-negative',True)
 r=dict(passed=True,states=294912,sequences=1056,counts=524288,prior_code_cases=131072,negative_wrong_state=True,negative_stop=True,reset_cases=2048,reset_checks=18432,
  wire_summary=re.search(r'PASS TAG165[^\r\n]+',wire)[0],sources={x.name:sha(x) for x in a.out.glob('*.sv')},positive_logs_reused_not_rerun=reused,
  source_pins={str(f.relative_to(BASE)):sha(f) for f in (old,new,b)},script_sha256=sha(Path(__file__)),physical=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
