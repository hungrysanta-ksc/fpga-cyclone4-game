// SPDX-License-Identifier: MIT
// CHECK disabled: compare every exposed RUN signal to frozen052.
`timescale 1ns/1ps
module rom_readback_diff;
 reg clk=0,mem_clk=0,reset=1,rom_request=0;
 reg [21:0] rom_address=0;
 always #23.280423 clk=~clk;
 always #5.952381 mem_clk=~mem_clk;
 wire [1:0] ready,response,error,ce1,ce2,oe,we,bhe,ble;
 wire [21:0] address[2],tag[2];wire [7:0] data[2];wire [15:0] pins[2];
 function automatic [7:0] value(input [21:0] a);
  value=a[7:0]^a[15:8]^a[21:16]^8'hc7;
 endfunction
 for(genvar n=0;n<2;n++)begin: model
  wire [21:0] a={address[n][19:0],ce1[n],1'b0};
  assign #25 pins[n]=!oe[n] && (!ce1[n]^!ce2[n]) ? {value(a),value(a+22'd1)}:16'hzzzz;
 end
 nes_rom_physical_reference reference(.clk(clk),.mem_clk(mem_clk),.reset(reset),
 .rom_request(rom_request),.rom_address(rom_address),.rom_ready(ready[0]),.rom_response(response[0]),
 .rom_error(error[0]),.rom_response_address(tag[0]),.rom_data(data[0]),.psram_address(address[0]),
 .psram_1ce(ce1[0]),.psram_2ce(ce2[0]),.psram_oe(oe[0]),.psram_we(we[0]),.psram_bhe(bhe[0]),.psram_ble(ble[0]),.psram_data(pins[0]));
 nes_rom_physical candidate(.clk(clk),.mem_clk(mem_clk),.reset(reset),
 .check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),
 .check_ready(),.check_response(),.check_response_address(),.check_data(),
 .rom_request(rom_request),.rom_address(rom_address),.rom_ready(ready[1]),.rom_response(response[1]),
 .rom_error(error[1]),.rom_response_address(tag[1]),.rom_data(data[1]),.psram_address(address[1]),
 .psram_1ce(ce1[1]),.psram_2ce(ce2[1]),.psram_oe(oe[1]),.psram_we(we[1]),.psram_bhe(bhe[1]),.psram_ble(ble[1]),.psram_data(pins[1]));
 integer comparisons=0,requests=0,replies=0,cancels=0;
 always @(posedge clk or negedge clk or posedge mem_clk or negedge mem_clk)begin
  #0.001;
  if($time>1)begin
   comparisons++;
   if({ready[0],response[0],error[0],tag[0],data[0],address[0],ce1[0],ce2[0],oe[0],we[0],bhe[0],ble[0]} !==
      {ready[1],response[1],error[1],tag[1],data[1],address[1],ce1[1],ce2[1],oe[1],we[1],bhe[1],ble[1]})
    $fatal(1,"RUN differential mismatch");
  end
 end
 always @(posedge clk)if(!reset&&response[1])replies++;
 initial begin
  repeat(4)@(negedge clk);reset=0;repeat(4)@(negedge clk);
  for(integer i=0;i<4096;i++)begin
   while(!ready[0])@(negedge clk);
   rom_address=(i*7919)^(i<<13);rom_request=1;requests++;
   @(negedge clk);rom_request=0;
   if(i%97==0)begin #2;reset=1;#37;reset=0;cancels++;repeat(4)@(negedge clk);end
   else if(i%3==0)@(negedge clk);
  end
  wait(ready[0]);repeat(5)@(negedge clk);
  if(replies+cancels!=requests)$fatal(1,"RUN differential accounting");
  $display("PASS READBACK RUN DIFF comparisons=%0d requests=%0d replies=%0d cancellations=%0d",comparisons,requests,replies,cancels);
  $finish;
 end
 initial begin #10000000;$fatal(1,"RUN differential watchdog");end
endmodule
