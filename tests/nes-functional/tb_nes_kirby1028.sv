// Same validated batch and qualified ROM slots for both builds. The final
// group can be sealed before its first tile is admitted by the consumer.
`timescale 1ps/1ps
module tb_nes_kirby1028;
 reg host=0,nes=0,reset=1,stop=0;
 always #5952 host=~host;
 always #23281 nes=~nes;
 reg wr=0,seal=0,cap=0,cap_seal=0;
 reg [7:0] wd;
 reg [9:0] length;
 reg [4:0] count;
 reg [15:0] crc;
 wire writable,valid,ready,shortform,done,bad,fault,hint,hint_ready,capready;
 wire [13:0] tag,ht;
 wire [1:0] kind;
 wire [9:0] slot;
 wire [15:0] gen;
 wire [47:0] rows;
 wire [7:0] mask,alts,hm;
 wire [111:0] alt;
 reg warm=0,measure=0;
 integer cycle=0,release_at,phase,mode,version,prev_end;
 wire prior_batch=(mode==8 || mode==9) && kind==2;
 wire admit=warm || (measure && (prior_batch ? cycle>=(mode==8?1000:prev_end+4) : cycle>=release_at));
 wire [4:0] ix;
 wire [7:0] value;
 wire ov;
 nes_plan_batch206 decoder(.host_clk(host),.nes_clk(nes),.reset(reset),.stop(stop),.active(1'b1),.source_fault(1'b0),
  .write_valid(wr),.write_ready(writable),.write_data(wd),.seal(seal),.seal_length(length),.seal_plans(count),.seal_crc(crc),
  .retire(1'b0),.retire_permitted(1'b1),.lease_valid(1'b1),.lease_generation(16'd1),.hint(hint),.hint_tag(ht),.hint_mask(hm),.hint_ready(hint_ready),
  .plan_short(shortform),.plan_valid(valid),.plan_ready(admit&&ready),.tile_done(done),.plan_kind(kind),.plan_generation(gen),
  .plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(alts),.plan_alt_tags(alt),
  .next_alt_row(3'd0),.end_ready(1'b1),.fault(bad));
 integer grant_fifo[0:2047],grants=0,gi=0,lag=0;
 reg [21:0] echo_addr;
 reg [7:0] rom[0:262143];
 wire window=warm || (measure && gi<grants && grant_fifo[gi]==cycle);
 wire req;wire [21:0] addr;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) src(.clk(nes),.reset(reset),.stop(stop),.hint(hint),.hint_tag(ht),.hint_mask(hm),
  .hint_ready(hint_ready),.page963(1'b0),.page_base963(11'd0),.cap_start(cap),.cap_seal(cap_seal),
  .cap_sample(1'b0),.cap_release(1'b0),.cap_generation(16'd1),.cap_release_generation(16'd1),.cap_address(18'd0),.cap_data(8'd0),.cap_ready(capready),
  .frame_owned(1'b1),.geometry_valid(1'b1),.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),
  .captured_epoch(32'd1),.live_epoch(32'd1),.frame_generation(16'd1),
  .plan_short(shortform),.plan_valid(valid&&admit),.plan_ready(ready),.plan_kind(kind),.plan_tag(tag),
  .plan_slot(slot),.plan_generation(gen),.plan_mask(mask),.plan_alt_mask(alts),.plan_alt_tags(alt),.plan_rows(rows),
  .core_safe(1'b1),.core_request(1'b0),.core_address(22'd0),.qualified_slot(window),
  .mem_ready(lag==0),.mem_response(lag==1),.mem_error(1'b0),.mem_response_address(echo_addr),
  .mem_data(rom[echo_addr[17:0]]),.bg_word(rom[echo_addr[17:0]|18'd8]),.mem_request(req),.mem_address(addr),
  .out_valid(ov),.out_ready(1'b1),.out_data(value),.out_index(ix),.done(done),.fault(fault));
 reg [7:0] bytes[0:47],saved[0:7];
 integer n,ck,tiles,f,rc,num,last,early=0,foreground=0,first_fg=-1,first_g=-1,first_hint=-1,seal_at=-1;
 integer ndone=0,checked=0,lastgrant=-1,biggest=0,blocked_row=-1,first_slot,prev_grants=0,prior_done=0;
 reg [13:0] expected_tag;
 reg [7:0] expected_data;
 always @(posedge nes)begin
  if(measure)cycle<=cycle+1;
  if(measure&&window)gi<=gi+1;
  if(lag)lag<=lag-1;
  if(req)begin
   if(!window || lag!=0 || addr[21:18]!=4'h8)$fatal(1,"unqualified read");
   echo_addr<=addr;lag<=4;
   if(measure && cycle<release_at)early++;
  end
  if(measure && hint && hint_ready && first_hint<0)first_hint=cycle;
  if(measure && src.ahead.foreground && first_fg<0)first_fg=cycle;
  if(measure && src.ahead.foreground && src.shared_ready)begin
   if(first_g<0)first_g=cycle;
   if(lastgrant>=0 && cycle-lastgrant>biggest)begin biggest=cycle-lastgrant;blocked_row=ndone*8+addr[2:0];end
   lastgrant=cycle;foreground++;
  end
  if(!stop && !reset && (bad||fault))$fatal(1,"source/decoder fault");
  if(measure && ov && prior_batch && value!==0)$fatal(1,"prior payload");
  if(measure && ov && !prior_batch)begin
   if(ndone>=tiles || kind!==1 || slot!==first_slot+ndone || ix!==checked%32)$fatal(1,"output identity/order");
   expected_tag={bytes[ndone*8+6][5:0],bytes[ndone*8+5]};
   expected_data=(ix>=16||!bytes[ndone*8+7][ix[3:1]])?0:rom[{expected_tag,ix[0],ix[3:1]}];
   if(value!==expected_data)$fatal(1,"Kirby CHR mismatch");
   checked++;
  end
  if(measure&&done)begin
   if(prior_batch)prior_done++;
   else begin ndone++;last=cycle;end
  end
 end
 task send(input integer len,input integer total,input integer checksum);
  @(negedge host);length=len;count=total;crc=checksum;
  for(integer i=0;i<len;i++)begin while(!writable)@(negedge host);wr=1;wd=bytes[i];@(negedge host);end
  wr=0;seal=1;if(measure)seal_at=cycle;@(negedge host);seal=0;
 endtask
 function automatic [15:0] checksum(input integer size);
  reg [15:0] c=16'hffff;
  for(integer i=0;i<size;i++)begin c=c^{bytes[i],8'h00};repeat(8)c=c[15]?(c<<1)^16'h1021:c<<1;end
  return c;
 endfunction
 initial begin
  if(!$value$plusargs("PHASE=%d",phase)||!$value$plusargs("MODE=%d",mode)||!$value$plusargs("VERSION=%d",version))$fatal;
  $readmemh("chr.hex",rom);
  f=$fopen($sformatf("case%0d.txt",phase),"r");if($fscanf(f,"%d %d %d %d %d",n,ck,tiles,release_at,prev_end)!=5)$fatal;$fclose(f);
  $readmemh($sformatf("batch%0d.hex",phase),bytes,0,n-1);first_slot=bytes[3];
  f=$fopen($sformatf("grants%0d.txt",phase),"r");
  while($fscanf(f,"%d",num)==1)begin
   grant_fifo[grants]=num;grants++;
   if(num<=prev_end)prev_grants++;
  end
  $fclose(f);
  repeat(8)@(negedge nes);reset=0;wait(capready);@(negedge nes);cap=1;@(negedge nes);cap=0;cap_seal=1;
  @(negedge nes);cap_seal=0;repeat(300)@(negedge nes);
  if(mode==1)begin
   // Real preceding demand arms the ordinary lookahead. Different directory index.
   for(integer i=0;i<8;i++)saved[i]=bytes[i];
   bytes[5]=8'h6e;bytes[6]=8'h31;bytes[7]=1;
   warm=1;send(8,1,checksum(8));wait(done);@(negedge nes);repeat(5)@(negedge nes);warm=0;
   for(integer i=0;i<8;i++)bytes[i]=saved[i];
  end
  if(mode==4)begin
   // Occupied, unrelated entries in the initial snapshot. Preserve all
   // previously valid rows until a real demand arms the original policy.
   for(integer j=0;j<256;j++)src.ahead.rows[j]={1'b1,10'h3ff,16'h5ac3};
  end
  measure=1;
  if(mode==8 || mode==9)begin
   for(integer i=0;i<6;i++)begin
    saved[i]=bytes[i];bytes[i]=(i%3==0)?8'h82:(i%3==1)?8'h01:8'h00;
   end
   send(6,2,checksum(6));@(negedge host);wait(writable);
   for(integer i=0;i<6;i++)bytes[i]=saved[i];
  end
  if(mode==2)wait(cycle>prev_end);
  if(mode>=5 && mode<=7)begin
   // Sample three seal deadlines with 32, 16 or 8 eligible edges left.
   wait(cycle>=grant_fifo[prev_grants-(32>>(mode-5))]-100);
  end
  send(n,tiles,ck);
  if(mode==4)begin
   wait(cycle==release_at-1);
   for(integer j=0;j<256;j++)if(src.ahead.rows[j]!=={1'b1,10'h3ff,16'h5ac3})$fatal(1,"resident evicted before demand");
  end
  if(mode==3)begin
   wait(req&&!src.ahead.foreground);@(posedge nes);@(negedge nes);stop=1;
   repeat(12)@(negedge nes);
   if(lag||req||ov||src.ahead.spec_owner||src.ahead.response||src.ahead.live||decoder.hint)$fatal(1,"canceled prefetch exposed data");
   $display("PASS1028_STOP");$finish;
  end
  wait(ndone==tiles);@(negedge nes);
  if(checked!=tiles*32 || first_hint<0 || prior_done!=((mode==8 || mode==9)?2:0))$fatal(1,"missing output/hint");
  stop=1;repeat(12)@(negedge nes);if(req||ov||lag||src.ahead.spec_owner)$fatal(1,"not drained");
  $display("PASS1028 phase=%0d mode=%0d version=%0d seal=%0d hint=%0d early=%0d fg=%0d first_fg=%0d first_grant=%0d max_intergrant=%0d delayed_tile_row=%0d done=%0d bytes=%0d",
   phase,mode,version,seal_at,first_hint,early,foreground,first_fg,first_g,biggest,blocked_row,last,checked);$finish;
 end
 initial #(64'd60000000000)$fatal(1,"timeout phase=%0d mode=%0d tiles=%0d",phase,mode,ndone);
endmodule
