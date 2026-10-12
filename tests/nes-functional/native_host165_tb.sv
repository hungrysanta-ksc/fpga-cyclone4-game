// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_host165_tb;
 parameter real HOST_PHASE=0.0;parameter integer MODE=0;
 reg clk=0,host_clk=0,host_clock_on=1,reset=1;
 always #23.280423 clk=~clk;
 initial begin #(HOST_PHASE);forever begin #5.9523809;if(host_clock_on)host_clk=~host_clk;end end
 reg frame_owned=0,geometry_valid=1;reg [15:0] generation=12;
 wire release_frame,query,response,hit,fill_start,fill_busy,fill_done,fill_success;
 wire [2:0] query_kind;wire [12:0] query_index;wire [15:0] query_generation;
 wire [63:0] data;wire byte_valid,byte_ready;wire [7:0] byte_data;
 wire [12:0] byte_tile;wire [3:0] byte_lane;wire [1:0] byte_kind;wire [15:0] byte_generation;
 wire tx_valid,tx_ready,ack_valid,ack_ready;wire [95:0] tx_data;wire [16:0] ack_data;
 reg host_ready=1,host_ack_valid=0;reg [16:0] host_ack_data=0;wire host_valid,host_ack_ready;wire [95:0] host_data;
 wire [3:0] error;wire busy;
 reg [63:0] table0[0:1055],table1[0:223],table2[0:127],table3[0:127],table4[0:223],table5[0:63],table6[0:8191];
 reg [7:0] chr[0:131071];integer groups,objects,exceptions,palettes,frame_no;
 string prefix;integer f,scan,k,q;reg [63:0] v;reg [7:0] header_error;integer header_valid,rows;
 reg query_response=0,query_hit=0;reg [63:0] query_data=0;
 wire fill_query;wire [2:0] fill_query_kind;wire [12:0] fill_query_index;wire [15:0] fill_query_generation;
 wire selected_query=fill_busy?fill_query:query;
 wire [2:0] selected_kind=fill_busy?fill_query_kind:query_kind;
 wire [12:0] selected_index=fill_busy?fill_query_index:query_index;
 assign response=query_response&&!fill_busy&&!fill_start;assign hit=query_hit&&!fill_busy&&!fill_start;assign data=query_data;
 always @(posedge clk)begin
  query_response<=selected_query;query_hit<=selected_query;query_data<=0;
  if(reset)begin query_response<=0;query_hit<=0;end
  else if(selected_query)begin
   case(selected_kind)
    0:query_data<=table0[selected_index];1:query_data<=table1[selected_index];2:query_data<=table2[selected_index];
    3:query_data<=table3[selected_index];4:query_data<=table4[selected_index];5:query_data<=table5[selected_index];6:query_data<=table6[selected_index];
   endcase
   if((MODE==1||(MODE==6&&generation==12))&&selected_kind==0&&selected_index==20)query_hit<=0;
  end
 end
 wire mem_ready,mem_response,mem_request,mem_abort;wire [21:0] mem_address;reg [21:0] mem_reply_address;reg [15:0] mem_generation_held;
 wire [15:0] mem_generation;reg [7:0] mem_data;reg [2:0] memory_wait=0;reg memory_response=0;
 assign mem_ready=memory_wait==0&&!memory_response;assign mem_response=memory_response;
 // Physical-reader sharing was checked separately. This backend replays the
 // exact private ROM byte at each requested address with bounded latency.
 always @(posedge clk)begin
  memory_response<=0;
  if(reset)begin memory_wait<=0;memory_response<=0;mem_reply_address<=0;mem_generation_held<=0;mem_data<=0;end
  else if(mem_request&&mem_ready)begin memory_wait<=5;mem_reply_address<=mem_address;mem_generation_held<=mem_generation;end
  else if(memory_wait!=0)begin
   memory_wait<=memory_wait-1;
   if(memory_wait==1)begin memory_response<=1;mem_data<=chr[mem_reply_address-22'h200000];end
  end
 end
 nes_native_fill165 #(.WAIT_CYCLES(65536)) fill(
 .clk(clk),.reset(reset),.start(fill_start),.clear(release_frame),.frame_owned(frame_owned),.geometry_valid(geometry_valid),.frame_generation(generation),
 .query(fill_query),.query_kind(fill_query_kind),.query_index(fill_query_index),.query_generation(fill_query_generation),.response(query_response),.hit(query_hit),.data(query_data),
 .mem_idle(mem_ready),.mem_ready(mem_ready),.mem_response(mem_response),.mem_error(1'b0),.mem_response_address(mem_reply_address),.mem_response_generation(mem_generation_held),.mem_data(mem_data),
 .mem_request(mem_request),.mem_abort(mem_abort),.mem_address(mem_address),.mem_generation(mem_generation),
 .byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),.byte_tile(byte_tile),.byte_lane(byte_lane),.byte_kind(byte_kind),.byte_generation(byte_generation),
 .busy(fill_busy),.done(fill_done),.success(fill_success),.error(),.quarantine(),.tile_count(),.byte_count(),.cycles());
 nes_native_export165 #(.MAX_CYCLES(262144)) exporter(
 .clk(clk),.reset(reset),.enable(1'b1),.frame_owned(frame_owned),.geometry_valid(geometry_valid),.frame_generation(generation),
 .row_count(8'd224),.object_count(objects[7:0]),.exception_count(exceptions[7:0]),.group_count(groups[5:0]),.palette_count(palettes[5:0]),
 .release_frame(release_frame),.query(query),.query_kind(query_kind),.query_index(query_index),.query_generation(query_generation),.response(response),.hit(hit),.data(data),
 .fill_start(fill_start),.fill_busy(fill_busy),.fill_done(fill_done),.fill_success(fill_success),.byte_valid(byte_valid),.byte_ready(byte_ready),.byte_data(byte_data),
 .byte_tile(byte_tile),.byte_lane(byte_lane),.byte_kind(byte_kind),.byte_generation(byte_generation),
 .tx_valid(tx_valid),.tx_ready(tx_ready),.tx_data(tx_data),.ack_valid(ack_valid),.ack_ready(ack_ready),.ack_accept(ack_data[16]),.ack_generation(ack_data[15:0]),.busy(busy),.error(error));
 nes_native_mailbox165 #(.WIDTH(96)) records(.src_clk(clk),.dst_clk(host_clk),.reset(reset),.src_valid(tx_valid),.src_ready(tx_ready),.src_data(tx_data),.dst_valid(host_valid),.dst_ready(host_ready),.dst_data(host_data));
 nes_native_mailbox165 #(.WIDTH(17)) prepared(.src_clk(host_clk),.dst_clk(clk),.reset(reset),.src_valid(host_ack_valid),.src_ready(host_ack_ready),.src_data(host_ack_data),.dst_valid(ack_valid),.dst_ready(ack_ready),.dst_data(ack_data));
 integer host_ticks=0,records_seen=0,bytes_seen=0,commits=0,aborts=0,out,ack_delay=0;
 reg awaiting_ack=0,stale_sent=0;reg [95:0] stalled_data;reg stalled=0;
 always @(posedge host_clk)begin
  if(reset)begin host_ticks<=0;records_seen<=0;bytes_seen<=0;host_ack_valid<=0;awaiting_ack<=0;ack_delay<=0;stalled<=0;stale_sent<=0;end
  else begin
   host_ticks<=host_ticks+1;
   if(stalled&&host_data!==stalled_data)$fatal(1,"mailbox data changed under backpressure");
   stalled<=host_valid&&!host_ready;stalled_data<=host_data;
   if(host_ack_valid&&host_ack_ready)host_ack_valid<=0;
   if(awaiting_ack)begin
    ack_delay<=ack_delay+1;
    if(ack_delay==8&&MODE!=3&&MODE!=4)begin
     host_ack_data<={MODE!=2,generation};host_ack_valid<=1;awaiting_ack<=0;
    end
   end
   if(host_valid&&host_ready)begin
    $fwrite(out,"%024h\n",host_data);
    if(host_data[95:93]!=7)begin records_seen<=records_seen+1;if(host_data[95:93]==6)bytes_seen<=bytes_seen+1;end
    else case(host_data[76:64])
     0:begin records_seen<=0;bytes_seen<=0;end
     1:begin
      if(host_data[31:16]!=records_seen||host_data[15:0]!=bytes_seen||bytes_seen!=240)$fatal(1,"END counters incomplete");
      awaiting_ack<=1;ack_delay<=0;
      // A stale acknowledgement must never release or commit this lease.
      host_ack_data<={1'b1,generation-16'd1};host_ack_valid<=1;stale_sent<=1;
     end
     2:aborts<=aborts+1;
     3:begin if(MODE!=0&&MODE!=5&&MODE!=6)$fatal(1,"failed scene committed");commits<=commits+1;end
    endcase
   end
  end
 end
 always @(negedge host_clk)if(!reset)host_ready=(host_ticks%11!=0&&host_ticks%11!=1);
 always @(posedge clk)if(release_frame)frame_owned<=0;
 initial begin
  if(!$value$plusargs("PREFIX=%s",prefix))$fatal(1,"PREFIX missing");
  f=$fopen({prefix,".dump"},"r");scan=$fscanf(f,"H %d %h %d %d %d %d\n",header_valid,header_error,rows,groups,objects,exceptions);
  palettes=1;
  while(!$feof(f))begin
   scan=$fscanf(f,"%d %d %h\n",k,q,v);
   if(scan==3)case(k)
    0:table0[q]=v;1:table1[q]=v;2:table2[q]=v;3:table3[q]=v;4:table4[q]=v;5:begin table5[q]=v;if(q>=32)palettes=2;end 6:table6[q]=v;
   endcase
  end
  $fclose(f);$readmemh("chr.hex",chr);out=$fopen("records.tsv","w");
  repeat(8)@(negedge clk);reset=0;repeat(12)@(negedge clk);frame_owned=1;
  if(MODE==4)begin wait(awaiting_ack);@(negedge clk);geometry_valid=0;end
  if(MODE==5)begin
   wait(bytes_seen>10);@(negedge clk);reset=1;frame_owned=0;$fwrite(out,"R\n");
   repeat(10)@(negedge clk);generation=16'hffff;reset=0;repeat(12)@(negedge clk);frame_owned=1;
  end
  if(MODE==6)begin
   wait(query&&query_index==20);#1;host_clock_on=0;
   wait(!frame_owned);repeat(10)@(negedge clk);generation=13;frame_owned=1;
   repeat(20)@(negedge clk);host_clock_on=1;
  end
  if(MODE==0||MODE==5||MODE==6)wait(commits==1);else wait(aborts==1);
  wait(!busy);repeat(20)@(negedge clk);
  if(commits!=(MODE==0||MODE==5||MODE==6)||aborts!=(MODE!=0&&MODE!=5)||frame_owned)$fatal(1,"retirement mismatch");
  $fclose(out);$display("PASS HOST165 mode=%0d commits=%0d aborts=%0d records=%0d bytes=%0d",MODE,commits,aborts,records_seen,bytes_seen);$finish;
 end
 // Pause the destination clock while source data is outstanding.
 initial begin wait(!reset);wait(tx_valid&&tx_ready);#30;host_clock_on=0;#2000;host_clock_on=1;end
 initial begin #30000000;$fatal(1,"host watchdog");end
endmodule
