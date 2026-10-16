`include "spi197_bus.svh"
reg host_clk=0;always #5.952 host_clk=!host_clk;
wire chunk_ready,bulk_fault,end_sealed,ck;wire [11:0] chunk_length;
wire [31:0] chunk_token;wire [9:0] cs;wire [15:0] cg;
wire host_valid196,seal196;wire [7:0] byte196;wire [5:0] length196;wire [15:0] crc196;
wire host_ready196,idle196,fault196,pv196,pr196,ev196,er196,spi_fault197;
wire [1:0] kind196;wire [15:0] gen196,eg196;wire [9:0] slot196;wire [12:0] tag196;
wire [47:0] rows196;wire [7:0] mask196,am196;wire [103:0] ats196;
nes_plan_spi197 endpoint(.clk(host_clk),.reset(reset),.enable(1'b1),.stop(stop),.source_fault(fault196||fault||bulk_fault),
 .SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),.selected(selected197),.miso(miso197),.fault(spi_fault197),
 .plan_idle(idle196),.plan_ready(host_ready196),.plan_write(host_valid196),.plan_data(byte196),.plan_seal(seal196),.plan_length(length196),.plan_crc(crc196),
 .chunk_ready(chunk_ready),.chunk_kind(ck),.chunk_length(chunk_length),.chunk_slot(cs),.chunk_generation(cg),.chunk_token(chunk_token),.end_sealed(end_sealed));
nes_plan_stream196 transport(.host_clk(host_clk),.nes_clk(clk),.reset(reset),.active(1'b1),.stop(stop),.source_fault(fault||spi_fault197),
 .write_valid(host_valid196),.write_ready(host_ready196),.write_data(byte196),.seal(seal196),.seal_length(length196),.seal_crc(crc196),
 .host_idle(idle196),.fault(fault196),.lease_valid(owned&&geometry),.lease_generation(16'(100+SCENE)),
 .plan_valid(pv196),.plan_ready(pr196),.tile_done(done),.plan_kind(kind196),.plan_generation(gen196),.plan_slot(slot196),
 .plan_tag(tag196),.plan_rows(rows196),.plan_mask(mask196),.plan_alt_mask(am196),.plan_alt_tags(ats196),
 .end_valid(ev196),.end_ready(er196),.end_generation(eg196));
integer wf,wn,wl,wi,wbyte,wcrc,submitted197=0,drains197=0;
reg [1023:0] wname;reg allow_consume197=0;
reg [7:0] wdata197[0:31];reg [7:0] fc197,unused197;
reg tile_done197=0;
always @(posedge clk)if(done)tile_done197<=1;
initial begin $sformat(wname,"scene%0d.wire",SCENE);if(MODE==1)wname="pressure.wire";wf=$fopen(wname,"r");if(!wf)$fatal(1,"wire file");end
always @(posedge host_clk)if(!reset&&(fault196||spi_fault197))$fatal(1,"plan SPI fault");
task poll197;
 integer k,offset;begin
  status197();
  if(rx197[3]&8'hfc||{rx197[4],rx197[5]}!=submitted197)$fatal(1,"status ownership");
  if(rx197[6]==1)begin
   offset=cs*(ck?32:16);
   if(!chunk_ready||rx197[7]!=ck||{rx197[9],rx197[8]}!=chunk_length||{rx197[11],rx197[10]}!=offset||
      {rx197[13],rx197[12]}!=cg||{rx197[17],rx197[16],rx197[15],rx197[14]}!=chunk_token)$fatal(1,"descriptor SPI mismatch");
   // Test consumer does raw SNES bus reads, then consumes; never via SPI.
   allow_consume197=1;wait(!allow_consume197);drains197++;rx197[3]=0;
  end else for(k=7;k<18;k=k+1)if(rx197[k])$fatal(1,"unready descriptor exposed");
 end
endtask
task submit_wire;
 begin
  tile_done197=0;
  wn=$fscanf(wf,"%h",wl);if(wn!=1||wl<16||wl>32)$fatal(1,"wire length");
  for(wi=0;wi<wl;wi=wi+1)begin wn=$fscanf(wf,"%h",wbyte);if(wn!=1)$fatal(1,"wire byte");wdata197[wi]=8'(wbyte);end
  wn=$fscanf(wf,"%h",wcrc);if(wn!=1)$fatal(1,"wire CRC");
  poll197();while(!rx197[3][0])poll197();
  fc197=crc8_197(crc8_197(0,8'he9),8'(wl));begin197();byte197(8'he9,unused197);byte197(8'(wl),unused197);
  for(wi=0;wi<wl;wi=wi+1)begin byte197(wdata197[wi],unused197);fc197=crc8_197(fc197,wdata197[wi]);end
  byte197(8'(wcrc>>8),unused197);byte197(8'(wcrc),unused197);fc197=crc8_197(crc8_197(fc197,8'(wcrc>>8)),8'(wcrc));
  byte197(fc197,unused197);byte197(8'ha5,unused197);end197();submitted197++;
 end
endtask
