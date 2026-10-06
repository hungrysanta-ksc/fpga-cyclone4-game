# SPDX-License-Identifier: MIT
"""Actual post-fit041 netlist/SDF experiment. No timing-check suppression."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
TB=r'''
`timescale 1ns/1ps
module gate_tb;
 parameter PHASE=0;
 reg CLKIN=0;always #62.5 CLKIN=~CLKIN;
 reg [23:0] SNES_ADDR_IN=0;
 reg SNES_READ_IN=1,SNES_WRITE_IN=1,SNES_ROMSEL_IN=1;
 reg SPI_MOSI=0,SPI_SS=1,SPI_SCK=0;
 wire SPI_MISO,MCU_RDY,SNES_DATABUS_OE,SNES_DATABUS_DIR;
 tri [7:0] SNES_DATA;reg [7:0] write_data=0;reg host_drive=0;
 assign SNES_DATA=host_drive?write_data:8'hzz;
 fxpak_nes_h1_top dut(.CLKIN(CLKIN),.SNES_ADDR_IN(SNES_ADDR_IN),.SNES_READ_IN(SNES_READ_IN),.SNES_WRITE_IN(SNES_WRITE_IN),.SNES_ROMSEL_IN(SNES_ROMSEL_IN),.SNES_DATA(SNES_DATA),.SPI_MOSI(SPI_MOSI),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MISO(SPI_MISO),.MCU_RDY(MCU_RDY),.SNES_DATABUS_OE(SNES_DATABUS_OE),.SNES_DATABUS_DIR(SNES_DATABUS_DIR),.SNES_CIC_CLK(1'b0),.SNES_CPU_CLK_IN(1'b0),.SNES_REFRESH(1'b0),.SNES_SYSCLK(1'b0),.SNES_PA_IN(8'b0),.SNES_PARD_IN(1'b1),.SNES_PAWR_IN(1'b1));
 reg [7:0] pattern[0:6143],ignored,reply,data;
 integer read_count=0;
 task automatic byte_io(input [7:0] tx,output [7:0] rx);
  for(integer b=7;b>=0;b--)begin SPI_MOSI=tx[b];#2000;SPI_SCK=1;#2000;rx[b]=SPI_MISO;SPI_SCK=0;end
  #2000;
 endtask
 task automatic query(input [7:0] cmd,output [7:0] rx);
  SPI_SS=0;#2000;byte_io(cmd,ignored);byte_io(0,rx);SPI_SS=1;#2000;
 endtask
 task automatic control(input [7:0] cmd);
  SPI_SS=0;#2000;byte_io(cmd,ignored);byte_io(8'ha5,ignored);byte_io(8'h5a,ignored);SPI_SS=1;#2000;
 endtask
 task automatic wr(input [23:0] addr,input [7:0] value);
  SNES_ADDR_IN=addr;SNES_ROMSEL_IN=1;write_data=value;host_drive=1;#40;SNES_WRITE_IN=0;#220;
  SNES_WRITE_IN=1;#40;host_drive=0;#160;
 endtask
 task automatic rd(input [23:0] addr,input regsel,output [7:0] rx);
  SNES_ADDR_IN=addr;SNES_ROMSEL_IN=regsel;#30;SNES_READ_IN=0;
  #180;rx=SNES_DATA;#34;SNES_READ_IN=1;#125;
 endtask
 task automatic dump;
  $display("GATE RAW frontend=%h aggregate=%h causal=%h reads=%0d",
   dut.\boundary|link|transport|frontend|frontend_error ,
   dut.\boundary|fault_snapshot ,dut.\boundary|link|transport|frontend|frontend_snapshot ,read_count);
 endtask
 initial begin
  $readmemh("h1-pattern.hex",pattern);
  wait(MCU_RDY===1);#10000;query(8'hf0,reply);if(reply!==8'ha5)$fatal(1,"gate identity %h",reply);
  query(8'hf1,reply);if(reply!==8'h41)$fatal(1,"gate protocol %h",reply);
  control(8'he8);#100000;
  wr(24'h6002,1);wr(24'h6003,0);wr(24'h6004,1);wr(24'h6005,0);wr(24'h6000,1);
  wait(dut.\boundary|link|transport|stage|state.READY~q ===1);#1000;rd(24'h6000,1,data);if(data!==1)begin dump();$fatal(1,"gate acquire %h",data);end
  #(PHASE);
  for(integer i=0;i<512;i++)begin
   rd(24'h408000+i,0,data);
   if(data!==pattern[i])begin $display("GATE MISMATCH addr=%h got=%h want=%h",24'h408000+i,data,pattern[i]);dump();$finish;end
   read_count++;
  end
  dump();$display("PASS GATE PAYLOAD512 phase=%0d",PHASE);$finish;
 end
 initial begin #10000000;$fatal(1,"gate watchdog");end
endmodule
'''
def read_payload(log):
 m=re.search(r'GATE RAW.*reads=(\d+)',log);return int(m.group(1)) if m else 0
def main():
 p=argparse.ArgumentParser()
 for n in ('out','build','questa-bin','netlist'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--sdf-mode',choices=('max','none'),default='max')
 a=p.parse_args();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 out=a.out;out.mkdir();shutil.copy2(a.build/'h1-pattern.hex',out/'h1-pattern.hex')
 original=a.netlist.read_text();needle='initial $sdf_annotate("board_v.sdo");';assert original.count(needle)==1
 (out/'board.original.vo').write_text(original)
 (out/'board.vo').write_text(original.replace(needle,'// SDF is selected explicitly by this driver.'))
 shutil.copy2(a.netlist.parent/'board_v.sdo',out/'board_v.sdo');(out/'gate_tb.sv').write_text(TB)
 jobs=[('vlib','vlib',['work']),('compile','vlog',['-sv','board.vo','gate_tb.sv'])]
 lib=a.questa_bin.parent/'intel/verilog/cycloneive'
 jobs+=[('gate','vsim',['-c','-t','1ps','-L',str(lib),'-L',str(lib.parent/'altera'),'gate_tb',*(['-sdfmax','/gate_tb/dut=board_v.sdo'] if a.sdf_mode=='max' else []),'-do','onerror {quit -code 1}; run -all; quit -f'])]
 for label,tool,args in jobs:
  with (out/(label+'.log')).open('wb') as f:cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  assert cp.returncode==0,label
 log=(out/'gate.log').read_text(errors='replace')
 fatal=bool(re.search(r'\*\* Fatal:',log));assert not fatal,log[-2000:]
 timing_errors=len(re.findall(r'\*\* Error:',log))
 annotated='SDF Backannotation Successfully Completed' in log
 assert annotated==(a.sdf_mode=='max'),'Unexpected SDF mode; inspect embedded annotation' 
 assert 'GATE RAW' in log and ('PASS GATE PAYLOAD512' in log or 'GATE MISMATCH' in log)
 (out/'result.json').write_text(json.dumps({'diagnostic_completed':True,'sdf_mode':a.sdf_mode,'payload_bytes':read_payload(log),'payload_match':'PASS GATE PAYLOAD512' in log,'timing_errors':timing_errors,'timing_pass':timing_errors==0,'scope':'Actual041 fitted netlist; '+('slow85C SDF' if a.sdf_mode=='max' else 'unannotated functional control')+' and real PLL model; synthetic pins, no physical waveform or hardware signoff'},indent=2))
 print(log[-2400:])
if __name__=='__main__':main()
