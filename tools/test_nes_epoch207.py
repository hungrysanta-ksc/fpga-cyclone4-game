# SPDX-License-Identifier: MIT
"""Actual207 epoch: baseline20 + clock-stopped/phase-swept cold reset32 cases.
Loader status fixture, not a whole ROM upload or physical metastability model.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_board204 import ROOT,BASE,sha,replace

def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src=BASE/'probes/nes-board207/source01';pins={};names=[]
 for n in ['nes_source_epoch207.sv','nes_domain_reset124.sv']:
  f=src/n;shutil.copyfile(f,a.out/n);names.append(n);pins[f.relative_to(BASE).as_posix()]=sha(f)
 f=ROOT/'tests/nes-functional/source_epoch205_tb.sv';pins[f.relative_to(BASE).as_posix()]=sha(f)
 s=f.read_text().replace('source_epoch205_tb','source_epoch207_tb').replace('nes_source_epoch205 dut','nes_source_epoch207 dut')
 s=s.replace('integer checks=0;', 'reg observe_cold=0;integer cold_cases=0;\n always @(negedge nes_clk)if(observe_cold&&ready&&(dut.cold_reset||epoch!==dut.gray))$fatal(1,"COLD207 stale epoch admitted");\n integer checks=0;')
 end='  $display("PASS EPOCH205 checks=%0d",checks);$finish;'
 extra='''  if(checks!=20)$fatal(1,"baseline count");
  for(integer stopped=0;stopped<2;stopped++)for(integer phase=0;phase<16;phase++)begin
   @(negedge nes_clk);observe_cold=0;run_clock=stopped==0;
   #(0.1+phase*2.5);reset=1;loaded=0;run=0;count=0;
   #0.1;if(ready||isrom||!writing)$fatal(1,"cold assert");
   repeat(4)@(negedge mem_clk);reset=0;
   // A new content load may finish before the paused NES clock resumes.
   begin_load=1;@(negedge mem_clk);begin_load=0;
   count=19'h60000;loaded=1;run=1;observe_cold=1;
   if(stopped)begin
    repeat(20)@(negedge mem_clk);
    if(ready||!dut.cold_reset||epoch!=0)$fatal(1,"stopped cold rearmed");
   end
   run_clock=1;repeat(12)@(negedge nes_clk);
   if(!ready||epoch!==dut.gray||epoch!=1)$fatal(1,"cold recovery");cold_cases++;
  end
  $display("PASS EPOCH207 baseline=%0d cold=%0d",checks,cold_cases);$finish;'''
 s=replace(s,end,extra).replace('#20000;','#100000;')
 (a.out/'bench.sv').write_text(s,encoding='utf8',newline='\n');names.append('bench.sv')
 def q(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert '** Fatal: COLD207 stale epoch admitted' in t and 'PASS EPOCH207' not in t,t[-3000:]
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
  return t
 q('vlib',['work'],'vlib');q('vlog',['-sv',*names],'vlog')
 args=['-c','work.source_epoch207_tb','-do','onerror {quit -code 1}; run -all; quit -f']
 t=q('vsim',args,'positive');assert 'PASS EPOCH207 baseline=20 cold=32' in t
 new=(a.out/'nes_source_epoch207.sv').read_text();wrong=replace(new,'reset||cold_reset||exhausted','reset||exhausted')
 (a.out/'wrong.sv').write_text(wrong,encoding='utf8',newline='\n');q('vlog',['-sv','wrong.sv'],'negative-compile');q('vsim',args,'negative',True)
 r=dict(passed=True,baseline_checks=20,cold_cases=32,wrong_admission_rejected=True,source_pins=pins,script_sha256=sha(Path(__file__)),physical=False,scope=__doc__)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print('PASS EPOCH207 baseline20/cold32/negative')
if __name__=='__main__':main()
