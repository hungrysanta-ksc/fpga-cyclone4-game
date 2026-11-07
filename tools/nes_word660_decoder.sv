 reg put=0,seal=0;reg [7:0] wb;reg [255:0] packet;reg [15:0] pcrc;integer plen;
 wire writable,p_valid,p_short,decoder_fault;
 wire [1:0] p_kind;wire [15:0] p_generation;wire [9:0] p_slot;wire [12:0] p_tag;
 wire [47:0] p_rows;wire [7:0] p_mask,p_am;wire [103:0] p_alt;
 nes_plan_batch206 decoder(.host_clk(host),.nes_clk(clk),.reset(reset_src),.active(run_enable),
  .stop(cancel),.source_fault(fault),.write_valid(put),.write_ready(writable),.write_data(wb),.retire(1'b0),
  .retire_permitted(1'b0),.seal(seal),.seal_length(plen[9:0]),.seal_plans(5'd1),.seal_crc(pcrc),
  .lease_valid(1'b1),.lease_generation(g),.plan_short(p_short),.plan_valid(p_valid),
  .plan_ready(accepted),.tile_done(done),.plan_kind(p_kind),.plan_generation(p_generation),
  .plan_slot(p_slot),.plan_tag(p_tag),.plan_rows(p_rows),.plan_mask(p_mask),.plan_alt_mask(p_am),
  .plan_alt_tags(p_alt),.end_ready(1'b0),.fault(decoder_fault));
 function [15:0] packet_crc;
  integer n,b;reg [15:0] c;begin c=16'hffff;
   for(n=0;n<plen;n++)begin c=c^{packet[n*8+:8],8'd0};for(b=0;b<8;b++)c=c[15]?(c<<1)^16'h1021:c<<1;end
   packet_crc=c;end
 endfunction
 task publish;integer n;begin
  for(n=0;n<plen;n++)begin @(negedge host);wait(writable);@(negedge host);wb=packet[n*8+:8];put=1;
   @(negedge host);put=0;end
  seal=1;@(negedge host);seal=0;wait(p_valid || decoder_fault);
  if(decoder_fault||p_short!==packet[7] || {p_kind,p_generation,p_slot,p_tag,p_rows,p_mask,p_am}!=={kind,g,slot,tag,rows,mask,altmask})
   $fatal(1,"decoded plan mismatch %d %d",g,slot);
 end endtask
