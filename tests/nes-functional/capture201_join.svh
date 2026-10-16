// Actual collector/fill/export instances above come from the selected board.
// Only PPU stimulus, PSRAM replies and the final display decision are fixtures.
reg host_clk=0;always #5.952 host_clk=!host_clk;
`include "spi200_bus.svh"
wire pw201,ps201,pi201,pr201,pf201,pv201,ev201,er201,rf201,rd201,sf201;
wire [7:0] pd201;wire [9:0] pl201;wire [4:0] pn201;wire [15:0] pc201;
wire cr201,ck201,ef201,bf201;wire [11:0] cl201;wire [9:0] cs201;wire [15:0] cg201,sg201;wire [31:0] ct201;
wire tile_ready201,tile_done201,tile_fault201,tv201,tr201;wire [1:0] pk201,tk201;
wire [15:0] pg201,tg201;wire [9:0] slot201,ts201;wire [12:0] tag201;wire [47:0] rows201;
wire [7:0] mask201,altmask201,td201;wire [103:0] tags201;wire [4:0] ti201;wire [5:0] tl201;
reg consume201=0;reg [23:0] bus201=0;reg read201=1;wire [7:0] busdata201;wire busoe201,busdir201;
integer consumed201=0;reg [31:0] consume_token201=0;
nes_plan_spi200 endpoint(.clk(host_clk),.reset(reset),.enable(1'b1),.stop(1'b0),.source_fault(lease_fault201||pf201||bf201),
 .SPI_SS(ss197),.SPI_SCK(sck197),.SPI_MOSI(mosi197),.selected(selected197),.miso(miso197),.fault(sf201),
 .plan_idle(pi201),.plan_ready(pr201),.plan_write(pw201),.plan_data(pd201),.plan_seal(ps201),.plan_length(pl201),.plan_plans(pn201),.plan_crc(pc201),
 .retire_done(rd201),.retire(rf201),.end_generation(sg201),.chunk_ready(cr201),.chunk_kind(ck201),.chunk_length(cl201),
 .chunk_slot(cs201),.chunk_generation(cg201),.chunk_token(ct201),.end_sealed(ef201));
nes_plan_batch201 transport(.host_clk(host_clk),.nes_clk(clk),.reset(reset),.active(1'b1),.stop(1'b0),.source_fault(lease_fault201||sf201||bf201),
 .write_valid(pw201),.write_ready(pr201),.write_data(pd201),.retire(rf201),.retire_done(rd201),
 .retire_permitted(permit201),.retire_commit(retire_commit201),.seal(ps201),.seal_length(pl201),.seal_plans(pn201),.seal_crc(pc201),
 .host_idle(pi201),.fault(pf201),.lease_valid(lease201),.lease_generation(captured_gen201),
 .plan_valid(pv201),.plan_ready(tile_ready201),.tile_done(tile_done201),.plan_kind(pk201),.plan_generation(pg201),.plan_slot(slot201),.plan_tag(tag201),.plan_rows(rows201),.plan_mask(mask201),.plan_alt_mask(altmask201),.plan_alt_tags(tags201),
 .end_valid(ev201),.end_ready(er201),.end_generation(eg201));
nes_tile191 #(.EXTERNAL_PLAN(1)) tile(.clk(clk),.reset(reset),.stop(lease_fault201||sf201),.lease_valid(lease201),.lease_generation(captured_gen201),
 .plan_valid(pv201),.plan_ready(tile_ready201),.plan_kind(pk201),.plan_generation(pg201),.plan_slot(slot201),.plan_tag(tag201),.plan_rows(rows201),.plan_mask(mask201),.plan_alt_mask(altmask201),.plan_alt_tags(tags201),
 .mem_idle(1'b1),.mem_ready(1'b0),.mem_request(),.mem_cancel(),.mem_address(),.mem_generation(),.mem_response(1'b0),.mem_error(1'b0),
 .response_address(17'd0),.response_generation(16'd0),.response_data(8'd0),
 .out_valid(tv201),.out_ready(tr201),.out_data(td201),.out_index(ti201),.out_length(tl201),.out_kind(tk201),.out_slot(ts201),.out_generation(tg201),.busy(),.done(tile_done201),.fault(tile_fault201));
nes_tile_bulk193 bulk(.nes_clk(clk),.host_clk(host_clk),.reset(reset),.active(1'b1),.stop(1'b0),.source_fault(lease_fault201||sf201),
 .tile_valid(tv201),.tile_ready(tr201),.tile_data(td201),.tile_index(ti201),.tile_length(tl201),.tile_kind(tk201),.tile_slot(ts201),.tile_generation(tg201),
 .end_valid(ev201),.end_ready(er201),.end_generation(eg201),.token_seed(32'd1000),
 .chunk_ready(cr201),.chunk_length(cl201),.chunk_token(ct201),.chunk_kind(ck201),.chunk_slot(cs201),.chunk_generation(cg201),
 .consume(consume201),.consume_token(consume_token201),.consume_error(),.address(bus201),.read_n(read201),.write_n(1'b1),.data_out(busdata201),.oe_n(busoe201),.dir(busdir201),
 .fault(bf201),.end_sealed(ef201),.sealed_generation(sg201));
always @(posedge sf201 or posedge pf201 or posedge bf201)if(!reset&&!lease_fault201)
 $display("FIRST201 fault SPI=%b PLAN=%b BULK=%b state=%d kind=%d gen=%h lease=%h crc=%h/%h bytes=%d flags=%b/%b",sf201,pf201,bf201,transport.state,transport.plan_kind,transport.plan_generation,captured_gen201,transport.crc,pc201,transport.count,transport.hf,transport.nf);
reg memory_response=0;reg [21:0] memory_address=0;reg [15:0] memory_generation=0;reg [7:0] memory_data=0;
assign native_arbiter_fault=0;assign native_fill_ready=1;assign native_fill_idle=!memory_response;
assign native_fill_response=memory_response;assign native_fill_reply_address=memory_address;
assign native_fill_reply_generation=memory_generation;assign native_fill_data=memory_data;assign native_fill_mem_error=0;
reg ack=0;assign native_ack_valid=ack;assign native_ack_data={1'b1,native_generation};
integer clocks=0,begins=0,completed=0,releases=0,stalls=0,raw=0,checks201=0;
reg chr_ended201=0;
assign native_tx_ready=(clocks%11<6);
always @(posedge clk)begin
 memory_response<=native_fill_request;
 if(native_fill_request)begin memory_address<=native_fill_address;memory_generation<=native_fill_generation;memory_data<=native_fill_address[7:0]^8'h5a;end
 clocks<=clocks+1;ack<=0;
 if(!reset)begin
  if(native_release_frame)releases++;
  if(native_tx_valid&&!native_tx_ready)stalls++;
  if(native_tx_valid&&native_tx_ready)begin
   if(native_tx_data[95:93]==7)case(native_tx_data[76:64])
    0:begin begins++;chr_ended201=0;end
    1:ack<=1;
    2:$fatal(1,"unexpected exporter abort %h",native_tx_data);
    3:completed++;
    4:chr_ended201=1;
   endcase
   if(native_tx_data[95:93]==7&&native_tx_data[76:74]==3'b100&&chr_ended201)begin
    if(native_tx_data[73:64]!==10'(raw)||native_tx_data[63:60]<1||native_tx_data[63:60]>10)$fatal(1,"packed raw address/count");
    for(integer n=0;n<native_tx_data[63:60];n++)begin
     if(native_tx_data[(int'(native_tx_data[63:60])-1-n)*6+:6]!==pixel(185+raw/256,raw%256))$fatal(1,"packed raw export pixel");
     raw++;checks201++;
    end
   end
  end
 end
end
function automatic [15:0] crc16_201(input [15:0] c0,input [7:0] b);
 reg [15:0] c;integer k;begin c=c0^{b,8'd0};for(k=0;k<8;k++)c=c[15]?(c<<1)^16'h1021:c<<1;crc16_201=c;end
endfunction
task send_end201;
 reg [7:0] b[0:13],ignored,c;reg [15:0] c16;integer k;begin
  b[0]=8'he9;b[1]=6;b[2]=0;b[3]=2;b[4]=8'h82;b[5]=captured_gen201[7:0];b[6]=captured_gen201[15:8];
  b[7]=8'h83;b[8]=b[5];b[9]=b[6];
  c16=16'hffff;for(k=4;k<10;k++)c16=crc16_201(c16,b[k]);b[10]=c16[15:8];b[11]=c16[7:0];
  c=0;for(k=0;k<12;k++)c=crc8_197(c,b[k]);b[12]=c;b[13]=8'ha5;
  status197();if(rx197[3]!==1)$fatal(1,"initial credit");
  begin197();for(k=0;k<14;k++)byte197(b[k],ignored);end197();
  wait(cr201);if(cl201!==16||ct201!==32'(1000+consumed201)||cg201!==captured_gen201||ck201!==0||cs201!==0)$fatal(1,"zero descriptor");
  for(k=0;k<16;k++)begin
   @(negedge host_clk);bus201=24'h400800+24'(k);read201=0;repeat(5)@(negedge host_clk);
   if(busdata201!==0||busoe201!==0||busdir201!==1)$fatal(1,"zero aperture");read201=1;repeat(5)@(negedge host_clk);
  end
  consume_token201=ct201;consume201=1;@(negedge host_clk);consume201=0;consumed201++;
  status197();while(rx197[3]==0||rx197[3]==1)status197();
  if(rx197[3]!==2||rx197[6]!==0)$fatal(1,"END drain flags=%h chunk=%h",rx197[3],rx197[6]);checks201++;
 end
endtask
task request_retire201;
 reg [7:0] b[0:6],c,ignored;integer k;begin
  b[0]=8'hea;b[1]=captured_gen201[7:0];b[2]=captured_gen201[15:8];b[3]=0;b[4]=1;
  c=0;for(k=0;k<5;k++)c=crc8_197(c,b[k]);b[5]=c;b[6]=8'ha5;
  begin197();for(k=0;k<7;k++)byte197(b[k],ignored);end197();
 end
endtask
task retired201;
 begin
  status197();while(rx197[3]==6)status197();
  if(rx197[3]!==1||rx197[4]||rx197[5]||lease_fault201||pf201||sf201||bf201||tile_fault201)
   $fatal(1,"retire did not release both owners");checks201++;
 end
endtask
task next_frame201(input integer s);
 begin
  scenario=s;scanline=7;dot=0;commits=0;ppu_ce=0;rom_fault=0;ppu_valid=1;
  bg_low=0;bg_high=0;obj_low=0;obj_high=0;obj_valid=0;ppu_read=0;emphasis=0;fine_x=0;
  for(integer k=0;k<32;k++)palette[k*6+:6]=k;
  wait(native_initialized);@(negedge clk);
 end
endtask
task inspect201(input integer k,input integer a,input [63:0] expected);
 begin
  inspect=1;inspect_kind=3'(k);inspect_index=13'(a);tick();
  if(!native_frame_response||!native_frame_hit||native_frame_data!==expected)$fatal(1,"retained query k%0d a%0d",k,a);
  inspect=0;tick();checks201++;
 end
endtask
initial begin
 repeat(4)tick();reset=0;next_frame201(1);frame();wait(waiting201);repeat(5)tick();
 if(!lease201||captured_epoch201!=41||captured_gen201!=native_generation||completed!=1||releases!=1||native_frame_owned||raw!=512)$fatal(1,"export lease/capture release lease%b epoch%h gen%h/%h commit%0d release%0d owned%b raw%0d fault%b",lease201,captured_epoch201,captured_gen201,native_generation,completed,releases,native_frame_owned,raw,lease_fault201);checks201++;
 // Capture the next frame while the old immutable source generation is in use.
 next_frame201(0);frame();
 if(native_generation!=captured_gen201+16'd1||completed!=1||commits!=224||releases!=1||!lease201||export_permitted201)$fatal(1,"overlap replaced exported lease");checks201++;
 for(integer x=0;x<33;x++)inspect201(0,x,64'(x+1));
 send_end201();reader_drained201=0;request_retire201();status197();
 if(rx197[3]!==6||!waiting201||!native_frame_owned||releases!=1)$fatal(1,"retire ignored physical drain");checks201++;
 repeat(100)tick();reader_drained201=1;retired201();
 wait(waiting201);repeat(5)tick();
 if(captured_epoch201!=41||captured_gen201!=2||completed!=2||releases!=2)$fatal(1,"prefetched capture export");checks201++;
 send_end201();request_retire201();retired201();
 // Invalid geometry still releases immediately, without waiting for display.
 next_frame201(4);frame();wait(releases==3);repeat(5)tick();
 if(native_frame_owned||waiting201||lease_fault201||completed!=2)$fatal(1,"rejected capture held");checks201++;
 epoch201=42;
 next_frame201(0);frame();wait(waiting201);
 if(completed!=3||!lease201)$fatal(1,"capture did not recover after reject");checks201++;
 send_end201();request_retire201();retired201();
 // Mutation during the actual capture invalidates it even without a new query.
 next_frame201(0);repeat(300)one_dot();epoch201=43;repeat(5)tick();
 if(!lease_fault201||lease201||waiting201)$fatal(1,"epoch change not terminal");checks201++;
 if(raw!=512||consumed201!=3)$fatal(1,"missing pipeline bytes");
 $display("PASS CAPTURE201 checks=%0d commits=%0d raw_exported=512 overlapped_capture=1 rejections=1 source_faults=1",checks201,completed);$finish;
end
initial begin #250000000;$fatal(1,"capture201 watchdog");end
