"""Existing screen151 bus qualification and atomic SPI73 user-stop publication."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_raw506 import sha

BENCH='''`timescale 1ns/1ps
module longrun693_tb;
 reg host=0,reset=1,active=0,rd=1,wr=1;always #5.952 host=!host;
 reg [23:0] addr=0;reg [7:0] data=0;
 `include "spi200_bus.svh"
 nes_screen_status151 dut(.clk(host),.reset(reset),.active(active),.address(addr),
 .read_n(rd),.write_n(wr),.romsel_n(1'b1),.data_in(data),.bus_drive(1'b0),
 .SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),.selected(selected197),.miso(miso197),.receive_write());
 task put(input [23:0] a,input [7:0] v);
  @(negedge host);addr=a;data=v;wr=0;repeat(8)@(negedge host);
  wr=1;repeat(8)@(negedge host);
 endtask
 task check(input [7:0] stage,input [7:0] err,input [15:0] frames);
  if(rx197[1]!==8'he6||rx197[2]!==stage||rx197[3]!==err||{rx197[5],rx197[6]}!==frames||rx197[7]!==3)
   $fatal(1,"status %h %h %h %h",rx197[1],rx197[2],rx197[3],rx197[7]);
 endtask
 task readstatus;
  begin197();byte197('h73,rx197[0]);for(int i=1;i<8;i++)byte197(0,rx197[i]);end197();
 endtask
 initial begin
  repeat(8)@(negedge host);reset=0;active=1;repeat(8)@(negedge host);
  put('h7001,'ha9);put('h7000,6);readstatus();check(6,'ha9,1);
  begin197();byte197('h73,rx197[0]);put('h7000,'h7e);
  for(int i=1;i<8;i++)byte197(0,rx197[i]);end197();check(6,'ha9,1);
  repeat(3)begin readstatus();check('h7e,'ha9,1);end
  // User request cannot overwrite an older fault result.
  put('h7001,'he1);readstatus();check('h7e,'ha9,1);
  reset=1;repeat(8)@(negedge host);reset=0;active=0;repeat(8)@(negedge host);
  put('h7000,'h7e);readstatus();if(rx197[2]!==0)$fatal(1,"inactive user stage accepted");
  $display("PASS693 user stage atomic, held, first result preserved, reset/inactive blocked");$finish;
 end
 initial begin #2000000;$fatal(1,"timeout693");end
endmodule
'''

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','out','bin'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    for src in (a.board/'nes_screen_status151.sv',root/'tests/nes-functional/spi200_bus.svh'):shutil.copyfile(src,a.out/src.name)
    (a.out/'test.sv').write_text(BENCH,newline='\n')
    for tool,args in [('vlib',['work']),('vlog',['-sv','nes_screen_status151.sv','test.sv']),('vsim',['-c','longrun693_tb','-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0'])]:
        with (a.out/(tool+'.log')).open('wb') as log:subprocess.run([a.bin/(tool+'.exe'),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    assert 'PASS693 user stage' in (a.out/'vsim.log').read_text()
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,RTL=sha(a.out/'nes_screen_status151.sv'),bench=sha(a.out/'test.sv'),log=sha(a.out/'vsim.log'),new_RTL=False),indent=2)+'\n')
    print('PASS693 unchanged screen RTL bus/SPI boundaries')
