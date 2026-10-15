// Included in a source-pinned copy of192's actual reader/191 C-reference bench.
reg host_clk=0;always #5.952 host_clk=!host_clk;
reg ev=0,consume=0;wire er,chunk_ready,bulk_fault,consume_error,end_sealed;
wire [11:0] chunk_length;wire [31:0] chunk_token;wire ck;wire [9:0] cs;wire [15:0] cg,sg;
reg [31:0] consume_token=0;reg [23:0] bus_address=0;reg read_n=1;
wire [7:0] bus_data;wire bus_oe,bus_dir;
integer bus_bytes=0,chunks=0,full_wait=0,source_wait=0,wrong_checks=0,end_count=0;
reg [31:0] expected_token=1000;
nes_tile_bulk193 bridge(.nes_clk(clk),.host_clk(host_clk),.reset(reset),.active(1'b1),.stop(stop),.source_fault(fault),
 .tile_valid(ov),.tile_ready(out_ready),.tile_data(od),.tile_index(oi),.tile_length(length),.tile_kind(ok),.tile_slot(os),.tile_generation(og),
 .end_valid(ev),.end_ready(er),.end_generation(gen),.token_seed(32'd1000),
 .chunk_ready(chunk_ready),.chunk_length(chunk_length),.chunk_token(chunk_token),.chunk_kind(ck),.chunk_slot(cs),.chunk_generation(cg),
 .consume(consume),.consume_token(consume_token),.consume_error(consume_error),
 .address(bus_address),.read_n(read_n),.write_n(1'b1),.data_out(bus_data),.oe_n(bus_oe),.dir(bus_dir),
 .fault(bulk_fault),.end_sealed(end_sealed),.sealed_generation(sg));
always @(posedge host_clk)begin
 if(bridge.aperture.sealed==3)full_wait<=full_wait+1;
 if(end_sealed)begin if(sg!=gen)$fatal(1,"END generation");end_count<=end_count+1;end
 if(!reset&&bulk_fault)$fatal(1,"unexpected bulk fault");
end
always @(posedge clk)if(ov&&!out_ready)source_wait<=source_wait+1;
task host_tick;begin @(posedge host_clk);#1;end endtask
task finish_bulk;
 begin
  while(!er)tick();@(negedge clk);ev=1;tick();@(negedge clk);ev=0;
  while(end_count==0||chunk_ready||bus_bytes!=checked)host_tick();
  @(negedge host_clk);#1; // consumer records the completed consume on this edge
  if(end_count!=1||!wrong_checks||(MODE==1&&(!full_wait||!source_wait)))$fatal(1,"missing bulk coverage");
  $display("PASS BULK193 scene=%0d mode=%0d bytes=%0d chunks=%0d fullwait=%0d sourcewait=%0d wrong=%0d",SCENE,MODE,bus_bytes,chunks,full_wait,source_wait,wrong_checks);
 end
endtask
integer read_at,len,baseline_bg,expected_slot;reg expected_kind;reg [31:0] tok;
initial begin
 wait(!reset);
 if(MODE==1)begin wait(bridge.aperture.sealed==3);repeat(200)host_tick();end
 forever begin
  wait(chunk_ready);@(negedge host_clk);
  len=chunk_length;tok=chunk_token;
  baseline_bg=SCENE==0?144:160;
  expected_kind=MODE==0&&bus_bytes>=baseline_bg;
  expected_slot=MODE==1?1+bus_bytes/16:expected_kind?(bus_bytes-baseline_bg)/32:bus_bytes/16;
  if(cg!=gen||ck!=expected_kind||cs!=expected_slot||tok!=expected_token||len==0||len>2048||len%(ck?32:16)!=0)
   $fatal(1,"chunk descriptor scene=%d bytes=%d slot=%d expected=%d",SCENE,bus_bytes,cs,expected_slot);
  // A bad consume must neither change descriptor ownership nor expose next data.
  if(chunks==0)begin
   consume_token=tok+99;consume=1;host_tick();
   if(!consume_error||!chunk_ready||chunk_token!=tok||chunk_length!=len)$fatal(1,"wrong token changed owner");
   @(negedge host_clk);consume=0;wrong_checks++;
  end
  for(read_at=0;read_at<len;read_at++)begin
   #PHASE;bus_address=24'h400800+read_at;read_n=0;
   repeat(32)host_tick();
   if(bus_oe||!bus_dir||bus_data!==expected[MODE==1?16+(bus_bytes%16):bus_bytes])$fatal(1,"raw bus byte %d",bus_bytes);
   bus_bytes++;@(negedge host_clk);
  end
  bus_address=24'h401800;repeat(4)host_tick();if(!bus_oe)$fatal(1,"aliased read");
  @(negedge host_clk);read_n=1;consume_token=tok;consume=1;host_tick();
  if(consume_error)$fatal(1,"matching token refused");
  @(negedge host_clk);consume=0;chunks++;expected_token++;
 end
end
