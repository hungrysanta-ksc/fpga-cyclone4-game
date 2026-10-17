# SPDX-License-Identifier: MIT
"""Existing220 bridge admission, actual E0 replies and paired212 ROM response.

RUN/reset and SNES pins are fixtures. No physical reset-release or wholeboard proof.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_runtime213 import ROOT,BASE,sha
TB=r'''
`timescale 1ns/1ps
module startup222;
 reg clk=0,reset=1,active=0,stop=0,ss=1,sck=0,mosi=0;
 reg [23:0] address=0;reg rn=1,wn=1,romsel=1;reg [7:0] din=0;
 wire selected,miso,oe,dir,pc,fault;wire [7:0] dout;wire [15:0] pads;
 nes_sink_bridge165 dut(clk,reset,active,stop,ss,sck,mosi,selected,miso,address,rn,wn,romsel,din,dout,oe,dir,pc,pads,fault);
 always #5.952 clk=~clk;
 integer fd,checks=0;reg [7:0] rx[0:19];
 task query(input integer expected);
 integer x,k;reg [7:0] tx;
 begin
  #2000;ss=0;#2000;
  for(x=0;x<20;x++)begin tx=x==0?8'he0:0;rx[x]=0;
   for(k=7;k>=0;k--)begin mosi=tx[k];#190.476;sck=1;rx[x][k]=selected?miso:0;#190.476;sck=0;end
  end
  #2000;ss=1;#2000;
  if(expected)begin
   if(rx[1]!==8'hf7||fault||!dut.host_ready||dut.session_reset)$fatal(1,"admission failed");
   for(x=2;x<19;x++)if(rx[x]!==0)$fatal(1,"nonempty initial state");
  end else begin
   for(x=0;x<20;x++)if(rx[x]!==0)$fatal(1,"blocked bridge selected");
  end
  $fwrite(fd,"%0d",expected);for(x=0;x<20;x++)$fwrite(fd," %02h",rx[x]);$fwrite(fd,"\n");checks++;
 end endtask
 task readbyte(input [23:0] at,input [7:0] expected);
 begin address=at;rn=0;wn=1;romsel=0;#100;
  if(oe||!dir||dout!==expected)$fatal(1,"ROM not ready after positive E0 %h %h",at,dout);
  rn=1;romsel=1;#100;checks++;
 end endtask
 initial begin
  fd=$fopen("replies.txt","w");if(!fd)$fatal(1,"output");
  #200;reset=0;#300;query(0); // inactive RUN cannot admit.
  ss=0;active=1;#300;query(0); // active but no SPI idle boundary.
  query(1);readbyte(24'h00fffc,0);readbyte(24'h00fffd,128);readbyte(24'h008000,8'h78);
  active=0;reset=1;#300;wn=0;reset=0;active=1;#300;
  query(0); // SNES /WR held low prevents admission even when RESET sense is high.
  wn=1;#300;query(1);readbyte(24'h00fffc,0);readbyte(24'h00fffd,128);
  $fclose(fd);$display("PASS STARTUP222_BRIDGE checks=%0d replies=5",checks);$finish;
 end
endmodule
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert str(d).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True,exist_ok=False)
 board=BASE/'probes/nes-status220/source02';names=['nes_domain_reset124.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv']
 for n in names:shutil.copyfile(board/n,d/n)
 rom=BASE/'probes/nes-runtime213/asm01/sink-program.hex';shutil.copyfile(rom,d/'sink-program.hex')
 (d/'startup222.sv').write_text(TB,encoding='utf8')
 for label,args in [('vlib',['vlib.exe','work']),('vlog',['vlog.exe','-sv',*names,'startup222.sv']),('vsim',['vsim.exe','-c','work.startup222','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (d/(label+'.log')).open('wb') as f:q=subprocess.run([str(a.questa_bin/args[0]),*args[1:]],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(d/(label+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
 assert 'PASS STARTUP222_BRIDGE checks=10 replies=5' in t
 r=dict(passed=True,rtl_pins={n:sha(board/n) for n in names},rom_sha256=sha(rom),replies_sha256=sha(d/'replies.txt'),source_sha256=sha(Path(__file__)),physical=False,root_cause_reproduced=False,scope=__doc__)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print('PASS STARTUP222 bridge replies and paired ROM')
if __name__=='__main__':main()
