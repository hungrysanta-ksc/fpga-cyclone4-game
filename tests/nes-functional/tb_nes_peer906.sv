`timescale 1ns/1ps
module tb_nes_peer906;
 `include "period.svh"
 reg clk=0; always #5 clk=!clk;
 reg reset=1,stop=0,cap_start=0,cap_sample=0,cap_seal=0,cap_release=0;
 reg [16:0] cap_addr=0; reg [7:0] cap_data=0;
 reg [1:0] kind=2;reg [9:0] slot=0;reg [12:0] tag=0;
 reg [47:0] rows=48'hff6b646d2240;reg [7:0] mask=0;reg shortform=1,pv=0;
 wire tr,tv,done,fault,drained,mreq,cap_ready,sample_ready;
 wire [21:0] maddr;reg [21:0] raddr=0;
 reg [7:0] data=0,peer=0;wire [7:0] outbyte;
 wire [4:0] idx;wire [5:0] length;wire [1:0] outkind;wire [9:0] outslot;wire [15:0] outgen;
 reg [7:0] chr[0:511],counts[0:30];integer cal[0:N-1];
 integer tick=0,pos=0,tile=0,waitcycles=0,stalls=0,phase,pattern,grants,total=0,emitted=0,fd;
 integer request_tick=-1,last_grant=-1;
 reg timed=0,mc_response=0;
 wire allowed=timed && tick==cal[pos];
 wire accept_out=stalls==0;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) dut(.clk(clk),.reset(reset),.stop(stop),.evt905(),.busy(),
  .core_ready(),.core_response(),.core_error(),.core_response_address(),.core_data(),
  .frame_owned(1'b1),.geometry_valid(1'b1),.frame_generation(16'd1079),.source_ready(1'b1),
  .source_is_rom(1'b1),.source_writing(1'b0),.captured_epoch(32'd1),.live_epoch(32'd1),
  .cap_start(cap_start),.cap_seal(cap_seal),.cap_sample(cap_sample),.cap_release(cap_release),
  .cap_generation(16'd1079),.cap_release_generation(16'd1079),.cap_address(cap_addr),.cap_data(cap_data),
  .cap_ready(cap_ready),.cap_sample_ready(sample_ready),.plan_short(shortform),.plan_valid(pv),
  .plan_kind(kind),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(8'd0),
  .plan_alt_tags(104'd0),.plan_generation(16'd1079),.plan_ready(tr),
  .qualified_slot(allowed),.core_safe(1'b1),.core_request(1'b0),.core_address(22'd0),
  .mem_ready(waitcycles==0),.mem_response(mc_response),.mem_response_address(raddr),.mem_error(1'b0),
  .mem_request(mreq),.mem_address(maddr),.mem_data(data),.bg_word(peer),
  .out_valid(tv),.out_ready(accept_out),.out_index(idx),.out_data(outbyte),.out_length(length),
  .out_kind(outkind),.out_generation(outgen),.out_slot(outslot),.done(done),.fault(fault),.drained(drained));

 // The two masks bracket how often both planes of a row miss. The physical
 // log records counts per tile, not which rows missed. Never infer its tags.
 function automatic bit miss(input integer i,a);
  integer order;
  order=pattern==0 ? (a%8)*2+a/8 : a;
  return pattern==2 || order<counts[i];
 endfunction
 integer elapsed=0,k,a,source_lane,edge_test,window_end,found_windows;
 always @(posedge clk)begin
  if(timed)begin
   elapsed<=elapsed+1;
   if(tick==PERIOD-1)begin tick<=0;pos<=0;end
   else begin tick<=tick+1;if(allowed && pos<N-1)pos<=pos+1;end
   if(stalls>0)stalls<=stalls-1;
   if(dut.arb_request && request_tick<0)request_tick=elapsed;
   if(mreq)begin
    if(!allowed || maddr[21:9]!=(22'h218000>>9) || request_tick<0)$fatal(1,"unqualified grant");
    $fdisplay(fd,"%0d %0d %0d %0d %0d",tile,grants,last_grant,request_tick,elapsed);
    request_tick=-1;last_grant=elapsed;grants=grants+1;total=total+1;
    waitcycles<=5;raddr<=maddr;data<=chr[maddr[8:0]];peer<=chr[maddr[8:0]|9'd8];
   end else if(waitcycles>0)waitcycles<=waitcycles-1;
   mc_response<=waitcycles==2;
   if(fault)$fatal(1,"unexpected source fault");
   if(tv && accept_out)begin
    source_lane=(idx[0]?8:0)+((rows>>(idx[3:0]*3))&7);
    if(idx!==emitted[4:0] || outslot!==slot || outgen!=1079 || outkind!==kind ||
        outbyte!==(kind==2 || idx>=16 || !mask[idx[3:1]] ? 8'd0 : chr[{tag[4:0],4'b0}+source_lane]))
      $fatal(1,"unexpected output tile=%d idx=%d",tile,idx);
    emitted=emitted+1;
   end
  end
 end
 task automatic launch;
  begin while(!tr)@(negedge clk);pv=1;@(negedge clk);pv=0;end
 endtask
 initial begin
  if(!$value$plusargs("phase=%d",phase)||!$value$plusargs("pattern=%d",pattern))$fatal;
  $readmemh("counts.hex",counts);$readmemh("chr.hex",chr);
  fd=$fopen("calendar.txt","r");
  for(k=0;k<N;k++)if($fscanf(fd,"%d",cal[k])!=1)$fatal;
  $fclose(fd);edge_test=$test$plusargs("edge");
  fd=$fopen(edge_test ? $sformatf("edge-%0d.tsv",phase) : $sformatf("requests-%0d-%0d.tsv",phase,pattern),"w");
  repeat(6)@(negedge clk);reset=0;while(!cap_ready)@(negedge clk);
  cap_start=1;@(negedge clk);cap_start=0;
  for(k=1;k<=30;k++)for(a=0;a<16;a++)if(!miss(k,a))begin
   while(!sample_ready)@(negedge clk);
   cap_sample=1;cap_addr=17'h18000+k*16+a;cap_data=chr[k*16+a];
   @(negedge clk);cap_sample=0;repeat(3)@(negedge clk);
  end
  cap_seal=1;@(negedge clk);cap_seal=0;
  tick=(phase-1)*178684;while(pos<N-1 && cal[pos]<tick)pos++;
  timed=1;
  for(tile=0;tile<=30;tile++)begin
   if(edge_test)begin
    if(!(tile==9 || tile==12 || tile==16 || tile==22))continue;
    // Directed boundary control. Start just before the last admissible
    // slot in each of two different windows from the independent trace.
    found_windows=0;window_end=-1;
    for(k=0;k<N-1;k++)if(cal[k+1]-cal[k]>200000)begin
     found_windows++;if(found_windows==phase)window_end=k;
    end
    if(window_end<1 || cal[window_end]-cal[window_end-1]<=50)$fatal;
    tick=cal[window_end]-50;pos=window_end;
   end
   kind=tile==0?2:1;tag=tile==0?0:13'h1800+tile;
   // Same eight discontinuities and final slot 30 as the wire descriptor.
   // Interior slot numbers and tag identities were not sampled.
   if(tile==0)slot=0;
   else if(tile<=5)slot=40+tile;
   else if(tile<=7)slot=60+tile;
   else if(tile<=26)slot=tile-8;
   else slot=32+(tile-27)*2;
   if(tile==30)slot=30;
   mask=tile==0 ? 0 : pattern==2 ? (1<<(counts[tile]/2))-1 : 255;
   rows=tile==0?0:48'hff6b646d2240;emitted=0;grants=0;last_grant=-1;
   launch();stalls=edge_test?0:24;while(!done)@(negedge clk);
   if(emitted!=(tile==0?16:32))$fatal;
   $display("TILE %0d %0d %0d",tile,grants,elapsed);@(negedge clk);
  end
  if(edge_test)begin $fclose(fd);$display("PASS906 directed last slot");$finish;end
  // Nonidentity full form and sparse masked rows must not inherit a peer.
  tile=30;shortform=0;rows=48'h924924924924;mask=8'h93;emitted=0;grants=0;
  launch();while(!done)@(negedge clk);if(emitted!=32)$fatal;
  // STOP with an outstanding physical request, then cold reload with no capture.
  cap_release=1;@(negedge clk);cap_release=0;emitted=0;
  launch();while(!mreq)@(negedge clk);@(negedge clk);stop=1;#1;
  if(tv||tr||mreq)$fatal(1,"late output after STOP");
  repeat(10)@(negedge clk);stop=0;while(!drained)@(negedge clk);
  emitted=0;grants=0;launch();while(!done)@(negedge clk);
  if(emitted!=32||grants!=8)$fatal(1,"full cold recovery");
  $fclose(fd);$display("PASS906 data identity STOP drain cold");$finish;
 end
 initial #900000000 $fatal(1,"timeout");
endmodule
