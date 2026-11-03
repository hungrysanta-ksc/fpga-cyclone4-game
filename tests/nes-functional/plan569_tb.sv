// SPDX-License-Identifier: MIT
`timescale 1ps/1ps
module plan569_tb;
 reg host_clk=0,nes_clk=0,host_on=1,nes_on=1,reset=0,stop=0;
 always #5952 if(host_on)host_clk=!host_clk;
 initial begin if($test$plusargs("SHIFT"))#11000;forever #23281 if(nes_on)nes_clk=!nes_clk;end
 reg write_valid=0,seal=0,plan_ready=0,tile_done=0,retire=0,end_ready=0,lease_valid=1;
 reg [7:0] write_data=0;
 reg [9:0] seal_length=0; reg [4:0] seal_plans=0; reg [15:0] seal_crc=0;
 wire write_ready,retire_done,retire_commit,host_idle,fault,plan_valid,end_valid;
 wire [9:0] plan_slot;wire [12:0] plan_tag;wire [103:0] plan_alt_tags;
 wire [7:0] plan_alt_mask,plan_mask;wire [1:0] plan_kind;
 wire [15:0] plan_generation,end_generation;wire [47:0] plan_rows;
 nes_plan_batch206 dut(.active(1'b1),.source_fault(1'b0),.retire_permitted(1'b1),.lease_generation(16'd954),.*);
 bit guard_pending=0;
 integer cycle_h=0,cycle_n=0,retired=0,committed=0,run_id=0;
 always @(posedge host_clk)begin
  cycle_h++;
  if(guard_pending&&(write_ready||!dut.pending||dut.control.held!=={1'b0,10'd512,5'd16}))
   $fatal(1,"early bank reservation release");
  if(dut.pending&&dut.box_ready&&!dut.hc)
   $display("EV %0d SEND %0t %0d %0d %0d",run_id,$time,dut.writer,dut.count,dut.plans);
  if(retire_done)retired++;
 end
 always @(posedge nes_clk)begin
  cycle_n++;
  if(guard_pending&&dut.state==dut.CHECK&&dut.remaining==1)guard_pending=0;
  if(dut.word_valid&&dut.state==dut.WAIT&&!dut.nc)
   $display("EV %0d WAIT %0t %h",run_id,$time,dut.word);
  if(dut.control.capture&&!dut.nc)$display("EV %0d CAP %0t",run_id,$time);
  if(dut.word_valid&&dut.word_ready)$display("EV %0d ACK %0t",run_id,$time);
  if(plan_valid&&plan_ready)$display("EV %0d PLAN %0t %d %d %d",run_id,$time,plan_slot,plan_tag,plan_generation);
  if(retire_commit)committed++;
 end
 function automatic [15:0] crc(input [15:0] prior,input [7:0] b);
  reg [15:0] c;c=prior^{b,8'd0};for(int i=0;i<8;i++)c=c[15]?(c<<1)^16'h1021:c<<1;return c;
 endfunction
 function automatic [7:0] octet(input int n,i);
  int row,pos;
  if(n==512)begin
   row=i/32;pos=i%32;
   case(pos)
    0:return 0;1:return 255;2:return 8'hba;3:return 3;4:return row+1;
    6:return row+19;8:return 255;15:return 1;
    default:return (pos>=16&&pos%2==0)?(row+pos):0;
   endcase
  end
  case(i)
   0:return n==3?8'h83:8'h80;1:return 8'hba;2:return 3;3:return 89;5:return 71;default:return 0;
  endcase
 endfunction
 task send_batch(input integer n, input bit bad_crc=0,input integer expected_plans=0);
  reg [15:0] c;c=16'hffff;
  for(int i=0;i<n;i++)begin
   @(negedge host_clk);if(!write_ready)$fatal(1,"write without storage credit");
   write_valid=1;write_data=octet(n,i);c=crc(c,write_data);
  end
  @(negedge host_clk);write_valid=0;seal=1;seal_length=n;seal_plans=expected_plans?expected_plans:(n==512?16:1);seal_crc=c^bad_crc;
  @(negedge host_clk);seal=0;
 endtask
 task consume_plan(input integer slot,tag,input bit full);
  wait(plan_valid);@(negedge nes_clk);
  if(plan_slot!==slot||plan_tag!==tag||plan_generation!==954||plan_kind!==0||
     plan_mask!==255||plan_alt_mask!==(full?255:0))$fatal(1,"wrong visible plan");
  if(full)for(int i=0;i<8;i++)if(plan_alt_tags[i*13+:13]!==slot-1+16+i*2)$fatal(1,"alt payload");
  plan_ready=1;@(negedge nes_clk);plan_ready=0;
  if(dut.state!=dut.RUN)$fatal(1,"lost owner");
  tile_done=1;@(negedge nes_clk);tile_done=0;
 endtask
 task flush(input integer paused);
  host_on=!(paused&1);nes_on=!(paused&2);#1400;stop=1;#100;
  if(write_ready||plan_valid||end_valid||dut.word_valid||retire_commit)$fatal(1,"STOP leak");
  #900;stop=0;#245000;
  if(paused==3&&(write_ready||plan_valid||end_valid))$fatal(1,"rearmed without clocks");
  host_on=1;nes_on=1;wait(host_idle);repeat(8)@(negedge nes_clk);
  if(dut.word_valid||dut.pending||plan_valid||end_valid||fault||dut.writer!=0||dut.state!=dut.WAIT)$fatal(1,"old owner after STOP");
  run_id++;
 endtask
 initial begin
  #2000;reset=1;#80000;reset=0;wait(host_idle);
  // Fill bank 0 completely; hold the first decoded plan while bank 1 seals.
  send_batch(512);wait(plan_valid);send_batch(7);
  if(write_ready||!dut.pending||dut.control.held!=={1'b0,10'd512,5'd16})$fatal(1,"bank reservation");
  guard_pending=1;repeat(40)@(negedge nes_clk);
  for(int i=1;i<16;i++)consume_plan(i,i+18,1);
  wait(plan_valid);wait(write_ready);
  // The last CHECK released bank 0 before tile_done; all decoded fields stay owned.
  if(plan_slot!=16||dut.writer!=0)$fatal(1,"early return boundary");
  send_batch(3);wait(dut.word_valid);
  if(dut.state!=dut.READY||dut.control.held!=={1'b1,10'd7,5'd1}||write_ready)$fatal(1,"next word overwritten");
  consume_plan(16,34,1);consume_plan(89,71,0);wait(end_valid);
  if(end_generation!=954||fault)$fatal(1,"bad END");
  @(negedge nes_clk);end_ready=1;@(negedge nes_clk);end_ready=0;
  wait(host_idle);@(negedge host_clk);retire=1;@(negedge host_clk);retire=0;
  wait(retired==1);if(committed!=1||fault)$fatal(1,"bad retire");
  // Abort at the handoff, before decoder capture, at the final CHECK and
  // after ACK with a delayed plan still live. A fresh bank 0 must work each time.
  run_id=1;
  for(int stage=0;stage<4;stage++)begin
   for(int paused=0;paused<4;paused++)begin
    send_batch(7);
    case(stage)
     0:wait(dut.control.request!=dut.control.acknowledge);
     1:wait(dut.word_valid&&dut.state==dut.WAIT);
     2:wait(dut.word_ready);
     3:wait(plan_valid);
    endcase
    flush(paused);
    send_batch(7);consume_plan(89,71,0);wait(host_idle);
   end
  end
  send_batch(7,1);wait(fault);if(plan_valid)$fatal(1,"bad CRC exposed");
  flush(3);
  send_batch(7,0,2);wait(fault);if(plan_valid||dut.word_ready)$fatal(1,"invalid length ACK");
  flush(3);
  send_batch(7);wait(dut.word_valid);lease_valid=0;wait(fault);
  if(plan_valid||dut.word_ready)$fatal(1,"wrong lease ACK");
  lease_valid=1;flush(3);send_batch(7);consume_plan(89,71,0);
  if(committed!=1||retired!=1||fault)$fatal(1,"late or duplicate retirement");
  $display("PASS569 STOP=16 faults=3 reuse=1 retire=1");$finish;
 end
 initial begin #200000000;$fatal(1,"timeout run=%0d state=%0d",run_id,dut.state);end
endmodule
