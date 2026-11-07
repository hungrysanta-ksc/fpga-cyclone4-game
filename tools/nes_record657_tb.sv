// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module bench;
 reg clk=0,reset=1,owned=0,geometry=1,enable=1,response=0,hit=1;
 always #5 clk=~clk;
 reg [15:0] generation=1,lfsr=16'hbeef;
 reg [63:0] value=0;
 reg [2:0] patches;
 reg [5:0] groups,palettes;
 reg [7:0] objects,exceptions;
 wire ready=lfsr[3:2]!=0;
 wire [1:0] q,release_frame,valid,busy,ack_ready;
 wire [2:0] kind[2];
 wire [12:0] idx[2];wire [15:0] qgen[2];
 wire [95:0] word_data[2];wire [3:0] state[2],fault[2];
 integer scenario=0,complete=0,aborted=0;
`define PORTS(i) .clk(clk),.reset(reset),.enable(enable),.start_permitted(1'b1),.discard_permitted(1'b1), \
 .frame_owned(owned),.geometry_valid(geometry),.frame_generation(generation),.patch_count(patches), \
 .row_count(8'd224),.group_count(groups),.object_count(objects),.exception_count(exceptions),.palette_count(palettes), \
 .release_frame(release_frame[i]),.query(q[i]),.query_kind(kind[i]),.query_index(idx[i]),.query_generation(qgen[i]), \
 .response(response),.hit(hit),.data(value),.tx_valid(valid[i]),.tx_ready(ready),.tx_data(word_data[i]), \
 .ack_valid(state[0]==8),.ack_accept(1'b1),.ack_generation(generation),.ack_ready(ack_ready[i]), \
 .observe_state177(state[i]),.busy(busy[i]),.error(fault[i])
 reference old(`PORTS(0));
 candidate dut(`PORTS(1));
 always @(posedge clk) begin
  lfsr<={lfsr[14:0],lfsr[15]^lfsr[13]^lfsr[12]^lfsr[10]};
  response<=q[0];hit<=!(scenario==4 && kind[0]==3 && idx[0]==17);
  if(q[0])case(kind[0])
   0:value<=idx[0]*7;
   1:value<=idx[0]&255;
   5:value<=idx[0]&63;
   7:value<=idx[0]<270?6'h2d:idx[0]<615?(idx[0]>>3)&63:idx[0]&63;
   default:value<={4{3'h0,idx[0]}};
  endcase
  if(!reset)begin
   if({q[0],kind[0],idx[0],qgen[0],state[0],fault[0],ack_ready[0],release_frame[0],valid[0],busy[0]}
    !=={q[1],kind[1],idx[1],qgen[1],state[1],fault[1],ack_ready[1],release_frame[1],valid[1],busy[1]})
    $fatal(1,"source control mismatch");
   if(valid[0] && (word_data[0]!==word_data[1] || $isunknown(word_data[1])))$fatal(1,"record mismatch");
   if(valid[0] && ready && word_data[0][95:93]==7)case(word_data[0][76:64])
    1:begin
     if(word_data[1][31:16]!==groups*33+224+objects+exceptions+224+palettes*32+patches*256 ||
        word_data[1][15:0]!==patches*256)$fatal(1,"END totals");
     complete<=complete+1;
    end
    2:aborted<=aborted+1;
   endcase
  end
 end
 initial begin
  repeat(3)@(negedge clk);reset=0;
  for(scenario=0;scenario<6;scenario++)begin
   @(negedge clk);generation=16'hfffB+scenario;owned=1;
   patches=scenario==0?0:scenario==1?1:7;groups=scenario==0?1:32;
   palettes=scenario==0?1:2;objects=scenario==0?0:128;exceptions=objects;
   if(scenario==5)begin wait(q[0] && idx[0]==16);@(negedge clk);enable=0;end
   wait(release_frame[0]);@(negedge clk);owned=0;enable=1;
   wait(state[0]==0);@(negedge clk);
  end
  if(complete!=4 || aborted!=2)$fatal(1,"missing END/ABORT");
  $display("PASS657 limits, 4 ENDs, 2 ABORTs");$finish;
 end
 initial begin repeat(300000)@(posedge clk);$fatal(1,"timeout");end
endmodule
