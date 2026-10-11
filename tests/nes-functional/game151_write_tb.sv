`timescale 1ns/1ps
module game151_write_tb;
 reg clk=0,reset=1,active=1;always #5.952 clk=~clk;
 reg [23:0] address=0;reg rd=1,wr=1;reg [7:0] din=0;
 wire release_new,release_old,commit_new;wire [15:0] buttons;
 integer new_releases=0,old_releases=0,commits=0,checks=0,negatives=0;
 nes_game_bus151 dut(.host_clk(clk),.reset(reset),.active(active),.address(address),
 .read_n(rd),.write_n(wr),.romsel_n(1'b1),.data_in(din),.data_out(),.oe_n(),.dir(),
 .frame_ready(1'b1),.frame_response(1'b0),.frame_data(8'd0),.frame_request(),.frame_address(),
 .release_frame(release_new),.pad_commit(commit_new),.pad_buttons(buttons));
 nes_game_bus150 old(.host_clk(clk),.reset(reset),.active(active),.address(address),
 .read_n(rd),.write_n(wr),.romsel_n(1'b1),.data_in(din),.data_out(),.oe_n(),.dir(),
 .frame_ready(1'b1),.frame_response(1'b0),.frame_data(8'd0),.frame_request(),.frame_address(),
 .release_frame(release_old),.pad_commit(),.pad_buttons());
 nes_screen_status151 status(.clk(clk),.reset(reset),.active(active),.address(address),
 .read_n(rd),.write_n(wr),.romsel_n(1'b1),.data_in(din),.SPI_SS(1'b1),.SPI_SCK(1'b0),.SPI_MOSI(1'b0),
 .receive_write(),.selected(),.miso());
 nes_screen_status142 oldstatus(.clk(clk),.reset(reset),.active(active),.address(address),
 .read_n(rd),.write_n(wr),.romsel_n(1'b1),.data_in(din),.SPI_SS(1'b1),.SPI_SCK(1'b0),.SPI_MOSI(1'b0),
 .receive_write(),.selected(),.miso());
 always @(negedge clk)begin
  if(release_new)new_releases=new_releases+1;
  if(release_old)old_releases=old_releases+1;
  if(commit_new)commits=commits+1;
 end
 task write_byte(input [23:0] a,input [7:0] early,input [7:0] value,input integer late);
  address=a;din=early;rd=1;wr=0;
  #(late);din=value;#(300-late);
  wr=1;din=8'hee;address=24'h123456;#180;
 endtask
 integer n,o,c,f;
 initial begin
  #100;reset=0;#200;
  for(integer phase=0;phase<3;phase=phase+1)begin
   #(phase*3.5);
   for(integer late=0;late<=160;late=late+80)begin
    n=new_releases;o=old_releases;
    write_byte(24'h006000,8'h60,8'ha5,late);
    if(new_releases!=n+1)$fatal(1,"late release lost %0d",late);
    if(late>0)begin if(old_releases!=o)$fatal(1,"old missed-release negative absent");negatives++;end
    n=new_releases;o=old_releases;
    write_byte(24'h006000,8'ha5,8'h55,late);
    if(new_releases!=n)$fatal(1,"early false release");
    if(late>0)begin if(old_releases!=o+1)$fatal(1,"old false-release negative absent");negatives++;end
    c=commits;write_byte(24'h006002,8'h60,8'h80,late);write_byte(24'h006003,8'h60,8'h10,late);
    if(buttons!==16'h1080 || commits!=c+1)$fatal(1,"late pad capture");
    f=status.frames;write_byte(24'h007000,8'h70,8'd6,late);
    if(status.stage!==6 || status.frames!=f+1)$fatal(1,"late stage capture");
    if(late>0)begin if(oldstatus.stage!==8'h70)$fatal(1,"old stage70 negative absent");negatives++;end
    checks+=4;
   end
  end
  // Reset cancels an in-flight write; inactive/foreign writes cannot release.
  n=new_releases;address=24'h006000;din=8'ha5;wr=0;#120;reset=1;#180;wr=1;#100;reset=0;#150;
  if(new_releases!=n)$fatal(1,"reset write committed");
  active=0;write_byte(24'h006000,8'h60,8'ha5,80);active=1;
  write_byte(24'h016000,8'h60,8'ha5,80);
  if(new_releases!=n)$fatal(1,"inactive/foreign release");
  $display("PASS GAME151 write checks=%0d causal_negatives=%0d phases3 delays0/80/160ns immediate_end_garbage reset/inactive/foreign",checks,negatives);$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
