# SPDX-License-Identifier: MIT
"""Actual216/217 loader differential: commands, timed writes, prior codes, blocks."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_loader217 import ROOT,BASE,sha,transform

def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=BASE/'probes/nes-wait216/source02/nes_rom_loader.sv';new=BASE/'probes/nes-loader217/source01/nes_rom_loader.sv'
 ref=old.read_text();candidate=new.read_text();assert candidate==transform(ref)
 (a.out/'reference.sv').write_text(ref.replace('module nes_rom_loader #','module nes_rom_loader_reference #'),encoding='utf8')
 (a.out/'candidate.sv').write_text(candidate,encoding='utf8')
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
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert re.search(r'\*\* Fatal: (DIFF131|CODE217)',t) and 'PASS STATE165' not in t,t[-3000:]
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-4000:]
  return t
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','bench.sv'],'vlog')
 args=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f']
 t=run('vsim',args,'equivalence');assert 'states=294912 sequences=1056 exhaustive=524288 codes=131072' in t
 for label,bad in [('conflict',candidate.replace('wire err5=command_conflict;','wire err5=1\'b0;')),('stop',candidate.replace('wire err6=stop &&','wire err6=1\'b0 &&'))]:
  assert bad!=candidate;(a.out/'wrong.sv').write_text(bad,encoding='utf8')
  run('vlog',['-sv','wrong.sv'],label+'-compile');run('vsim',args,label+'-negative',True)
 r=dict(passed=True,states=294912,sequences=1056,counts=524288,prior_code_cases=131072,negative_conflict=True,negative_stop=True,
  source_pins={str(f.relative_to(BASE)):sha(f) for f in (old,new,b)},script_sha256=sha(Path(__file__)),physical=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':main()
