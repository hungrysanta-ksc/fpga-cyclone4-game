 // 657 source, production two-slot staging and host aperture.
 reg [15:0] g=905;reg [9:0] slot=0;reg [12:0] tag=0;reg [1:0] kind=0;
 reg [47:0] rows=0;reg [103:0] alt=0;reg [7:0] mask=0,altmask=0;
 reg valid=0,ending=0,cancel=0,core=0;reg [21:0] core_addr=0;
 wire reset_src=reset||!run_enable;
 wire plan_ready,permit;wire accepted=valid&&permit&&plan_ready;
 wire request,tv,tr,done,fault,drained;
 wire [21:0] request_addr;wire[7:0] td;wire[4:0] idx;wire[5:0] length;
 wire[1:0] tk;wire[9:0] ts;wire[15:0] tg;
 wire cr,cp,ce;wire[21:0] ca;wire[7:0] cd;
 integer tick=0;always @(posedge clk)tick<=tick+1;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) source(.clk(clk),.reset(reset_src),.stop(cancel),
  .frame_owned(1'b1),.geometry_valid(1'b1),.frame_generation(g),.source_ready(1'b1),.source_is_rom(1'b1),
  .source_writing(1'b0),.captured_epoch(32'd7),.live_epoch(32'd7),
  .cap_start(1'b0),.cap_seal(1'b0),.cap_sample(1'b0),.cap_release(1'b0),.cap_address(17'd0),.cap_data(8'd0),
  .cap_generation(g),.cap_release_generation(g),.plan_valid(valid&&permit),.plan_ready(plan_ready),
  .plan_kind(kind),.plan_generation(g),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),
  .plan_mask(mask),.plan_alt_mask(altmask),.plan_alt_tags(alt),.qualified_slot(tick%12==0),
  .core_safe(!core),.core_request(core),.core_address(core_addr),.core_ready(cr),.core_response(cp),.core_error(ce),
  .core_response_address(ca),.core_data(cd),.mem_ready(ready),.mem_response(response),.mem_error(err),
  .mem_response_address(reply),.mem_data(rom_data),.bg_word(word_data),.mem_request(request),.mem_address(request_addr),
  .out_valid(tv),.out_ready(tr),.out_data(td),.out_index(idx),.out_length(length),
  .out_kind(tk),.out_slot(ts),.out_generation(tg),.done(done),.fault(fault),.drained(drained));
 reg host=0;always #5.952 if(run_enable)host=~host;
 wire chunk,bfault,end_ready,end_sealed,oe_n,ck;wire [15:0] cg;wire [31:0] token;
 wire[11:0] clen;wire[9:0] cs;wire[7:0] dout; reg [23:0] bus_addr=0;reg take=0,rd=1;reg[31:0] take_token;
 nes_tile_bulk206 bulk(.nes_clk(clk),.host_clk(host),.reset(reset_src),.active(run_enable),.stop(cancel),.source_fault(fault),
  .plan_valid(valid),.plan_taken(accepted),.plan_kind(kind),.plan_slot(slot),.plan_generation(g),.plan_permit(permit),
  .tile_valid(tv),.tile_ready(tr),.tile_data(td),.tile_index(idx),.tile_length(length),.tile_kind(tk),
  .tile_slot(ts),.tile_generation(tg),.end_valid(ending),.end_ready(end_ready),.end_generation(g),
  .token_seed(32'd1),.chunk_ready(chunk),.chunk_length(clen),.chunk_token(token),.chunk_kind(ck),.chunk_slot(cs),
  .chunk_generation(cg),.consume(take),.consume_token(take_token),.address(bus_addr),.read_n(rd),.write_n(1'b1),
  .data_out(dout),.oe_n(oe_n),.fault(bfault),.end_sealed(end_sealed));
 integer bf,jj;reg [31:0] last_token=0;
 initial begin bf=$fopen("chunks.txt","w");forever begin
  wait(chunk);@(negedge host);
  if(token<=last_token)$fatal(1,"stale token");
  $fwrite(bf,"%0d %0d %0d %0d ",cg,ck,cs,token);
  for(jj=0;jj<clen;jj=jj+1)begin bus_addr=24'h400800+jj;rd=0;#1;wait(!oe_n);@(negedge host);
   $fwrite(bf,"%02x",dout);end
  $fwrite(bf,"\n");rd=1;take_token=token;last_token=token;take=1;@(negedge host);take=0;
 end end
 integer stats;initial stats=$fopen("grants.txt","w");
 always @(posedge clk)if(!reset_src)begin
  if(fault||bfault)$fatal(1,"source/staging fault gen=%d slot=%d",g,slot);
  if(request&&ready&&!core)$fwrite(stats,"%0d %0d %05x\n",g,kind,request_addr);
 end
 task core_read(input integer addr);
  begin @(negedge clk);core_addr=addr;core=1;wait(cr);@(posedge clk);@(negedge clk);core=0;wait(cp);
   if(ce||ca!==22'(addr)||cd!==native_mem[{core_addr[21],core_addr[17:0]}])$fatal(1,"core byte");
   @(negedge clk);end
 endtask
