# SPDX-License-Identifier: MIT
"""OAM edge comparison under explicit positive-edge launch, negative-read contract."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(exist_ok=False)
 prep=json.loads((a.prepared/'preparation.json').read_bytes())
 for n,h in prep['sources'].items():assert sha(a.prepared/n)==h,n
 bench=(ROOT/'tests/nes-functional/oam_banked_tb.sv').read_text()
 bench=bench.replace('reference.oam[i]','reference.oam_read(i)')
 old='for(integer i=0;i<256;i++)if(reference.oam_read(i)!==candidate.oam_read(i))$fatal(1,"primary OAM mismatch cycle%0d addr%0d ref%h new%h",cycles_checked,i,reference.oam_read(i),candidate.oam_read(i));'
 assert old in bench
 expr=lambda inst:','.join(f'{inst}.oam_bank{k}[i]' for k in range(8))
 bench=bench.replace(old,'for(integer i=0;i<32;i++)if({'+expr('reference')+'}!=={'+expr('candidate')+'})$fatal(1,"primary OAM mismatch row%0d edge%0d",i,cycles_checked);')
 bench=bench.replace('wire [7:0] ref_bus',"wire [7:0] native_oam_address=Savestate_OAMAddr;wire [7:0] ref_native,new_native;wire ref_write,new_write;\n wire [7:0] ref_bus")
 for name,prefix in [('reference','ref'),('candidate','new')]:bench=bench.replace(name+'(.oam_bus',name+f'(.native_oam_data({prefix}_native),.native_oam_write({prefix}_write),.oam_bus')
 bench=bench.replace('if({ref_bus,','if({ref_native,ref_write,ref_bus,').replace('!=={new_bus,','!=={new_native,new_write,new_bus,')
 # Drivers launch after a positive edge, as the surrounding registered core does.
 # Keep the exact same PPU edge count, state seeds, data, and writer collisions.
 bench=bench.replace('repeat(3)@(negedge clk);','repeat(3)begin @(posedge clk);#1;end\n')
 bench=bench.replace('@(negedge clk);','@(posedge clk);#1;')
 bench=bench.replace('  #1;','  #0.5;') # Compare before next input launch.
 results={}
 for variant in ['negative-read','wrong-positive-read']:
  d=a.out/variant;d.mkdir()
  for folder,name in [(a.baseline,'oam_reference'),(a.prepared,'oam_banked')]:
   s=(folder/'rtl/ppu.sv').read_text();m=re.search(r'(?ms)^module OAMEval\(.*?^endmodule',s);assert m
   text=s[:s.index('import regs_savestates::*;')]+'import regs_savestates::*;\n'+m[0].replace('module OAMEval(','module '+name+'(',1)+'\n'
   if variant=='wrong-positive-read' and name=='oam_banked':
    assert text.count('always @(negedge clk)') in [4,5]
    text=text.replace('always @(negedge clk)','always @(posedge clk)')
   (d/(name+'.sv')).write_text(text,encoding='utf8',newline='\n')
  for n in ['regs_savestates.sv','bus_savestates.vhd']:shutil.copy2(a.prepared/'rtl'/n,d/n)
  (d/'oam_banked_tb.sv').write_text(bench,encoding='utf8',newline='\n')
  def run(exe,args,label,negative=False):
   with (d/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=180)
   log=(d/(label+'.log')).read_text(errors='replace')
   if negative:assert '** Fatal:' in log and 'mismatch' in log and 'PASS OAM BANKING' not in log,log[-3000:]
   else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),log[-3000:]
   return log
  run('vlib',['work'],'vlib');run('vcom',['-2008','bus_savestates.vhd'],'vcom')
  run('vlog',['-sv','-mfcu','regs_savestates.sv','oam_reference.sv','oam_banked.sv','oam_banked_tb.sv'],'vlog')
  log=run('vsim',['-c','oam_banked_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation',variant=='wrong-positive-read')
  if variant=='negative-read':
   match=re.search(r'PASS OAM BANKING cycles=(\d+) row_copies=(\d+) cpu_writes=(\d+) ss_writes=(\d+) collisions=(\d+)',log);assert match
   results[variant]=dict(zip(['cycles','row_copies','cpu_writes','ss_writes','collisions'],map(int,match.groups())))
  else:results[variant]='expected mismatch'
 result=dict(passed=True,results=results,source_sha256=sha(a.prepared/'rtl/ppu.sv'),baseline_sha256=sha(a.baseline/'rtl/ppu.sv'),
  runner_sha256=sha(Path(__file__)),bench_sha256=sha(ROOT/'tests/nes-functional/oam_banked_tb.sv'),scope=__doc__,full_game=False,physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
