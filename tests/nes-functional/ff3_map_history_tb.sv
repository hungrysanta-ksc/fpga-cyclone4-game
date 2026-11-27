// Check visible outputs at the consuming clock edge against the original capture.
`timescale 1ns/1ps
module ff3_map_history_tb;
 reg [2:0] next_rank=0;
 reg clk=0;always #5 clk=!clk;
 reg reset=1,release_scene=0,begin_scene=0,end_scene=0,source_fault=0;
 reg event_valid=0,row_commit=0,row_patched=0,query=0;
 reg [7:0] committed_row=0;
 reg [1:0] query_kind=0; reg [10:0] query_address=0;
 reg [63:0] event_data=0;
 wire [107:0] expected,actual;
 `define OUTPUTS(v) .data(v[63:0]),.hit(v[64]),.response(v[65]),.row_needs_patch(v[66]),.active(v[67]),.owned(v[68]),.valid(v[69]),.errors(v[77:70]),.row_count(v[85:78]),.object_count(v[93:86]),.exception_count(v[101:94]),.group_count(v[107:102])
 nes_compact_reference original(`OUTPUTS(expected),.*);
 nes_native_compact181 changed(`OUTPUTS(actual),.*);
 integer reads=0;
 always @(negedge clk)begin
   if(actual[107:64]!==expected[107:64] || actual[63:0]!==expected[63:0])
     $fatal(1,"capture mismatch row %d query %d expected=%h actual=%h",committed_row,query_address,expected,actual);
   if(query && actual[64])reads++;
 end
 task automatic tick; @(posedge clk);#1;endtask
 task automatic restart;
   release_scene=1;tick();release_scene=0;begin_scene=1;tick();begin_scene=0;
 endtask
 initial begin
   tick();reset=0;restart();
   for(int y=0;y<224;y++)begin
     for(int x=0;x<33;x++)begin
       event_data=0;event_data[12:0]=x+(y>>3)*7; event_data[15:13]=y%8;
       event_data[32:25]=y;event_data[40:33]=x;event_data[42:41]=(x+y/8)%4;
       event_valid=1;tick();
       if(x%5==0)begin event_valid=0;tick();end
     end
     event_valid=0;next_rank=0;committed_row=y;row_patched=(y==39);row_commit=1;tick();
     row_commit=0;row_patched=0;
     for(int e=0;e<5 && y<16;e++)begin
       int rank;
       rank=(e<2)?0:e-1;
       event_valid=1;event_data=0;event_data[49]=1;event_data[52:50]=rank;next_rank=(e==0)?0:((rank+1)%4);
       event_data[12:0]=rank+12;event_data[32:25]=2*y+(e==1);event_data[15:13]=(2*y+(e==1))%8;tick();
     end
     event_valid=0;repeat(34)tick();
   end
   end_scene=1;tick();end_scene=0;tick();
   if(!actual[69])$fatal(1,"valid reference frame required %h",actual);
   query=1;
   for(int kind=0;kind<4;kind++)for(int i=0;i<1130;i++)begin
     query_kind=kind;query_address=i;tick();
   end
   query=0;tick();
   if(reads<1000)$fatal(1,"insufficient RAM query coverage");
   restart();event_data=0;event_valid=1;tick();event_valid=0;
   row_commit=1;committed_row=0;tick();row_commit=0;repeat(4)tick();restart();
   // Interleave all eight ranks, including a forwarded same-slot write.
   // Duplicate and descending rows must still be rejected after intervening
   // ranks evict the forwarding register or a new fragment changes slot.
   for(int descending=0;descending<2;descending++)begin
     restart();event_valid=0;next_rank=0;tick();
     for(int i=0;i<16;i++)begin
       event_data=0;event_data[49]=1;event_data[52:50]=i%8;
       event_data[32:25]=i<8?8:9;event_data[12:0]=i;
       next_rank=(i+1)%8;event_valid=1;tick();
     end
     event_data[52:50]=0;event_data[32:25]=descending?8:9;
     next_rank=0;tick();event_valid=0;
     if(!actual[74])$fatal(1,"rank row order guard missing");
   end
   $display("PASS FF3 capture row history, 224 rows, %0d valid readbacks, release during copy",reads);
   $finish;
 end
endmodule
