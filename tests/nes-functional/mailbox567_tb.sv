// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module mailbox567_pair #(parameter WIDTH=96, SRC_HALF=23281, DST_HALF=5952)(output reg finished=0);
 reg sc=0,dc=0,run_s=1,run_d=1,reset=0,send=0,take=0;
 reg [WIDTH-1:0] data=0,expected=0;
 wire old_ready,new_ready,old_valid,new_valid;
 wire [WIDTH-1:0] old_data,new_data;
 mailbox565 #(.WIDTH(WIDTH)) refbox(sc,dc,reset,send,old_ready,data,old_valid,take,old_data);
 nes_native_mailbox165 #(.WIDTH(WIDTH)) dut(sc,dc,reset,send,new_ready,data,new_valid,take,new_data);
 always #SRC_HALF if(run_s)sc=!sc;
 initial begin if($test$plusargs("SHIFT"))#3100;forever #DST_HALF if(run_d)dc=!dc; end

 integer accepted=0,delivered=0,aborted=0,checks=0;
 bit pending=0;
 task compare_ports;
  if({old_ready,old_valid,old_data}!=={new_ready,new_valid,new_data})$fatal(1,"port difference");
  checks++;
 endtask
 always @(posedge sc)begin
  if(!reset&&send&&new_ready)begin
   if(pending)$fatal(1,"overwrite");
   expected=data;pending=1;accepted++;
  end
  #1;compare_ports();
 end
 always @(posedge dc)begin
  if(!reset&&new_valid)begin
   if(!pending||expected!==new_data)$fatal(1,"stale or corrupt word");
   if(take)begin pending=0;delivered++;end
  end
  #1;compare_ports();
 end
 task put(input integer id);
  wait(new_ready);@(negedge sc);data={32'hc4a7630b*id,32'h5e113a7f*id,32'hde171ceb*id};send=1;
  @(negedge sc);send=0;
 endtask
 task receive_word;
  wait(new_valid);@(negedge dc);take=1;@(negedge dc);take=0;wait(new_ready);
 endtask
 task cancel(input integer stopped);
  if(pending)aborted++;
  pending=0;

  // Freeze either or both clocks through release. With either clock absent,
  // the peer cannot re-establish both up indications.
  if(stopped&1)run_s=0;
  if(stopped&2)run_d=0;
  // Assert with the selected clocks already paused, including a pulse
  // shorter than the faster clock period. The release still needs both peers.
  #1;reset=1;#2;compare_ports();
  if(new_ready||new_valid)$fatal(1,"asynchronous mask");
  #801;reset=0;#250000;
  if(new_valid||(stopped&&new_ready))$fatal(1,"premature rearm");
  run_s=1;run_d=1;wait(new_ready);
 endtask
 initial begin
  #2900;cancel(3);
  for(int i=1;i<=80;i++)begin
   put(i);
   case(i%5)
    0:begin wait(new_valid);repeat(12)@(negedge dc);receive_word();end
    1:begin wait(new_valid);#717;cancel(i%4);end
    2:begin wait(dut.capture);#251;cancel(i%4);end
    3:begin wait(new_valid);@(negedge dc);take=1;#153;cancel(i%4);take=0;end
    4:begin wait(new_valid);@(negedge dc);take=1;@(posedge dc);#700;take=0;cancel(i%4);end
   endcase
  end
  put(81);receive_word();
  if(accepted!=81||delivered!=33||aborted!=48||pending)$fatal(1,"accounting");
  $display("PASS567 width=%0d accepted=%0d delivered=%0d canceled=%0d checks=%0d",WIDTH,accepted,delivered,aborted,checks);
  finished=1;
 end
endmodule
module mailbox567_tb;
 wire records_done,prepared_done;
 mailbox567_pair records(records_done);
 mailbox567_pair #(.WIDTH(17),.SRC_HALF(5952),.DST_HALF(23281)) prepared(prepared_done);
 initial begin wait(records_done&&prepared_done);$finish;end
 initial begin #2000000000;$fatal(1,"deadlock");end
endmodule
