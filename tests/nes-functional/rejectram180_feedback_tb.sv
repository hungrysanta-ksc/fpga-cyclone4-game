// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module rejectram180_feedback_tb;
 reg clk=0,reset=1,active=0,freeze=0,sample_enable=0;
 always #5 clk=~clk;
 reg [95:0] sample=0;reg [7:0] command=8'h77;
 wire [55:0] page;wire feedback_ready180;wire [24:0] feedback_errors180;
 nes_ppu_history157 ring(.*);
 task emit(input [24:0] errors);
  sample={2'd1,8'h5a,errors,61'h12345678};sample_enable=1;
  @(negedge clk);
  if(feedback_ready180)$fatal(1,"write-edge output still stale must be invalid");
 endtask
 initial begin
  repeat(3)@(negedge clk);reset=0;active=1;
  @(negedge clk);if(feedback_ready180)$fatal(1,"empty RAM feedback exposed");
  // Consecutive writes exercise old-data/read-address hazards beyond any
  // actual native-frame cadence. No available feedback may suppress an event.
  for(integer k=0;k<20;k++)emit(25'h1800000+k);
  sample_enable=0;@(negedge clk);
  if(!feedback_ready180 || feedback_errors180!==25'h1800013)$fatal(1,"last committed feedback %h",feedback_errors180);
  // While RUN owns the read port, SPI command selection must not change it.
  for(integer k=0;k<32;k++)begin
   command=8'ha0+k;@(negedge clk);
   if(!feedback_ready180 || feedback_errors180!==25'h1800013)$fatal(1,"RUN index disturbed");
  end
  active=0;command=8'ha6;repeat(2)@(negedge clk);
  if(feedback_ready180 || page!=={8'he5,2'd1,8'h5a,25'h1800013,13'd0})$fatal(1,"STOP read slot3 %h",page);
  // STOP remains frozen when active is erroneously raised again.
  active=1;emit(25'h1ffffff);sample_enable=0;@(negedge clk);
  if(feedback_ready180)$fatal(1,"frozen RAM feedback exposed");
  command=8'ha6;repeat(2)@(negedge clk);
  if(page!=={8'he5,2'd1,8'h5a,25'h1800013,13'd0})$fatal(1,"STOP mutated");
  reset=1;@(negedge clk);reset=0;active=1;command=8'h77;freeze=1;
  sample={2'd1,8'h5a,25'h1234567,61'd0};sample_enable=1;@(negedge clk);
  freeze=0;sample_enable=0;command=8'ha0;repeat(2)@(negedge clk);
  if(feedback_ready180 || page!=={8'he5,2'd1,8'h5a,25'h1234567,13'd0})$fatal(1,"fault edge retention");
  $display("PASS RAM180 feedback consecutive20,settled-value,RUN32indices,STOP,fault,reset");$finish;
 end
 initial begin #100000;$fatal(1,"watchdog");end
endmodule
