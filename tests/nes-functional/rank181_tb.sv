// SPDX-License-Identifier: MIT
// Exact-output comparison, including RAM results, on complete compact scenes.
module rank181_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,release_scene=0,begin_scene=0,end_scene=0,source_fault=0;
 reg event_valid=0,row_commit=0,row_patched=0,query=0;
 reg [63:0] event_data=0;reg [7:0] committed_row=0;
 reg [1:0] query_kind=0;reg [10:0] query_address=0;
 wire [7:0] errors,row_count,object_count,exception_count;
 wire [5:0] group_count;wire active,owned,valid,response,hit,row_needs_patch;
 wire [63:0] data;
 nes_native_compact181 dut(.*);
 wire [7:0] r_errors,r_row_count,r_object_count,r_exception_count;
 wire [5:0] r_group_count;wire r_active,r_owned,r_valid,r_response,r_hit,r_row_needs_patch;
 wire [63:0] r_data;
 compact181_original reference_compact(
 .clk(clk),.reset(reset),.release_scene(release_scene),.begin_scene(begin_scene),
 .end_scene(end_scene),.source_fault(source_fault),.event_valid(event_valid),.event_data(event_data),
 .row_commit(row_commit),.row_patched(row_patched),.committed_row(committed_row),
 .query(query),.query_kind(query_kind),.query_address(query_address),
 .errors(r_errors),.row_count(r_row_count),.object_count(r_object_count),.exception_count(r_exception_count),
 .group_count(r_group_count),.active(r_active),.owned(r_owned),.valid(r_valid),
 .response(r_response),.hit(r_hit),.row_needs_patch(r_row_needs_patch),.data(r_data));
 integer cycles=0,same_count=0,new_count=0,scenes=0,reads=0;
 always @(posedge clk)begin
  if(dut.accept && dut.obj && !reset && !release_scene)begin
   if(dut.same_object)same_count=same_count+1;else new_count=new_count+1;
  end
  #2;
  if({errors,row_count,object_count,exception_count,group_count,active,owned,valid,response,hit,row_needs_patch,data}
     !=={r_errors,r_row_count,r_object_count,r_exception_count,r_group_count,r_active,r_owned,r_valid,r_response,r_hit,r_row_needs_patch,r_data})
     $fatal(1,"rank differential cycle=%0d",cycles);
  cycles=cycles+1;
  if(hit)reads=reads+1;
 end
 task step;begin @(negedge clk);end endtask
 task sprite(input integer row,input integer rank,input integer tile,input integer attr,input integer fine);
 begin
  event_data=0;event_data[49]=1;event_data[52:50]=rank;
  event_data[32:25]=row;event_data[40:33]=rank*16;
  event_data[48:41]=attr;event_data[15:13]=fine;event_data[12:0]=tile;
  event_valid=1;step();event_valid=0;
 end endtask
 integer s,y,k,i;reg [31:0] rng=32'h4518ab93;
 initial begin
  step();step();reset=0;step();
  // Stable, changed keys, flipped fine, duplicate rows, capacity exhaustion,
  // source fault, and release. No extra event bubble between rank accesses.
  for(s=0;s<8;s=s+1)begin
   release_scene=1;step();release_scene=0;begin_scene=1;step();begin_scene=0;
   for(y=0;y<224;y=y+1)begin
    if(y<96 || s==4)begin
     for(k=0;k<8;k=k+1)begin
      sprite(y,k,(s==1 ? (y/8)*8+k : k),s==2?128:0,s==2?7-(y%8):y%8);
      if(s==3 && y==7)sprite(y,k,k,0,y%8);
     end
    end
    if(s==5 && y==40)begin source_fault=1;step();source_fault=0;end
    if(s==6 && y==40)begin release_scene=1;step();release_scene=0;end
    row_patched=1;row_commit=1;committed_row=y;step();row_commit=0;
   end
   end_scene=1;step();end_scene=0;step();step();
   if(s==0 || s==1 || s==2 || s==7)begin
    if(!valid || errors!=0)$fatal(1,"expected valid scene %0d err=%h",s,errors);
    for(i=0;i<128;i=i+1)begin query=1;query_kind=2;query_address=i;step();end
   end
   query=0;step();scenes=scenes+1;
  end
  // Arbitrary controls stress reset/begin/release/fault priority and malformed
  // events; deterministic LFSR, no hierarchy writes or forced hidden state.
  for(i=0;i<100000;i=i+1)begin
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   reset=(i%997==0);release_scene=(i%251==0);begin_scene=(i%31==0);
   end_scene=(i%499==0);source_fault=(i%503==0);query=rng[2];
   query_kind=rng[4:3];query_address=rng[15:5];row_commit=(i%43==0);
   row_patched=rng[7];committed_row=rng[23:16];event_valid=rng[1];
   event_data={rng,rng^32'h18275a39};step();
  end
  if(same_count<100 || new_count<100 || reads<100)$fatal(1,"insufficient exercise");
  $display("PASS RANK181 cycles=%0d scenes=%0d same=%0d new=%0d reads=%0d",cycles,scenes,same_count,new_count,reads);
  $finish;
 end
endmodule
