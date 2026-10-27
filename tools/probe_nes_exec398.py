# SPDX-License-Identifier: MIT
"""Execute shared byte ISA bounds against the independent396 ABI vectors."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from nes_host398 import host_program

TB=r'''`timescale 1ns/1ps
module exec398_tb;
 reg clk=0;always #5 clk=~clk;reg reset=1,stop=0;
 wire[11:0]code_address,debug_pc;reg[17:0]code_data;reg[11:0]tag;
 reg[17:0]rom[0:4095];reg[7:0]ctx[0:255];reg[97:0]vectors[0:23999];
 wire mem_valid,mem_write,io_valid,io_write,fault,in_irq;wire[7:0]mem_address,mem_data,io_address,io_data;
 reg[7:0]mem_q;reg mseen=0;reg bank=0;
 always @(posedge clk)begin code_data<=rom[code_address];tag<=code_address;mem_q<=ctx[mem_address];
  if(reset)mseen<=0;
  else if(mem_valid&&!mseen)begin if(mem_write)ctx[mem_address]<=mem_data;mseen<=1;end
  else if(mem_valid&&mseen)mseen<=0;
 end
 nes_byte398 #(.ENTRY(BOUNDS)) cpu(.clk(clk),.reset(reset),.stop(stop),.irq(1'b0),
 .code_address(code_address),.code_data(code_data),.code_ready(tag==debug_pc),
 .mem_valid(mem_valid),.mem_write(mem_write),.mem_address(mem_address),.mem_data(mem_data),.mem_ready(mseen),.mem_q(mem_q),
 .io_valid(io_valid),.io_write(io_write),.io_address(io_address),.io_data(io_data),.io_ready(1'b1),.io_q({7'd0,bank}),.fault(fault),.in_irq(in_irq),.debug_pc(debug_pc));
 integer n,bad,cycles;
 initial begin
  $readmemh("program398.hex",rom);$readmemh("vectors.hex",vectors);
  for(n=0;n<24000;n++)begin
   reset=1;repeat(3)@(negedge clk);
   for(integer i=0;i<256;i++)ctx[i]=0;
   for(integer i=0;i<12;i++)ctx[i]=vectors[n][i*8+:8];ctx[80]=1;bank=vectors[n][96];
   reset=0;cycles=0;bad=-1;
   while(bad<0&&cycles<4000)begin
    @(negedge clk);cycles++;
    if(fault)$fatal(1,"ISA fault vector%0d pc%0d",n,debug_pc);
    if(io_valid&&io_write&&io_address==8)bad=1;
    if(debug_pc==0)bad=0;
   end
   if(bad!=vectors[n][97])$fatal(1,"byte bounds vector%0d record%h bank%0d got%0d want%0d pc%0d",n,vectors[n][95:0],bank,bad,vectors[n][97],debug_pc);
  end
  stop=1;repeat(10)begin @(negedge clk);if(mem_valid||io_valid)$fatal(1,"STOP leak");end
  $display("EXEC398 PASS vectors24000 STOP_no_mutation");$finish;
 end
endmodule
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 prog=host_program();code=prog.finish();code+=([15<<14|255]*(4096-len(code)))
 (d/'program398.hex').write_text('\n'.join(f'{x:05x}'for x in code)+'\n',newline='\n')
 (d/'exec398_tb.sv').write_text(TB.replace('BOUNDS',str(prog.labels['bounds'])),newline='\n')
 shutil.copyfile(ROOT/'src/fpga/nes_exec398/nes_byte398.sv',d/'nes_byte398.sv');shutil.copyfile(BASE/'probes/nes-joint396/edges03/vectors.hex',d/'vectors.hex')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 for name,args in [('vlib',['work']),('vlog',['-sv','nes_byte398.sv','exec398_tb.sv']),('vsim',['-c','work.exec398_tb','-do','onerror {quit -code 1};run -all;quit -f'])]:
  with(d/(name+'.log')).open('wb')as log:r=subprocess.run([str(q/(name+'.exe'))]+args,cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-2500:]
 assert 'EXEC398 PASS'in(d/'vsim.log').read_text()
 report=dict(passed=True,vectors=24000,host_words=len(prog.code),pins={q.name:sha(q)for q in d.iterdir()if q.is_file()});(d/'result.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS EXEC398',len(prog.code))
if __name__=='__main__':main()
