"""Current two-bank plan RTL: generation wrap, stale identity and stopped-clock cancel."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_raw506 import sha

BENCH=r'''
`timescale 1ps/1ps
module longrun694_plan_tb;
 reg host_clk=0,nes_clk=0,nes_on=1,reset=1,stop=0,active=1,source_fault=0;
 always #5952 host_clk=!host_clk;
 initial begin if($test$plusargs("SHIFT"))#11000;forever #23281 if(nes_on)nes_clk=!nes_clk;end
 reg write_valid=0,seal=0,plan_ready=0,tile_done=0,retire=0,end_ready=0,lease_valid=1,retire_permitted=1;
 reg [7:0] write_data=0;reg [9:0] seal_length=0;reg [4:0] seal_plans=1;
 reg [15:0] seal_crc=0,lease_generation=16'hfffe;
 wire write_ready,retire_done,retire_commit,host_idle,fault,plan_valid,end_valid,plan_short,plan_closed,witness_host,witness_reject;
 wire [9:0] plan_slot;wire [12:0] plan_tag;wire [103:0] plan_alt_tags;
 wire [7:0] plan_alt_mask,plan_mask;wire [1:0] plan_kind;wire [15:0] plan_generation,end_generation;wire [47:0] plan_rows;
 nes_plan_batch206 dut(.*);
 integer plans=0,ends=0,retires=0;
 always @(posedge nes_clk)begin if(plan_valid&&plan_ready)plans++;if(end_valid&&end_ready)ends++;if(retire_commit)retires++;end
 function automatic [15:0] crc(input [15:0] prior,input [7:0] b);
  reg [15:0] c;c=prior^{b,8'd0};for(int i=0;i<8;i++)c=c[15]?(c<<1)^16'h1021:c<<1;return c;
 endfunction
 task send(input [15:0] gen,input bit last);
  reg [15:0] c;reg [7:0] b;integer n;n=last?3:7;c=16'hffff;
  for(int i=0;i<n;i++)begin
   @(negedge host_clk);wait(write_ready);
   case(i)0:b=last?8'h83:8'h80;1:b=gen[7:0];2:b=gen[15:8];3:b=17;5:b=23;default:b=0;endcase
   write_valid=1;write_data=b;c=crc(c,b);
  end
  @(negedge host_clk);write_valid=0;seal=1;seal_length=n;seal_crc=c;
  @(negedge host_clk);seal=0;
 endtask
 task complete(input [15:0] gen);
  lease_generation=gen;send(gen,0);send(gen,1);
  wait(plan_valid);repeat(16)begin @(negedge nes_clk);if(!plan_valid||plan_generation!==gen||plan_slot!=17||plan_tag!=23)$fatal(1,"unstable owned plan");end
  plan_ready=1;@(negedge nes_clk);plan_ready=0;
  repeat(4)@(negedge nes_clk);tile_done=1;@(negedge nes_clk);tile_done=0;
  wait(end_valid);if(end_generation!==gen||fault)$fatal(1,"END generation");
  @(negedge nes_clk);end_ready=1;@(negedge nes_clk);end_ready=0;
  wait(host_idle);@(negedge host_clk);retire=1;@(negedge host_clk);retire=0;
  wait(retire_done);repeat(8)@(negedge host_clk);if(fault)$fatal(1,"retire fault");
 endtask
 task cancel;
  nes_on=0;#1000;stop=1;#100;
  if(write_ready||plan_valid||end_valid||retire_commit)$fatal(1,"STOP leaked with clock stopped");
  tile_done=1;#1000;stop=0;#200000;
  if(plan_valid||end_valid||retire_commit)$fatal(1,"stale completion after STOP");
  nes_on=1;tile_done=0;wait(host_idle);repeat(12)@(negedge nes_clk);
  if(fault||plan_valid||end_valid)$fatal(1,"cancel failed to reset ownership");
 endtask
 initial begin
  #80000;reset=0;wait(host_idle);
  complete(16'hfffe);complete(16'hffff);complete(16'h0000);
  if(plans!=3||ends!=3||retires!=3)$fatal(1,"wrap completion count");
  lease_generation=1;send(0,0);wait(fault);
  if(plan_valid||end_valid)$fatal(1,"stale generation accepted");cancel();
  lease_generation=2;send(2,0);wait(plan_valid);cancel();
  complete(3);if(plans!=4||ends!=4||retires!=4)$fatal(1,"old completion survived cancel");
  $display("PASS694 plan wrap FFFE FFFF 0000, stale reject, stopped-clock cancel, recovery");$finish;
 end
 initial begin #500000000;$fatal(1,"plan watchdog");end
endmodule
'''
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','out','bin'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    names=['nes_plan_batch206.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv']
    for n in names:shutil.copyfile(a.board/n,a.out/n)
    (a.out/'test.sv').write_text(BENCH,newline='\n')
    for t,args,name in [('vlib',['work'],'vlib'),('vlog',['-sv',*names,'test.sv'],'vlog'),*[( 'vsim',['-c','longrun694_plan_tb',*(['+SHIFT'] if shift else []),'-do','onbreak {quit -code 1};onerror {quit -code 1};run -all;quit -code 0'],f'phase{shift}') for shift in (0,1)]]:
        with (a.out/(name+'.log')).open('wb') as f:subprocess.run([a.bin/(t+'.exe'),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=60,check=True)
    for shift in (0,1):assert 'PASS694 plan wrap' in (a.out/f'phase{shift}.log').read_text()
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,phases=2,pins={n:sha(a.out/n) for n in [*names,'test.sv','phase0.log','phase1.log']},scope=__doc__),indent=2)+'\n')
    print('PASS694 current plan RTL wrap/cancel2 phases')
