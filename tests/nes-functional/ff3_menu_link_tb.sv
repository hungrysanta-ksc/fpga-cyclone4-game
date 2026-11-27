`timescale 1ns/1ps
module ff3_menu_link_tb;
 reg clk=0, reset=1, active=1, cancel=0, ss=1, sck=0, mosi=0, wr=1;
 reg [23:0] addr=0;
 reg [7:0] din=0;
 wire miso,selected,receive_write;
 wire [7:0] status;
 always #6 clk=!clk;
 nes_screen_status151 dut(.clk(clk),.reset(reset),.active(active),.trace_cancel(cancel),
  .accepted1034(1'b0),.group1034(1'b0),.evt905(3'd0),.first905(1'b0),.ret905(1'b0),
  .units905(8'd0),.writer903(1'b0),.reader903(1'b0),.ready903(1'b0),.snap903(1'b0),
  .kind903(1'b0),.token903(32'd0),.pawr_n(1'b1),.port_id(8'd0),.tr_head(1'b0),
  .tr_section(1'b0),.tr_retired(1'b0),.tr_data(8'd0),.tr_op(8'd0),.tr_gen(16'd0),
  .address(addr),.read_n(1'b1),.write_n(wr),.romsel_n(1'b1),.data_in(din),.bus_drive(1'b0),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.receive_write(receive_write),
  .selected(selected),.miso(miso),.menu_status(status));
 task automatic submit(input byte request);
  addr=24'h007002;din=request;#84;wr=0;#96;
  if(!receive_write)$fatal(1,"SNES write not owned");
  wr=1;#96;addr=0;
 endtask
 task automatic xfer(input byte tx,output byte rx);
  for(int b=7;b>=0;b--)begin
   mosi=tx[b];#96;rx[b]=miso;sck=1;#96;sck=0;
  end
 endtask
 task automatic packet(input byte expected,input byte echo_n,input byte result,input int length);
  byte rx;
  ss=0;#84;
  xfer(8'h7a,rx);
  xfer(expected,rx);if(rx!==8'h10)$fatal(1,"request %h",rx);
  xfer(echo_n,rx);if(rx!==8'hef)$fatal(1,"request complement %h",rx);
  if(length>3)xfer(result,rx);
  if(length>4)xfer(~result,rx);
  if(length>5)xfer(0,rx);
  ss=1;#120;if(selected)$fatal(1,"SPI not released");
 endtask
 initial begin
  #100;reset=0;#120;submit(8'h10);submit(8'h20);
  if(status!==8'h80)$fatal(1,"request not held");
  packet(0,0,0,3);packet(8'h11,8'hee,1,5);packet(8'h10,0,1,5);
  packet(8'h10,8'hef,1,4);packet(8'h10,8'hef,1,6);
  if(status!==8'h80)$fatal(1,"incomplete or stale reply retired request");
  packet(8'h10,8'hef,1,5);if(status!==1)$fatal(1,"valid success lost");
  submit(8'h10);packet(8'h10,8'hef,2,5);if(status!==2)$fatal(1,"empty slot lost");
  submit(8'h10);cancel=1;#60;cancel=0;#60;
  if(status!==0 || dut.menu_request!==0)$fatal(1,"pending command survived STOP");
  $display("PASS FF3 menu SNES write, SPI query/echo, pending ownership, length, error and STOP");
  $finish;
 end
endmodule
