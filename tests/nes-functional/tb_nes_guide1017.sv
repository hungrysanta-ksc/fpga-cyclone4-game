// Compare immutable row service with the same physical foreground operands and grants.
module tb_nes_guide1017;
 reg clk=0, reset=1, flush=0, invalidate=0, plan=0, rec=0, demand=0;
 reg [12:0] tag=0;
 reg [7:0] mask=0;
 reg [21:0] addr=0, response_address=0;
 wire ready,response,request,guide_ready;
 wire [7:0] lo,hi;
 wire [21:0] physical;
 reg [7:0] rom[0:131071];
 reg [21:0] reads[0:111];
 reg [7:0] warm[0:111];
 reg [20:0] objects[0:63];
 integer openings[0:899];
 integer t=0,ng,nobj,e9,source_done,mode,phase,howmany;
 integer next_grant=0,return_at=-1,first_row=-1,demand_count=0,guide_count=0;
 integer i,j,first_request=-1,events,old_count;
 reg seeding=1;
 wire grant=!reset&&!invalidate&&return_at<0&&(seeding||(next_grant<ng&&openings[next_grant]==t));
 wire reply=return_at==t;
 nes_e9_rows914 #(.COMPACT(1),.SINGLE_READ(1),.CHECK_HINT(1),.COMPLETE_ROW_SET(1)) dut(
 .clk(clk),.reset(reset),.invalidate(invalidate),.flush_rom(flush),.empty_capture(1'b1),
 .page963(1'b0),.plan963(plan),.page_base963(10'd0),.hint(1'b0),.tag(13'd0),.mask(8'd0),.hint_ready(guide_ready),
 .guide_record(rec),.guide_tag(tag),.guide_mask(mask),.demand(demand),.pair(1'b1),.address(addr),
 .ready(ready),.response(response),.lo(lo),.hi(hi),.request(request),.physical_address(physical),
 .grant_ready(grant),.reply(reply),.physical_done(reply),.physical_error(1'b0),.reply_address(response_address),
 .physical_lo(rom[response_address[16:0]]),.physical_hi(rom[response_address[16:0]+8]));
 always #1 clk=~clk;
 always @(posedge clk)begin
  if(reply)return_at<=-1;
  if(!seeding && next_grant<ng && openings[next_grant]==t)next_grant<=next_grant+1;
  if(request&&grant)begin
   return_at<=t+5;response_address<=physical;
   if(!seeding)begin
    if(demand)demand_count<=demand_count+1;else guide_count<=guide_count+1;
   end
  end
  t<=t+1;
  if(t>1300000)$fatal(1,"stalled");
 end
 task operand(input [21:0] a);
 begin
  addr=a;demand=1;
  do begin @(posedge clk);end while(!ready);
  @(negedge clk);demand=0;
  while(!response)@(negedge clk);
  if({hi,lo}!=={rom[a[16:0]+8],rom[a[16:0]]})$fatal(1,"wrong returned row %x",a);
  @(posedge clk);@(negedge clk);
 end endtask
 initial begin
  if(!$value$plusargs("MODE=%d",mode)||!$value$plusargs("PHASE=%d",phase))$fatal;
  $readmemh("chr.hex",rom);
  $readmemh("reads.hex",reads);$readmemh("warm.hex",warm);
  events=$fopen($sformatf("phase%0d.txt",phase),"r");
  if($fscanf(events,"%d %d %d %d",ng,nobj,source_done,e9)!=4)$fatal;
  for(i=0;i<ng;i=i+1)if($fscanf(events,"%d",openings[i])!=1)$fatal;
  $fclose(events);$readmemh("objects.hex",objects,0,nobj-1);
  repeat(3)@(negedge clk);reset=0;repeat(260)@(negedge clk);
  for(i=0;i<112;i=i+1)if(warm[i])operand(reads[i]);
  // Valid nonmatching occupants exercise a conservative miss in the guide.
  if(mode==2)for(i=0;i<112;i=i+1)if(!warm[i])operand(reads[i]^22'h200);
  seeding=0;while(t<source_done)@(negedge clk);
  for(i=0;i<nobj;i=i+1)begin
   {tag,mask}=objects[i];rec=mode!=0;
   @(negedge clk);rec=0;repeat(1)@(negedge clk);
  end
  while(t<e9)@(negedge clk);
  plan=1;@(negedge clk); plan=0;
  for(i=0;i<112;i=i+1)begin
   j=demand_count;
   if(!warm[i]&&first_request<0)first_request=t;
   operand(reads[i]);
   if(!warm[i]&&first_row<0)first_row=t;
   if(warm[i]&&j!=demand_count)$fatal(1,"displaced one of 96 hits");
  end
  $display("RESULT phase=%0d mode=%0d guide=%0d foreground=%0d first_wait=%0d last_row=%0d",phase,mode,guide_count,demand_count,first_row-first_request,t-e9);
  if((mode==0||mode==2)&&demand_count!=16 ||mode==1&&demand_count!=(phase==3?16:0))$fatal(1,"unexpected misses");
  // STOP with an outstanding speculative request must discard its late reply.
  @(negedge clk);flush=1;invalidate=1;@(negedge clk);flush=0;invalidate=0;
  repeat(262)@(negedge clk);seeding=1;tag=37;mask=1;rec=1;@(negedge clk);rec=0;
  while(return_at<0)@(negedge clk);
  invalidate=1;flush=1;@(negedge clk);flush=0;
  repeat(268)@(negedge clk);invalidate=0;@(negedge clk);
  if(dut.rows[dut.cache_index({5'h10,13'd37,4'b0})][25]!==0)$fatal(1,"late STOP write");
  $display("PASS checked all rows, preserved hits, STOP drained");$finish;
 end
endmodule
