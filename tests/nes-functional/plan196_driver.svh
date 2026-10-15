// Actual C wire input drives the production dual-clock decoder.
reg host_valid196=0,seal196=0;reg [7:0] byte196=0;reg [5:0] length196=0;reg [15:0] crc196=0;
wire host_ready196,idle196,fault196,pv196,pr196,ev196,er196;
wire [1:0] kind196;wire [15:0] gen196,eg196;wire [9:0] slot196;wire [12:0] tag196;
wire [47:0] rows196;wire [7:0] mask196,am196;wire [103:0] ats196;
nes_plan_stream196 transport(.host_clk(mem_clk),.nes_clk(clk),.reset(reset),.active(1'b1),.stop(stop),.source_fault(fault),
 .write_valid(host_valid196),.write_ready(host_ready196),.write_data(byte196),.seal(seal196),.seal_length(length196),.seal_crc(crc196),
 .host_idle(idle196),.fault(fault196),.lease_valid(owned&&geometry),.lease_generation(16'(100+SCENE)),
 .plan_valid(pv196),.plan_ready(pr196),.tile_done(done),.plan_kind(kind196),.plan_generation(gen196),.plan_slot(slot196),
 .plan_tag(tag196),.plan_rows(rows196),.plan_mask(mask196),.plan_alt_mask(am196),.plan_alt_tags(ats196),
 .end_valid(ev196),.end_ready(er196),.end_generation(eg196));
integer wf,wn,wl,wi,wbyte,wcrc;reg [1023:0] wname;
initial begin $sformat(wname,"scene%0d.wire",SCENE);wf=$fopen(wname,"r");if(!wf)$fatal(1,"wire file");end
always @(posedge clk)if(!reset&&fault196)$fatal(1,"unexpected plan codec fault");
task submit_wire;
 begin
  wn=$fscanf(wf,"%h",wl);if(wn!=1||wl<16||wl>32)$fatal(1,"wire length");
  while(!idle196)@(negedge mem_clk);
  for(wi=0;wi<wl;wi=wi+1)begin
   wn=$fscanf(wf,"%h",wbyte);if(wn!=1)$fatal(1,"wire byte");
   @(negedge mem_clk);host_valid196=1;byte196=8'(wbyte);
   while(!host_ready196)@(negedge mem_clk);
   @(posedge mem_clk);#1;
  end
  @(negedge mem_clk);host_valid196=0;
  wn=$fscanf(wf,"%h",wcrc);if(wn!=1)$fatal(1,"wire CRC");
  length196=6'(wl);crc196=16'(wcrc);seal196=1;
  @(negedge mem_clk);seal196=0;
 end
endtask
