# SPDX-License-Identifier: MIT
"""Same-edge actual SPI RTL equivalence, priority truth table and serial faults."""
import argparse,json,os,subprocess
from pathlib import Path
from nes_fault507 import transform
from check_nes_game478 import sha

TB=r'''
`timescale 1ns/1ps
module tb;
 reg clk=0,reset=1,ss=1,sck=0,mosi=0,boot_fault=0,check_fault=0,response=0;
 reg loaded=1,ready=1;reg[18:0] addr=0;reg[7:0] data=8'h42;
 always #3 clk=~clk;
 wire[43:0] a,b;
 @INST@
 integer rows=0,serial=0;reg differential=1;
 always @(posedge clk)begin #0.01;if(differential && a!==b)$fatal(1,"OUTPUT507 %h %h",a,b);end
 task restart;
  @(negedge clk);reset=1;ss=1;sck=0;mosi=0;boot_fault=0;check_fault=0;response=0;
  repeat(5)@(negedge clk);reset=0;repeat(5)@(negedge clk);
 endtask
 function automatic[7:0] crc8(input[7:0] p,v);
  reg[7:0] c;c=p^v;repeat(8)c=c[7]?(c<<1)^8'h07:c<<1;return c;
 endfunction
 task frame(input[7:0] op,input[23:0] off,input[7:0] arg,input integer inject);
  reg[7:0] tx[0:7];reg[7:0] c;reg[63:0] bits;
  tx[0]=op;tx[1]=off[23:16];tx[2]=off[15:8];tx[3]=off[7:0];tx[4]=arg;tx[5]=~arg;
  c=0;for(integer k=0;k<6;k++)c=crc8(c,tx[k]);tx[6]=c;tx[7]=8'ha5;
  bits=0;ss=0;#2000;
  for(integer j=0;j<64;j++)begin
   if(j==inject)boot_fault=1;
   mosi=tx[j/8][7-j%8];#190.476;sck=1;#100;bits={bits[62:0],a[43]};#90.476;sck=0;
  end
  #2000;ss=1;#2000;serial++;
 endtask
 reg hard,resp,over,pend;reg[3:0] decoded,prior;reg sticky;
 initial begin
  restart();differential=0;
  force dut.error_hard=hard;force refdut.error_hard=hard;
  force dut.error_response=resp;force refdut.error_response=resp;
  force dut.error_overlap=over;force refdut.error_overlap=over;
  force dut.pending=pend;force refdut.pending=pend;
  force dut.decoded_error=decoded;force refdut.decoded_error=decoded;
  for(integer i=0;i<8192;i++)begin
   @(negedge clk);{sticky,prior,hard,resp,over,pend,decoded}=i[12:0];
   dut.fault=sticky;refdut.fault=sticky;dut.error_code=prior;refdut.error_code=prior;
   @(posedge clk);#0.02;
   if(dut.error_code!==refdut.error_code)$fatal(1,"CODE507 row=%0d got=%h expected=%h",i,dut.error_code,refdut.error_code);
   rows++;
  end
  release dut.error_hard;release refdut.error_hard;release dut.error_response;release refdut.error_response;
  release dut.error_overlap;release refdut.error_overlap;release dut.pending;release refdut.pending;
  release dut.decoded_error;release refdut.decoded_error;
  restart();differential=1;
  frame('h65,0,0,-1);frame('h64,1,0,-1);
  if(dut.fault)$fatal(1,"idle STOP failed");
  // Real CHECK/READ/response/ACK and final verification, no forced state.
  frame('h66,0,0,-1);frame('h67,0,0,-1);
  if(!dut.check_busy)$fatal(1,"READ not owned");
  @(negedge clk);response=1;@(negedge clk);response=0;repeat(5)@(negedge clk);
  frame('h68,0,'h42,-1);frame('h69,1,0,-1);
  if(!dut.verified || dut.fault)$fatal(1,"verification failed");
  frame('h63,1,0,-1);frame('h64,1,0,-1);
  if(dut.fault)$fatal(1,"START STOP failed");
  // Inject live boot fault at every serial bit, including snapshot capture.
  for(integer bitpos=0;bitpos<64;bitpos++)begin
   restart();frame('h66,0,0,-1);frame('h6a,0,0,bitpos);
   if(!dut.fault || dut.error_code!=9 || dut.check_enable)$fatal(1,"hard fault not immediate");
   frame('h64,0,0,-1);frame('h65,0,0,-1);
   if(dut.stop || dut.error_code!=9)$fatal(1,"sticky fault escaped");
  end
  // Wrong tag, unsolicited response and CHECK fault all fail closed.
  for(integer mode=0;mode<3;mode++)begin
   restart();frame('h66,0,0,-1);
   if(mode==0)begin frame('h67,0,0,-1);addr=1;end
   @(negedge clk);if(mode==2)check_fault=1;else response=1;
   @(negedge clk);response=0;repeat(5)@(negedge clk);
   if(!dut.fault || dut.error_code!=(mode==0?7:9))$fatal(1,"response guard");addr=0;
  end
  $display("PASS507 rows=%0d serial=%0d",rows,serial);$finish;
 end
 initial begin #20000000;$fatal(1,"TIMEOUT507");end
endmodule
'''

def inst(name,module,bus):
    ports=dict(mem_clk='clk',reset='reset',SPI_SS='ss',SPI_SCK='sck',SPI_MOSI='mosi',spi_miso=f'{bus}[43]',spi_selected=f'{bus}[42]',load_ready='ready',loaded='loaded',run_enable="1'b0",boot_fault='boot_fault',boot_error="4'd6",loaded_bytes="19'd1",load_begin=f'{bus}[41]',load_chr32=f'{bus}[40]',load_valid=f'{bus}[39]',load_end=f'{bus}[38]',start=f'{bus}[37]',stop=f'{bus}[36]',load_data=f'{bus}[35:28]',fault=f'{bus}[27]',error_code=f'{bus}[26:23]',check_enable=f'{bus}[22]',check_request=f'{bus}[21]',check_address=f'{bus}[18:0]',check_ready='ready',check_response='response',check_fault='check_fault',check_response_address='addr',check_data='data')
    return module+' '+name+'('+','.join('.'+k+'('+v+')'for k,v in ports.items())+');assign '+bus+"[20:19]=0;"

def run(a):
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    a.out.mkdir(parents=True,exist_ok=False)
    old=(a.base/'nes_rom_spi.sv').read_text();new=(a.board/'nes_rom_spi.sv').read_text();assert new==transform(old)
    (a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module reference('))
    (a.out/'tb.sv').write_text(TB.replace('@INST@',inst('dut','nes_rom_spi_check','a')+inst('refdut','reference','b')))
    def q(tag,args):
        with(a.out/(tag+'.log')).open('wb')as f:r=subprocess.run([str(a.bin/(args[0]+'.exe')),*args[1:]],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
        return r.returncode,(a.out/(tag+'.log')).read_text(errors='replace')
    code,log=q('lib',['vlib','work']);assert code==0,log
    for name,src in [('normal',new),('priority-mutant',new.replace('error_code[2]<=!error_hard &&','error_code[2]<=1\'b1 &&'))]:
        assert name=='normal' or src!=new
        (a.out/'candidate.sv').write_text(src)
        code,log=q(name+'-compile',['vlog','-sv','reference.sv','candidate.sv','tb.sv']);assert code==0 and '** Error' not in log,log
        code,log=q(name,['vsim','-c','tb','-do','onerror {quit -code 1};onbreak {quit -code 1};run -all;quit -f'])
        if name=='normal':assert code==0 and 'PASS507 rows=8192' in log and '** Fatal' not in log,log
        else:assert '** Fatal: CODE507' in log and 'PASS507' not in log,log
    result=dict(passed=True,rows=8192,serial_fault_bit_positions=64,priority_mutant_rejected=True,scope=__doc__,baseline_SHA256=sha(a.base/'nes_rom_spi.sv'),candidate_SHA256=sha(a.board/'nes_rom_spi.sv'),bench_SHA256=sha(a.out/'tb.sv'))
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['base','board','out','bin']:p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
