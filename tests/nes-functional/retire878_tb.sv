`timescale 1ns/1ps
module retire878_tb;
 reg clk=0,reset=1,stop=0,source_fault=0,idle=1,chunk=0,sealed=0,done=0;
 always #5.952 clk=~clk;
 `include "spi200_bus.svh"
 wire fault,retire;
 nes_plan_spi200 dut(.clk(clk),.reset(reset),.enable(1'b1),.stop(stop),
  .source_fault(source_fault),.SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),
  .selected(selected197),.miso(miso197),.fault(fault),.plan_idle(idle),.plan_ready(1'b1),
  .retire_done(done),.retire(retire),.end_generation(16'd950),.end_sealed(sealed),
  .chunk_ready(chunk),.chunk_kind(1'b0),.chunk_length(12'd0),.chunk_slot(10'd0),
  .chunk_generation(16'd0),.chunk_token(32'd0),.host_first(7'd0),.nes_first(8'd0));
 integer retires=0;
 always @(posedge clk) if(retire)retires<=retires+1;
 task send_ea(input integer testnum);
  reg [7:0] b[0:6];reg [7:0] crc,r;integer j;
  begin
   b[0]=8'hea;b[1]=(testnum==4)?8'hb7:8'hb6;b[2]=3;
   b[3]=0;b[4]=(testnum==5);crc=0;
   for(j=0;j<5;j=j+1)crc=crc8_197(crc,b[j]);
   b[5]=(testnum==6)?~crc:crc;b[6]=8'ha5;
   begin197();
   for(j=0;j<7;j=j+1)byte197(b[j],r);
   end197();
  end
 endtask
 integer i,prior;
 initial begin
  for(i=0;i<9;i=i+1)begin
   reset=1;source_fault=0;stop=0;idle=1;chunk=0;#150;reset=0;#180;
   @(negedge clk);sealed=1;@(negedge clk);sealed=0;
   status197();
   if(rx197[3]!=2||{rx197[4],rx197[5]}!=0)$fatal(1,"FINISH");
   prior=retires;
   case(i)
    1: source_fault=1;
    2: idle=0;
    3: chunk=1;
    7: stop=1;
    8: begin send_ea(0);prior=retires;end
   endcase
   send_ea(i);
   if(i==0)begin
    if(retires!=prior+1||fault)$fatal(1,"EA");
    status197();if(rx197[3]!=6)$fatal(1,"retiring");
    @(negedge clk);done=1;@(negedge clk);done=0;
    status197();if(rx197[3]!=1)$fatal(1,"rearm");
   end else begin
    if(retires!=prior||(!fault && i!=7))$fatal(1,"stale FINISH %d",i);
   end
  end
  $display("PASS retire878 9 conditions");$finish;
 end
endmodule
