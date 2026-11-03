// SPDX-License-Identifier: MIT
// Pin-level SNES consume strobes against the real aperture / 194 control.
reg memory_open=0,memory_reply=0,rd_n=1,wr_n=1;
reg [21:0] reply_address=0;
reg [23:0] bus=0;
reg [7:0] wdata=0;
integer consumes=0;
always @(posedge nes_clk)begin
 memory_reply<=memory_open&&dut.mem_request&&!reset;
 if(dut.mem_request)reply_address<=dut.mem_address;
end
always @(posedge host_clk)if(dut.consume)consumes++;
task reg_write(input [23:0] a,input [7:0] value);
 @(negedge host_clk);bus=a;wdata=value;wr_n=0;
 repeat(6)@(negedge host_clk);wr_n=1;repeat(6)@(negedge host_clk);
endtask
task bulk570;
 restart();memory_open=1;
 data_frame(0,32);wait(dut.chunk_ready);
 if(dut.chunk_length!=16||dut.chunk_token!=1)$fatal(1,"old descriptor");
 reg_write(24'h604c,1);reg_write(24'h604d,0);
 @(negedge host_clk);bus=24'h400800;rd_n=0;repeat(6)@(negedge host_clk);
 if(dut.oe_n||dut.data_out!==0)$fatal(1,"old aperture unreadable");
 host_on=0;nes_on=0;core_fault=1;#100;
 if(!dut.oe_n||dut.dir||dut.consume||dut.pr||dut.pv)$fatal(1,"stopped read still driven");
 if(dut.chunk_ready!==!$test$plusargs("SHARED"))$fatal(1,"bank cancel ownership");
 $display("BULK570 gated=1 chunk_after_raw=%0d",dut.chunk_ready);
 rd_n=1;finish_fault();restart();
 // A new single-BG/END packet produces 16 different bytes in token 1.
 $readmemh("fresh.hex",raw,0,17);data_frame(0,18);wait(dut.chunk_ready);
 if(dut.chunk_length!=16||dut.chunk_token!=1||dut.chunk_slot!=1)$fatal(1,"fresh descriptor");
 for(int i=0;i<16;i++)begin
  bus=24'h400800+i;rd_n=0;repeat(6)@(negedge host_clk);
  if(dut.oe_n||dut.data_out!==8'h63)$fatal(1,"fresh aperture %0d %h",i,dut.data_out);
 end
 rd_n=1;
 if($test$plusargs("PARTIAL"))begin
  reg_write(24'h604e,0);reg_write(24'h604f,0);reg_write(24'h6050,8'ha5);
  wait(hf);if(consumes!=0)$fatal(1,"cross-STOP token write");
 end else begin
  reg_write(24'h604c,1);reg_write(24'h604d,0);reg_write(24'h604e,0);reg_write(24'h604f,0);reg_write(24'h6050,8'ha5);
  if(consumes!=1||dut.chunk_ready||hf||nf)$fatal(1,"fresh consume");
 end
 $display("PASS570 BULK consumes=%0d",consumes);
endtask
