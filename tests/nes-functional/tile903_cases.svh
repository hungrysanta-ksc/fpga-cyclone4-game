// Uses the original SPI/E1/65816 test driver and the fitted aperture/E8 RTL.
 reg [15:0] expected903[1:3];
 reg open903=0,put903=0,seal903=0,take903=0;
 reg [31:0] next_token=32'h1200ffff,taken=0;
 wire ready,wptr,rptr,snap,pmiso,begin_ready,put_ready,pe,ce;
 wire [31:0] head_token;
 wire [11:0] length;
 nes_bulk_aperture188 #(.ALLOW_SHORT_SEAL(1)) aperture(.clk(clk),.reset(reset),.active(active),.stop(1'b0),
  .begin_valid(open903),.begin_length(12'd2),.begin_token(next_token),.begin_ready(begin_ready),
  .byte_valid(put903),.byte_data(8'h47),.byte_ready(put_ready),.seal(seal903),.cancel(1'b0),
  .producer_error(pe),.chunk_ready(ready),.chunk_length(length),.chunk_token(head_token),
  .consume(take903),.consume_token(taken),.consume_error(ce),
  .address(a),.read_n(rd),.write_n(wr),.writer903(wptr),.reader903(rptr));
 nes_plan_spi200 plan(.clk(clk),.reset(reset),.enable(active),.stop(1'b0),.source_fault(1'b0),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.miso(pmiso),.plan_idle(1'b1),.plan_ready(1'b1),
  .retire_done(1'b0),.end_generation(16'd905),.chunk_ready(ready),.chunk_kind(head_token[16]),
  .chunk_length(length),.chunk_slot(10'd3),.chunk_generation(16'd905),.host_first(7'd0),.nes_first(8'd0),
  .chunk_token(head_token),.end_sealed(1'b0),.snap903(snap));
 task publish;
  @(negedge clk);if(!begin_ready)$fatal(1,"no free tile bank");open903=1;
  @(negedge clk);open903=0;put903=1;
  @(negedge clk);put903=0;seal903=1;
  @(negedge clk);seal903=0;#100;
 endtask
 task consume;
  @(negedge clk);taken=head_token;take903=1;@(negedge clk);take903=0;#100;
 endtask
 task poll_tile(input [31:0] token);
  reg [7:0] reply903[1:19];
  ss=0;#200;octet('he8,b);
  for(integer k=1;k<20;k++)octet(0,reply903[k]);
  ss=1;#250;
  if({reply903[17],reply903[16],reply903[15],reply903[14]}!==token || reply903[6]!==1)
    $fatal(1,"wrong E8 head");
 endtask
 function [15:0] stamp(input integer k);
  return {snapshot[6+2*k],snapshot[5+2*k]};
 endfunction
 initial begin
  #130;reset=0;active=1;#1000;
  packet(904,1,0,0);packet(904,3,0,0);packet(905,1,0,0);
  publish();poll_tile(next_token);
  next_token=next_token+1;publish();expected903[1]=monitor.trace.now;
  poll_tile(next_token-1);packet(905,7,0,0);
  consume();expected903[2]=monitor.trace.now;
  #7500;expected903[3]=monitor.trace.now;poll_tile(next_token);
  poll_tile(next_token);packet(905,7,1,0);consume();packet(905,3,0,0);
  query();
  if(fault||pe||ce||snapshot[1]!==8'h93||snapshot[2]!==7||{snapshot[4],snapshot[3]}!==905||
    {snapshot[24],snapshot[23],snapshot[22],snapshot[21]}!==next_token||snapshot[25]!==1)
   $fatal(1,"identity, kind or final ACK");
  for(integer k=1;k<8;k++)if(^stamp(k)===1'bx||stamp(k)<stamp(k-1))$fatal(1,"order %d",k);
  for(integer k=1;k<=3;k++)if(stamp(k)<expected903[k]-1 || stamp(k)>expected903[k]+1)$fatal(1,"different token %d",k);
  packet(906,1,0,0);packet(906,3,0,0);query();if(snapshot[2]!==3)$fatal(1,"stale tile");
  packet(907,1,0,0);packet(907,7,1,1);query();
  if(!fault || snapshot[2][0])$fatal(1,"wrong ACK");
  active=0;#400;query();if(snapshot[2]!==0)$fatal(1,"STOP");
  $display("PASS903 hidden second bank, repeated first E8, carry, tile-free frame, CRC-checked queue, invalid identity, STOP");
  $finish;
 end
