// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module screen137_bus_tb;
 reg host_clk=0,reset=1,run_enable=0,read_n=1,write_n=1,romsel_n=1;
 always #5.952 host_clk=~host_clk;
 reg [23:0] address=0;reg [7:0] link_data=8'ha6;
 reg link_oe_n=1,link_dir=0;
 wire [7:0] data_out;wire oe_n,dir;
 nes_screen_bus137 dut(.*);
 reg [7:0] golden[0:65535];integer checks=0;
 task automatic ck(input bit ok,input string why);
  checks++;if(!ok)$fatal(1,"BUS137 %s address=%h data=%h",why,address,data_out);
 endtask
 initial begin
  $readmemh("screen-full.hex",golden);#100;
  address=24'h008000;read_n=0;romsel_n=0;#100;ck(oe_n&&!dir,"reset isolation");
  reset=0;run_enable=1;
  for(integer a=0;a<65536;a++)begin
   address={7'd0,a[15],1'b1,a[14:0]};#80;
   ck(!oe_n&&dir&&data_out===golden[a],"entire LoROM image/atlas/vector roundtrip");
   read_n=1;#0.001;ck(oe_n&&!dir,"raw read release");#20;read_n=0;
  end
  read_n=1;address=24'h00600b;romsel_n=1;#30;read_n=0;#30;ck(dir&&!oe_n&&data_out==1,"epoch low");
  read_n=1;address=24'h00600c;#30;read_n=0;#30;ck(dir&&!oe_n&&data_out==0,"epoch high");
  read_n=1;address=24'h408000;romsel_n=0;#30;read_n=0;link_oe_n=0;link_dir=1;#30;
  ck(dir&&!oe_n&&data_out==8'ha6,"packet path");
  reset=1;#0.001;ck(oe_n&&!dir,"reset gates retained link drive");
  reset=0;run_enable=0;#0.001;ck(oe_n&&!dir,"STOP gates retained link drive");
  $display("PASS137 BUS rom_bytes=65536 checks=%0d",checks);$finish;
 end
endmodule
