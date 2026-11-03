// SPDX-License-Identifier: MIT
// The runner appends the six pin mux assignments verbatim from the fitted board.
wire core_reset=reset;
wire sink_oe204,sink_dir204,status_receive;
wire [7:0] sink_data204,consumer_data;
wire bus_oe_n=dut.oe_n,bus_dir=dut.dir;
wire [7:0] bus_data=dut.data_out;
wire consumer_dir,consumer_oe,SNES_DATABUS_DIR,SNES_DATABUS_OE;
tri [7:0] SNES_DATA;
assign SNES_DATA=cpu_drives&&!wr_n&&!SNES_DATABUS_DIR&&!SNES_DATABUS_OE?wdata:8'hzz;
nes_sink_bridge165 sink571(.clk(host_clk),.raw_reset(reset),.active(!reset),.stop(1'b0),
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.address(bus),.read_n(rd_n),.write_n(wr_n),.romsel_n(1'b1),
 .data_in(SNES_DATA),.data_out(sink_data204),.oe_n(sink_oe204),.dir(sink_dir204));
nes_screen_status151 status571(.clk(host_clk),.reset(reset),.active(!reset),
 .address(bus),.read_n(rd_n),.write_n(wr_n),.romsel_n(1'b1),.data_in(SNES_DATA),
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.bus_drive(consumer_dir&&!consumer_oe),.receive_write(status_receive));
integer comparisons571=0;
task sample571(input bit oe,dir571,input logic [7:0] data);
 #2;if({SNES_DATABUS_OE,SNES_DATABUS_DIR,SNES_DATA}!=={oe,dir571,data})
  $fatal(1,"bus adr=%h got %b %b %h expected %b %b %h",bus,SNES_DATABUS_OE,SNES_DATABUS_DIR,SNES_DATA,oe,dir571,data);
 comparisons571++;
endtask
task read571(input [23:0] adr,input [7:0] data);
 bus=adr;rd_n=0;wr_n=1;repeat(7)@(negedge host_clk);sample571(0,1,data);
endtask
task test571;
 for(int k=0;k<3;k++)begin
  restart();memory_open=1;
  $readmemh("fresh.hex",raw,0,17);data_frame(0,18);wait(dut.chunk_ready);
  read571(24'h6040,1);read571(24'h6000,0);read571(24'h400800,8'h63);
  // A change of aperture address releases the old data until its new tag matches.
  bus=24'h400801;sample571(1,0,8'hzz);read571(24'h400801,8'h63);
  host_on=0;nes_on=0;rd_n=1;sample571(1,0,8'hzz);
  rd_n=0;sample571(0,1,8'h63);bus=24'h400810;sample571(1,0,8'hzz);
  bus=24'h6040;sample571(0,1,1);rd_n=1;wr_n=0;sample571(0,0,8'hzz);
  wdata=8'hbe;cpu_drives=1;sample571(0,0,8'hbe);bus=24'h7000;sample571(0,0,8'hbe);
  bus=24'h7002;sample571(1,0,8'hzz);cpu_drives=0;wr_n=1;
  // Check the guard with an aperture read actually driving all eight pins.
  bus=24'h400801;rd_n=0;sample571(0,1,8'h63);
  if(k==0)core_fault=1;
  if(k==1)reset=1;
  if(k==2)force dut.bulk.host_failed=1; // local latch before the direct fault feedback
  sample571(1,0,8'hzz);
  if(dut.chunk_ready||dut.consume)$fatal(1,"fault leaked owner");
  #250000;sample571(1,0,8'hzz);
  if(k==2)release dut.bulk.host_failed;
  rd_n=1;reset=1;#100;core_fault=0;host_on=1;nes_on=1;
 end
 restart();sample571(1,0,8'hzz);
 $display("PASS571 pin_samples=%0d",comparisons571);$finish;
endtask
