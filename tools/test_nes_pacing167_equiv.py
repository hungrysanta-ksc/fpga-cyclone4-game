# SPDX-License-Identifier: MIT
"""Narrow counter implementation vs the tested wide cooperative reference."""
from pathlib import Path
import argparse,json,subprocess,shutil,re,os
from nes_game147 import ROOT,sha
from nes_pacing167 import fill
def main():
 p=argparse.ArgumentParser()
 for n in ['reference','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(parents=True,exist_ok=False)
 assert json.loads((a.reference/'result.json').read_bytes())['passed']
 new=(a.candidate/'nes_native_fill165.sv').read_text();assert new==fill((ROOT/'src/nes/diagnostic/nes_native_fill165.sv').read_text())
 old=new.replace('reg [$clog2(WAIT_CYCLES+1)-1:0] waiting;', 'reg [31:0] waiting;').replace("waiting<=short_wait?waiting+1'b1:0;", "waiting<=waiting+1'b1;")
 assert old==(a.reference/'nes_native_fill165.sv').read_text()
 (a.out/'candidate.sv').write_text(new,encoding='utf8',newline='\n')
 (a.out/'reference.sv').write_text(old.replace('module nes_native_fill165','module reference_fill'),encoding='utf8',newline='\n')
 base=(ROOT/'tests/nes-functional/native_fill165_tb.sv').read_text()
 for name,finite in [('equiv_tb',False),('finite_tb',True)]:
  s=base.replace('native_fill165_tb',name)
  s=s.replace('.MAX_TILES(','.COOPERATIVE_WAIT(1),.MAX_TILES(')
  if finite:
   s=s.replace('.MAX_CYCLES(MODE==6?50:262144),.WAIT_CYCLES(32)', '.MAX_CYCLES(2097152),.WAIT_CYCLES(131072)')
   s=s.replace('MODE!=12','(MODE!=12 || ticks>=400000)').replace('MODE!=11','(MODE!=11 || ticks>=400000)').replace('MODE==0 || MODE==8','MODE==0 || MODE==11 || MODE==12 || MODE==8')
  else:s=s.replace('5,10,11,12:check(error==4', '11,12:check(error==3,"cooperative total");5,10:check(error==4')
  inst=re.search(r' nes_native_fill165 #\(.*?dut\(\.\*\);',s)[0]
  outputs=['query','query_kind','query_index','query_generation','mem_request','mem_abort','mem_address','mem_generation','byte_valid','byte_data','byte_tile','byte_lane','byte_kind','byte_generation','busy','done','quarantine','success','error','tile_count','byte_count','cycles']
  widths=[1,3,13,16,1,1,22,16,1,8,13,4,2,16,1,1,1,1,4,10,14,32]
  decl='\n'+''.join(f' wire [{w-1}:0] ref_{n};\n' for n,w in zip(outputs,widths))
  other=inst.replace('nes_native_fill165','reference_fill').replace(' dut(.*);',' refdut('+','.join('.'+n+'(ref_'+n+')' for n in outputs)+',.*);')
  assertion='\n always @(negedge clk) if(!reset && ticks>4) begin\n'+''.join(f'  if({n}!==ref_{n})$fatal(1,"counter equivalence {n} mode=%0d tick=%0d",MODE,ticks);\n' for n in outputs)+' end\n'
  s=s.replace(inst,inst+decl+other).replace('endmodule',assertion+'endmodule');(a.out/(name+'.sv')).write_text(s,encoding='utf8',newline='\n')
 for n in ['required.hex','chr.hex']:shutil.copy2(a.reference/n,a.out/n)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-3000:];return s
 run('vlib',['work'],'vlib');run('vlog',['-sv','candidate.sv','reference.sv','equiv_tb.sv','finite_tb.sv'],'vlog')
 for top,modes in [('equiv_tb',range(16)),('finite_tb',[11,12])]:
  for mode in modes:
   s=run('vsim',['-c','work.'+top,f'-gMODE={mode}','+REQUIRED=required.hex','+CHR=chr.hex',f'+OUTPUT={top}{mode}.tsv','-do','onerror {quit -code 1}; run -all; quit -f'],f'{top}{mode}')
   assert 'PASS FILL165' in s
 result=dict(passed=True,modes=18,outputs_compared_each_negedge=22,candidate_sha256=sha(a.candidate/'nes_native_fill165.sv'),reference_sha256=sha(a.reference/'nes_native_fill165.sv'),reference_result_sha256=sha(a.reference/'result.json'),public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_pacing167_equiv.py','tools/nes_pacing167.py','tests/nes-functional/native_fill165_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
