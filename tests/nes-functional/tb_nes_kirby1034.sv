`timescale 1ns/1ns
module tb_nes_kirby1034;
 reg clk=0,reset=1,cancel=0,first=0,accept=0,ret=0,group_start=0;
 reg tile=0,header=0,retired=0,dma=0,show=0,query=0;
 reg [7:0] op=0;
 reg [4:0] index=0;
 wire [7:0] reply;
 reg writer=0;
 reg [7:0] record[0:31];
 always #5 clk=!clk;
 nes_display1010 dut(.clk(clk),.reset(reset),.active(1'b1),.cancel(cancel),
  .first_e9(first),.accepted1034(accept),.group1034(group_start),.returned(ret),
  .writer(writer),.tile_done(tile),.token(32'd3184),.generation(16'd1561),
  .header(header),.data(8'd3),.retired(retired),.op(op),.dma(dma),.show(show),
  .query(query),.index(index),.reply(reply));
 task step; @(negedge clk); endtask
 task begin_frame; op=1;retired=1;step;retired=0;endtask
 task finish_frame;
  header=1;step;header=0;dma=1;step;dma=0;show=1;step;show=0;
  retired=1;op=3;step;retired=0;step;query=1;step;query=0;
  for(integer i=0;i<32;i++)begin index=i;repeat(3)step;record[i]=reply;end
 endtask
 task tick(input integer value);dut.clock_count=value<<15;endtask
 task run_frame(input integer extra);
  first=1;tick(250);step;first=0;begin_frame;
  for(integer i=0;i<4;i++)begin
   tick(251+i*3);accept=1;ret=(i!=0);
`ifdef PUBLISH1035
   writer=!writer;
`endif
   step;accept=0;ret=0;
   group_start=1;repeat(4)step;group_start=0;repeat(4)step;
  end
  if(extra!=0)begin accept=1;
`ifdef PUBLISH1035
   writer=!writer;
`endif
   step;accept=0;end
  tick(265);ret=1;step;ret=0;
  for(integer i=0;i<15;i++)begin tile=1;repeat(4)step;tile=0;repeat(4)step;end
  tick(268);finish_frame;
`ifdef PUBLISH1035
  if(record[1]!==8'ha5 || record[31]!==8'ha5 || record[5]!==4 || record[4]!==15 ||
     record[21][7:4]!==4+extra || record[20]!==0 || {record[29],record[28]}!==268)
`else
  if(record[1]!==8'ha4 || record[31]!==8'ha5 || record[5]!==4 || record[4]!==15 ||
     record[21][7:4]!==(8+4+extra) || record[20]!==4 || {record[29],record[28]}!==268)
`endif
    $fatal(1,"header counts, identity or ACK timing");
  for(integer i=0;i<4;i++)
   if(record[8+i]!==8'(251+i*3) || record[24+i]!==8'(i==3?265:254+i*3))
    $fatal(1,"accept/return order or wrap");
  if(extra==0)begin
   $write("HEADER1034 ");for(integer i=0;i<32;i++)$write("%02x",record[i]);$display("");
  end
 endtask
 initial begin
  repeat(5)step;reset=0;repeat(4)step;tick(238);begin_frame;finish_frame;
  run_frame(0);run_frame(1);cancel=1;repeat(4)step;
  if(reply!==0 || dut.complete!==0)$fatal(1,"STOP did not revoke snapshot");
  $display("PASS1034 simultaneous accept/return, low-byte wrap, overflow, STOP");$finish;
 end
endmodule
