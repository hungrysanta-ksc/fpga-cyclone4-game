// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tb_nes_port914 #(parameter REPLAY=0, parameter RETAIN951=0, parameter [15:0] G=16'd912);
 reg clk=0,host=0,mem=0,reset=0,stop=0;
 always #23.28 clk=~clk;
 always #5.95 host=~host;
 always #2.976 mem=~mem;
 reg write_en=0,seal=0,permit=1,core_want=0,out_ready=1;
 reg [7:0] byte_in; reg [15:0] crc;reg [9:0] size;reg [4:0] count;
 reg cap_start=0,cap_seal=0,cap_sample=0,release_capture951=0,qualified=1;
 reg [16:0] cap_addr;reg [7:0] cap_data;
 wire cap_ready,cap_sample_ready,bulk_ok,bulk_permit,ev,er;
 wire [15:0] eg;wire [1:0] out_kind;wire [5:0] out_length;
 wire enabled_plan=REPLAY?bulk_permit:permit;
 wire output_ready=REPLAY?bulk_ok:out_ready;
 wire wr,pv,pr,done,shortform,hint,hint_ready,closed,batch_fault,host_idle;
 wire [12:0] tag,hint_tag;wire [7:0] mask,altmask,hint_mask;
 wire [1:0] kind;wire [15:0] gen;wire [9:0] slot;
 wire [47:0] rows;wire [103:0] alts;
 wire [4:0] idx;wire tv;
 wire [3:0] next_tile_index=tv&&output_ready?idx[3:0]+1'b1:idx[3:0];
 nes_plan_batch206 transport(.next_alt_row(next_tile_index[3:1]),.host_clk(host),.nes_clk(clk),.reset(reset),.active(1'b1),
  .stop(stop),.source_fault(1'b0),.write_valid(write_en),.write_ready(wr),.write_data(byte_in),
  .retire(1'b0),.retire_permitted(1'b0),.seal(seal),.seal_length(size),.seal_plans(count),
  .host_idle(host_idle),
  .seal_crc(crc),.fault(batch_fault),.lease_valid(1'b1),.lease_generation(G),
  .plan_short(shortform),.plan_valid(pv),.plan_ready(pr&&enabled_plan),.tile_done(done),
  .plan_kind(kind),.plan_generation(gen),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),
  .plan_mask(mask),.plan_alt_mask(altmask),.plan_alt_tags(alts),.end_ready(REPLAY?er:1'b1),.end_valid(ev),.end_generation(eg),
  .hint(hint),.hint_ready(hint_ready),.hint_tag(hint_tag),.hint_mask(hint_mask));
 wire mready,mreq,mresp,merr,drained,core_ok,core_return,fault;
 wire [21:0] addr,phys_reply,ram_addr;
 wire [21:0] back_addr={phys_reply[21:4],phys_reply[0],phys_reply[3:1]};
 wire [7:0] lo,hi,tdata;wire [9:0] dest;
 wire ce1,ce2;
 wire core_req=core_want&&core_ok;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) source(.clk(clk),.reset(reset),.stop(stop),
  .frame_owned(1'b1),.geometry_valid(1'b1),.frame_generation(G),
  .source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),.captured_epoch(32'd1),.live_epoch(32'd1),
  .plan_short(shortform),.plan_valid(pv&&enabled_plan),.plan_ready(pr),.plan_kind(kind),
  .plan_generation(gen),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),
  .plan_alt_mask(altmask),.plan_alt_tags(alts),.cap_start(cap_start),.cap_seal(cap_seal),.cap_release(release_capture951),.cap_release_generation(G),
  .cap_ready(cap_ready),.cap_generation(G),.cap_sample_ready(cap_sample_ready),.cap_address(cap_addr),.cap_data(cap_data),
  .cap_sample(cap_sample),.qualified_slot(qualified),.core_safe(!core_want),.core_request(core_req),
  .core_address(22'h200040),.core_ready(core_ok),.core_response(core_return),
  .mem_ready(mready),.mem_response(mresp),.mem_error(merr),.mem_response_address(back_addr),
  .mem_data(lo),.bg_word(hi),.mem_request(mreq),.mem_address(addr),.out_valid(tv),.out_ready(output_ready),
  .out_kind(out_kind),.out_length(out_length),
  .out_data(tdata),.out_index(idx),.out_slot(dest),.done(done),.fault(fault),.drained(drained),
  .hint(hint),.hint_ready(hint_ready),.hint_tag(hint_tag),.hint_mask(hint_mask));
 reg [7:0] salt=8'had;
 function automatic [7:0] content(input [12:0] t,input [2:0] row_id,input plane);
  content=t[7:0]^t[12:5]^{2'b0,row_id,3'd4}^(plane?8'h5a:8'ha5)^salt;
 endfunction
 wire [21:0] word_addr={ram_addr[19:0],ce1,1'b0};
 // Logical bit 3 selects the high/low PSRAM lane. Reconstruct every byte
 // from the physical chip and address pins, independently of request state.
 reg [7:0] chr[0:131071],expected_bytes[0:(RETAIN951?16383:8191)];
 wire [15:0] pins=REPLAY? {chr[{word_addr[16:4],1'b0,word_addr[3:1]}],chr[{word_addr[16:4],1'b1,word_addr[3:1]}]}:
   {content(word_addr[16:4],word_addr[3:1],1'b0),content(word_addr[16:4],word_addr[3:1],1'b1)};
 nes_rom_physical #(.READ_CYCLES(16)) reader(.clk(clk),.mem_clk(mem),.reset(reset),.check_mode(1'b0),
  .check_request(1'b0),.check_address(22'd0),.rom_request(mreq),.rom_address({addr[21:4],addr[2:0],addr[3]}),
  .rom_ready(mready),.rom_response(mresp),.rom_error(merr),.rom_response_address(phys_reply),
  .rom_data(lo),.bg_word(hi),.psram_address(ram_addr),.psram_1ce(ce1),.psram_2ce(ce2),.psram_data(pins));
 integer fills=0,hits=0,bytes_out=0,done_count=0,core_reads=0;
 reg expected_error=0,full_bg=0;reg [7:0] bg_mask=0;
 wire [12:0] bg_tag=(!idx[0]&&bg_mask[idx[3:1]])?13'h1a31+idx[3:1]:13'h163;
 always @(posedge clk)if(!reset)begin
  if(fault||(batch_fault&&!expected_error&&!stop))$fatal(1,"unexpected fault");
  if(core_return)core_reads++;
`ifdef NES_COMPANION952
  if(source.ahead.take&&source.ahead.aux952&&(core_req||source.arb_request||stop))
   $fatal(1,"companion displaced a primary request");
`endif
  if(source.ahead.take&&source.ahead.spec)begin
   if(core_req||source.arb_request||stop)$fatal(1,"priority");fills++;
  end
  if(source.ahead.hit_reply&&source.arb_response)hits++;
  if(done)done_count++;
  if(tv&&output_ready)begin
   if(tdata!==(REPLAY?expected_bytes[((RETAIN951 && out_kind==1)?8192:0)+32*dest+idx]:idx>=16?8'h00:content(full_bg?bg_tag:13'h110+dest,idx[3:1],idx[0])))$fatal(1,"bad tile %d index %d data %x",dest,idx,tdata);
   bytes_out++;
  end
 end
 function automatic [15:0] update_crc(input [15:0] old,input [7:0] b);
  reg [15:0] c;c=old^{b,8'b0};repeat(8)c=c[15]?(c<<1)^16'h1021:c<<1;return c;
 endfunction
 task send_byte(input [7:0] b);
  @(negedge host);while(!wr)@(negedge host);
  byte_in=b;write_en=1;size++;crc=update_crc(crc,b);
 endtask
 task full(input [7:0] bits);
  size=0;count=1;crc='1;full_bg=1;bg_mask=bits;
  send_byte(0);send_byte(bits);send_byte(G[7:0]);send_byte(G[15:8]);send_byte(12);send_byte(0);
  send_byte('h63);send_byte(1);send_byte('hff);
  send_byte('h40);send_byte('h22);send_byte('h6d);send_byte('h64);send_byte('h6b);send_byte('hff);send_byte(1);
  for(int j=0;j<8;j++)if(bits[j])begin send_byte('h31+j);send_byte('h1a);end
  @(negedge host);write_en=0;seal=1;@(negedge host);seal=0;
 endtask
 task batch(input [15:0] g,input corrupt);
  size=0;count=4;crc='1;
  for(int i=0;i<4;i++)begin
   send_byte(8'h81);send_byte(g[7:0]);send_byte(g[15:8]);send_byte(8'(i));send_byte(0);
   send_byte(8'h10+8'(i));send_byte(1);send_byte(8'hff);
  end
  @(negedge host);write_en=0;if(corrupt)crc^=1;seal=1;
  @(negedge host);seal=0;
 endtask
 integer old_fills;
 task recover;
  @(negedge clk);stop=1;repeat(12)@(negedge clk);stop=0;
  repeat(150)@(negedge clk);expected_error=0;
 endtask
 initial if(!REPLAY)begin
  #2;reset=1;repeat(10)@(negedge clk);reset=0;repeat(150)@(negedge clk);
  expected_error=1;batch(G,1);repeat(40)@(negedge clk);
  if(!batch_fault||fills||bytes_out)$fatal(1,"CRC admission");recover();
  expected_error=1;batch(G+1,0);repeat(60)@(negedge clk);
  if(!batch_fault||fills||bytes_out)$fatal(1,"generation admission");recover();
  core_want=1;batch(G,0);repeat(60)@(negedge clk);
  if(fills||core_reads==0||bytes_out)$fatal(1,"core arbitration");
  core_want=0;wait(done_count==4);@(negedge clk);
  if(bytes_out!=128||hits==0||fills==0)$fatal(1,"no checked prefetch");
  recover();batch(G,0);wait(source.ahead.spec_owner);@(negedge clk);stop=1;
  #1;if(drained||source.arb_response||tv)$fatal(1,"early STOP drain");
  while(!mresp)begin @(negedge clk);if(source.arb_response||tv)$fatal(1,"late delivery");end
  @(negedge clk);if(!drained||source.ahead.spec_owner)$fatal(1,"physical owner not drained");
  salt=~salt;repeat(10)@(negedge clk);stop=0;repeat(150)@(negedge clk);
  batch(G,0);wait(done_count==8);@(negedge clk);
  full(8'ha5);wait(tv);@(negedge clk);out_ready=0;repeat(9)@(negedge clk);out_ready=1;
  wait(done_count==9);@(negedge clk);full(8'h5a);wait(done_count==10);
  $display("PASS914 checked repeated generation after STOP, hits=%0d speculative grants=%0d core=%0d",hits,fills,core_reads);$finish;
 end
 if(REPLAY)begin:trace_run
  reg consume=0;wire chunk,chunk_kind,bulk_fault,consume_fault,end_sealed;wire [31:0] token;
  reg seen_end=0,all_polls=0;integer accepted=0;
  wire [11:0] chunk_length;wire [15:0] chunk_gen;
  nes_tile_bulk206 bulk(.nes_clk(clk),.host_clk(host),.reset(reset),.stop(stop),.active(1'b1),.source_fault(1'b0),
   .plan_valid(pv),.plan_taken(pv&&pr&&enabled_plan),.plan_kind(kind),.plan_slot(slot),.plan_generation(gen),.plan_permit(bulk_permit),
   .tile_valid(tv),.tile_ready(bulk_ok),.tile_data(tdata),.tile_index(idx),.tile_length(out_length),.tile_kind(out_kind),.tile_slot(dest),.tile_generation(gen),
   .end_valid(ev),.end_ready(er),.end_generation(eg),.end_sealed(end_sealed),.token_seed(32'd1),.chunk_ready(chunk),.chunk_kind(chunk_kind),
   .chunk_length(chunk_length),.chunk_generation(chunk_gen),.chunk_token(token),.consume(consume),.consume_token(token),
   .consume_error(consume_fault),.fault(bulk_fault),.address(24'd0),.read_n(1'b1),.write_n(1'b1));
  integer tick=-1;reg counting=0;
  always @(posedge clk)if(counting)tick++;
  always @(posedge host)begin
   if(end_sealed)seen_end<=1;
   if(seal)accepted++;
  end
  always @(posedge clk)if(counting&&source.ahead.take)
   $display("ROM914 edge=%0d spec=%0d addr=%0d",tick,source.ahead.spec,source.shared_address[16:0]);
`ifdef NES_COMPANION952
  always @(posedge clk)begin
   if(counting && source.ahead.aux952 && source.ahead.take)
    $display("AUX952 at=%0d address=%0d",tick,source.ahead.physical_address[16:0]);
   if(counting && source.ahead.hit && source.ahead.demand)
    $display("HIT952 at=%0d address=%0d",tick,source.ahead.address[16:0]);
  end
`endif
  always @(posedge host)if(counting&&bulk.state==bulk.SEAL&&!bulk.hc)
   $display("PUB914 token=%0d bytes=%0d at=%0d",bulk.token,bulk.used,tick);
  reg [7:0] wire_bytes[0:4095];string dir, previous_rows;
  integer fd,a,b,c,prev,gr,bs,rs,deadline,sz,plans,check,off=0,j=0,ck,cs,prod,pop,first;
  integer totals,expected_jobs,expected_total;
  integer polls,sample,flags,seq,requested,observed,observed_flags,wrong=0,probes=0;
  initial begin
   if(!$value$plusargs("trace=%s",dir))$fatal;
   $readmemh({dir,"/chr914.hex"},chr);$readmemh({dir,"/expected914.hex"},expected_bytes);
   $readmemh({dir,"/wire914.hex"},wire_bytes);
   fd=$fopen({dir,"/cap914.txt"},"r");gr=$fopen({dir,"/grants914.txt"},"r");
   bs=$fopen({dir,"/batch914.txt"},"r");rs=$fopen({dir,"/tokens914.txt"},"r");
   totals=$fopen({dir,"/sizes914.txt"},"r");
   polls=$fopen({dir,"/polls914.txt"},"r");
   if($fscanf(totals,"%d %d",expected_jobs,expected_total)!=2)$fatal;
   if(!(fd&&gr&&bs&&rs))$fatal;
   #2;reset=1;qualified=0;repeat(8)@(negedge clk);reset=0;
   wait(cap_ready);@(negedge clk);cap_start=1;@(negedge clk);cap_start=0;prev=0;
   while($fscanf(fd,"%d %d %d",a,b,c)==3)begin
    repeat(a-prev-1)@(negedge clk);prev=a;
    if(!cap_sample_ready)$fatal;cap_sample=1;cap_addr=b;cap_data=c;@(negedge clk);cap_sample=0;
   end
   repeat(8)@(negedge clk);cap_seal=1;@(negedge clk);cap_seal=0;
   repeat(RETAIN951?280:150)@(negedge clk);
   // Carry only completed rows from the preceding RTL invocation. Everything
   // else starts from the independently captured generation and the ARM wire.
   if(RETAIN951==1 && G!=905)begin
    if(!$value$plusargs("previous_rows=%s",previous_rows))$fatal;
    $readmemh(previous_rows,source.ahead.rows);
   end
   counting=1;
   fork
    begin
     while($fscanf(polls,"%d %d %d %d",sample,flags,seq,requested)==4)begin
      while(tick<sample)@(negedge host);
      probes++;observed=chunk?token:0;observed_flags=seen_end?2:host_idle?1:0;
      if(chunk)$display("DESC914 edge=%0d local_token=%0d kind=%0d bytes=%0d slot=%0d gen=%0d",sample,token,chunk_kind,chunk_length,bulk.chunk_slot,chunk_gen);
      if(observed!=requested||accepted!=seq||observed_flags!=flags)begin
       if(wrong<8 || $test$plusargs("all_e8_differences"))$display("E8914 difference edge=%0d token=%0d/%0d flags=%0d/%0d count=%0d/%0d",sample,observed,requested,observed_flags,flags,accepted,seq);
       wrong++;
      end
     end
     all_polls=1;
    end
    begin
     while($fscanf(gr,"%d",a)==1)begin
      while(tick+1<a)@(negedge clk);qualified=1;@(negedge clk);qualified=0;
     end
    end
    begin
     while($fscanf(bs,"%d %d %d %d",deadline,sz,plans,check)==4)begin
      while(tick<deadline-2*sz)@(negedge clk);
      count=plans;crc='1;size=0;
      for(int k=0;k<sz;k++)send_byte(wire_bytes[off+k]);
      off+=sz;@(negedge host);write_en=0;if(crc!==check[15:0])$fatal(1,"wire CRC");
      while(tick<deadline)@(negedge host);
      if(tick>deadline+1)$fatal(1,"E9 bank unavailable at reference seal");
      seal=1;@(negedge host);seal=0;
     end
    end
    begin
     while($fscanf(rs,"%d %d %d %d",ck,cs,prod,pop)==4)begin
      j++;wait(chunk&&token==j);first=tick;
      if(chunk_kind!=ck||chunk_length!=cs||chunk_gen!=G||bulk_fault||consume_fault)$fatal(1,"chunk %d",j);
      $display("PORT914 chunk=%0d bytes=%0d head=%0d reference_producer=%0d reference_return=%0d",j,cs,first,prod,pop);
      while(tick<pop)@(negedge host);@(negedge host);consume=1;@(negedge host);consume=0;
     end
     if(j!=expected_jobs||bulk_fault||consume_fault||fault||batch_fault||bytes_out!=expected_total)$fatal(1,"end n=%0d bytes=%0d",j,bytes_out);
     wait(all_polls);
     if(RETAIN951)begin
      @(negedge clk);release_capture951=1;
      @(negedge clk);release_capture951=0;
      repeat(270)@(negedge clk);
      $writememh({dir,"/rows-out951.hex"},source.ahead.rows);
     end
     $display("E8914 compared=%0d different=%0d",probes,wrong);
     $display("PASS914 trace chunks=%0d bytes=%0d hits=%0d grants=%0d",j,bytes_out,hits,fills);$finish;
    end
   join
  end
 end
 initial begin if(REPLAY)repeat(RETAIN951?6000000:2500000)@(posedge clk);else #2000000;$fatal(1,"timeout");end
endmodule
