// Matched 15-tile stream through tile205, capture cache, row cache and ROM arbiter.
module tb_nes_guide_source1017;
 reg clk=0,reset=1,stop=0,owned=1,pv=0,rec=0;
 reg [20:0] word_in=0,objects[0:63];
 reg [21:0] reads[0:111], returned;
 reg [7:0] warm[0:111],rom[0:131071],expected;
 reg [12:0] tag=0;
 reg [1:0] kind=2;
 reg [9:0] slot=0;
 reg [47:0] rows=0;
 wire ready,finished,fault,drained,emit,mreq;
 wire [21:0] physical;
 wire [7:0] data;wire [4:0] oi;wire [5:0] length;
 integer t=0,next_grant=0,openings[0:899],ng,nobj,source_done,e9,ret,fd,mode,phase;
 integer i,j,b,ret_time=-1,spec=0,fg=0,allbytes=0,last,first_bank_end,second_bank_end;
 wire grant=next_grant<ng&&openings[next_grant]==t;
 wire reply=t==ret_time;
 always #1 clk=~clk;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) dut(.clk(clk),.reset(reset),.stop(stop),.frame_owned(owned),
 .geometry_valid(owned),.frame_generation(16'd1),.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),
 .captured_epoch(32'd1),.live_epoch(32'd1),.plan_short(1'b1),.plan_valid(pv),.plan_ready(ready),
 .plan_kind(kind),.plan_generation(16'd1),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),
 .plan_mask(kind==1?8'hff:8'h00),.plan_alt_mask(8'd0),.plan_alt_tags(104'd0),
`ifndef MMC1012_REF
 .guide_record(rec),.guide_tag(word_in[20:8]),.guide_mask(word_in[7:0]),
`endif
 .cap_start(1'b0),.cap_seal(1'b0),.cap_release(1'b0),.cap_sample(1'b0),.cap_generation(16'd1),.cap_release_generation(16'd1),
 .cap_address(17'd0),.cap_data(8'd0),.page963(1'b0),.page_base963(10'd0),.hint(1'b0),.hint_tag(13'd0),.hint_mask(8'd0),
 .qualified_slot(grant),.core_safe(1'b1),.core_request(1'b0),.core_address(22'd0),.mem_ready(ret_time<0),
 .mem_response(reply),.mem_error(1'b0),.mem_response_address(returned),.mem_data(rom[returned[16:0]]),
 .bg_word(rom[returned[16:0]+8]),.mem_request(mreq),.mem_address(physical),
 .out_valid(emit),.out_ready(1'b1),.out_data(data),.out_index(oi),.out_length(length),.done(finished),.fault(fault),.drained(drained));
 always @(posedge clk)begin
  if(!reset&&fault)$fatal(1,"source fault");
  if(reply)ret_time<=-1;
  if(grant)next_grant<=next_grant+1;
  if(mreq)begin
   if(!grant||ret_time>=0)$fatal(1,"unqualified request");
   returned<=physical;ret_time<=t+5;
   if(t<e9)spec<=spec+1;else fg<=fg+1;
  end
  if(emit)begin
   expected=0;
   if(kind==1&&oi<16)expected=rom[tag*16+(oi>>1)+(oi[0]?8:0)];
   if(data!==expected||oi!=b||length!=(kind==1?32:16))$fatal(1,"independent CHR output");
   b<=b+1;allbytes<=allbytes+1;
  end
  t<=t+1;if(t>1300000)$fatal(1,"watchdog");
 end
 reg [21:0] key;
 initial begin
  if(!$value$plusargs("MODE=%d",mode)||!$value$plusargs("PHASE=%d",phase))$fatal;
  fd=$fopen($sformatf("phase%0d.txt",phase),"r");if($fscanf(fd,"%d %d %d %d",ng,nobj,source_done,e9)!=4)$fatal;
  for(i=0;i<ng;i=i+1)if($fscanf(fd,"%d",openings[i])!=1)$fatal;
  $fclose(fd);fd=$fopen($sformatf("return%0d.txt",phase),"r");if($fscanf(fd,"%d",ret)!=1)$fatal;
  $fclose(fd);$readmemh("chr.hex",rom);$readmemh("reads.hex",reads);$readmemh("warm.hex",warm);$readmemh("objects.hex",objects,0,nobj-1);
  repeat(4)@(negedge clk);reset=0;repeat(270)@(negedge clk);
  for(i=0;i<112;i=i+1)if(warm[i]||mode==2)begin
   key=warm[i]?reads[i]:reads[i]^22'h200;
   dut.ahead.rows[dut.ahead.cache_index(key)]={1'b1,key[16:8],rom[key[16:0]+8],rom[key[16:0]]};
  end
  while(t<source_done)@(negedge clk);
  for(i=0;i<nobj;i=i+1)begin word_in=objects[i];rec=mode!=0;@(negedge clk);rec=0;@(negedge clk);end
  while(t<e9)@(negedge clk);
  for(i=0;i<15;i=i+1)begin
   if(i==13)while(t<e9+ret)@(negedge clk);
   kind=i==0?2:1;slot=i;tag=i==0?0:reads[(i-1)*8][16:4];rows=0;b=0;
   if(i!=0)for(j=0;j<16;j=j+1)rows[j*3+:3]=j/2;
   pv=1;do begin @(posedge clk);end while(!ready);
   @(negedge clk);pv=0;while(!finished)@(negedge clk);
   if(b!=(i==0?16:32))$fatal(1,"truncated tile");
   if(i==0)first_bank_end=t-e9;if(i==12)second_bank_end=t-e9;
  end
  last=t-e9;
  if(allbytes!=464 || fg!=(mode==1&&phase!=3?0:16))$fatal(1,"foreground or byte count");
  stop=1;owned=0;repeat(12)@(negedge clk);
  if(!drained||emit||mreq||ready)$fatal(1,"STOP did not quiesce");
  $display("SOURCE phase=%0d mode=%0d spec=%0d fg=%0d bytes=%0d first=%0d second=%0d last=%0d PASS",phase,mode,spec,fg,allbytes,first_bank_end,second_bank_end,last);
  $finish;
 end
endmodule
