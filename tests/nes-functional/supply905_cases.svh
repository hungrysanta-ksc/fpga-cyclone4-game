 reg [2:0] stimulus=0,ev=0;reg nesclk=0,mem_response=0;
 always #23 nesclk=~nesclk;
 wire grant_ready,arb_fault,fill_response;
 nes_native_arbiter165 arb(.clk(nesclk),.reset(reset),.slot(stimulus[1]),.core_safe(1'b1),
  .core_request(1'b0),.core_address(22'd0),.fill_request(stimulus[0]),.fill_abort(1'b0),
  .fill_address(22'h200001),.fill_generation(16'd905),.fill_ready(grant_ready),.fill_response(fill_response),
  .mem_ready(1'b1),.mem_response(mem_response),.mem_error(1'b0),.mem_response_address(22'h200001),
  .mem_data(8'h42),.fault(arb_fault));
 always @(posedge nesclk)begin
  ev<=reset ? 0 : {stimulus[2],stimulus[0]&&grant_ready,stimulus[0]};
  mem_response<=!reset && stimulus[0]&&grant_ready;
 end
 wire first905;
 reg open905=0,put905=0,seal905=0,take905=0;
 reg [31:0] next_token=32'h1200ffff,taken=0;
 wire ready,wptr,rptr,pmiso,begin_ready,put_ready,pe,ce,pfault;
 wire [31:0] head_token;wire [11:0] length;
 nes_bulk_aperture188 aperture(.clk(clk),.reset(reset),.active(active),.stop(1'b0),
  .begin_valid(open905),.begin_length(next_token[0]?12'd16:12'd32),.begin_token(next_token),.begin_ready(begin_ready),
  .byte_valid(put905),.byte_data(8'h47),.byte_ready(put_ready),.seal(seal905),.cancel(1'b0),
  .producer_error(pe),.chunk_ready(ready),.chunk_length(length),.chunk_token(head_token),
  .consume(take905),.consume_token(taken),.consume_error(ce),
  .address(a),.read_n(rd),.write_n(wr),.writer903(wptr),.reader903(rptr));
 nes_plan_spi200 plan(.clk(clk),.reset(reset),.enable(active),.stop(1'b0),.source_fault(1'b0),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.miso(pmiso),.plan_idle(1'b1),.plan_ready(1'b1),
  .retire_done(1'b0),.end_generation(16'd905),.chunk_ready(ready),.chunk_kind(!head_token[0]),
  .chunk_length(length),.chunk_slot(10'd3),.chunk_generation(16'd905),.host_first(7'd0),.nes_first(8'd0),
  .chunk_token(head_token),.end_sealed(1'b0),.first905(first905),.fault(pfault));
 reg [7:0] bytes905[0:31];
 task page905(input integer page);
  ss=0;#200;octet('h78,b);octet(page,bytes905[1]);
  for(integer k=2;k<32;k++)octet(0,bytes905[k]);
  ss=1;#350;
 endtask
 integer capture905;
 task save_reply905;
  for(integer k=1;k<32;k++)$fdisplay(capture905,"%02x",bytes905[k]);
 endtask
 task e9;
  reg [7:0] c,x;
  ss=0;#200;c=0;
  for(integer k=0;k<9;k++)begin
   case(k) 0:x='he9;1:x=3;3:x=1;default:x=0;endcase
   c=c^x;repeat(8)c=c[7]?(c<<1)^7:c<<1;octet(x,b);
  end
  octet(c,b);octet('ha5,b);ss=1;#350;
 endtask
 task publish;
  @(negedge clk);if(!begin_ready)$fatal;open905=1;
  @(negedge clk);open905=0;put905=1;
  repeat(next_token[0]?16:32)@(negedge clk);
  put905=0;seal905=1;@(negedge clk);seal905=0;#120;
 endtask
 task consume;
  @(negedge clk);taken=head_token;take905=1;@(negedge clk);take905=0;#150;
 endtask
 task source(input [2:0] v);@(negedge nesclk);stimulus=v;@(negedge nesclk);stimulus=0;repeat(4)@(negedge nesclk);endtask
 function [35:0] word905(input integer i);
  return {bytes905[i+4][3:0],bytes905[i+3],bytes905[i+2],bytes905[i+1],bytes905[i]};
 endfunction
 reg [9:0] rq,gr,lg,ret0,ret1,start_stamp;
 reg [35:0] x;
 initial begin
  #130;reset=0;active=1;#1000;
  packet(905,1,0,0);e9();start_stamp=monitor.trace.origin;
  // One cache-served BG. The next tile waits on a held backing request,
  // then hits a second grant. The physical read bank stays on the first token.
  source(4);publish();next_token++;
  @(negedge clk);stimulus=1;#150;rq=monitor.trace.now;
  repeat(34000)@(negedge clk);source(3);gr=monitor.trace.now;
  repeat(34000)@(negedge clk);source(3);lg=monitor.trace.now;source(4);
  publish();e9();if(monitor.trace.origin!=start_stamp)$fatal(1,"second E9 reset timeline");
  consume();ret0=monitor.trace.now;#50000;consume();ret1=monitor.trace.now;
  packet(905,3,0,0);page905(0);
  capture905=$fopen("physical-page905.hex","w");if(!capture905)$fatal;
  save_reply905();
  if(arb_fault||fault||pfault||pe||ce||bytes905[1]!==8'h95||{bytes905[3],bytes905[2]}!==905||
     bytes905[4]!==2 || bytes905[5]!==2 || {bytes905[15],bytes905[14],bytes905[13],bytes905[12]}!==next_token)$fatal(1,"header");
  x=word905(16);if(x[35:30]!==0)$fatal(1,"cache hit");
  if(word905(24)!=={6'd2,lg,gr,rq})$fatal(1,"ROM timeline %x expected %x",word905(24),{6'd2,lg,gr,rq});
  page905(128);
  save_reply905();$fclose(capture905);
  if(word905(16)!=={4'b0,11'h7ff,1'b0,1'b0,8'd1,1'b0,ret0} ||
     word905(24)!=={4'b0,11'd0,1'b1,1'b1,8'd2,1'b0,ret1})$fatal(1,"bank return");
  packet(906,1,0,1);if(!fault)$fatal(1,"invalid receipt");
  active=0;#500;page905(0);if(bytes905[4]!==0 || bytes905[5]!==0)$fatal(1,"STOP");
  $display("PASS905 first E9, two overlapping banks, held request, multiple grants, cache hit, token carry, CRC guard and STOP");
  $finish;
 end
