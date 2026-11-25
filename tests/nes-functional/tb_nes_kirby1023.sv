// Replay the final ARM's encoded plans through the board decoder and tile engine.
`timescale 1ns/1ps
module tb_nes_kirby1023;
 reg host_clk=0, nes_clk=0, reset=1, stop=0;
 always #6 host_clk=~host_clk;
 always #19 nes_clk=~nes_clk;
 reg write_valid=0,seal=0;
 reg [7:0] write_data;
 reg [15:0] gen,crc;
 reg [9:0] length;
 wire write_ready,plan_valid,plan_ready,shortform,done,fault,tile_fault;
 wire [1:0] kind;
 wire [9:0] slot;
 wire [13:0] tag;
 wire [15:0] generation;
 wire [47:0] rows;
 wire [7:0] mask,alt_mask;
 wire [111:0] alt;
 wire [4:0] index;
 wire [2:0] next_alt;
 nes_plan_batch206 decoder(.host_clk(host_clk),.nes_clk(nes_clk),.reset(reset),.stop(stop),.active(1'b1),
  .source_fault(1'b0),.write_valid(write_valid),.write_ready(write_ready),.write_data(write_data),
  .retire(1'b0),.retire_permitted(1'b1),.seal(seal),.seal_length(length),.seal_plans(5'd1),.seal_crc(crc),
  .fault(fault),.lease_valid(1'b1),.lease_generation(gen),.plan_short(shortform),.plan_valid(plan_valid),
  .plan_ready(plan_ready),.tile_done(done),.plan_kind(kind),.plan_generation(generation),.plan_slot(slot),
  .plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(alt_mask),.plan_alt_tags(alt),
  .next_alt_row(next_alt),.end_ready(1'b1),.hint_ready(1'b1));
 wire request,cancel,valid;
 wire [17:0] address;
 wire [7:0] data;
 reg [7:0] rom[0:262143],lo,hi;
 reg [17:0] reply_addr;
 reg reply=0,corrupt=0;
 always @(posedge nes_clk)begin
  reply<=request && !cancel;
  if(request)begin reply_addr<=address^(corrupt?18'h20000:0);lo<=rom[address];hi<=rom[address|8];end
 end
 nes_tile205 #(.EXTERNAL_PLAN(1)) tile(.clk(nes_clk),.reset(reset),.stop(stop),.lease_valid(1'b1),.lease_generation(gen),
  .plan_short(shortform),.plan_valid(plan_valid),.plan_ready(plan_ready),.plan_kind(kind),.plan_generation(generation),
  .plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(alt_mask),.plan_alt_tags(alt),
  .mem_idle(!reply),.mem_ready(1'b1),.mem_request(request),.mem_cancel(cancel),.mem_address(address),
  .mem_response(reply),.mem_error(1'b0),.response_address(reply_addr),.response_generation(gen),.from_rom(1'b1),
  .second_plane(hi),.response_data(lo),.out_valid(valid),.out_ready(1'b1),.out_data(data),.out_index(index),.fault(tile_fault),.done(done));
 // Same one-cycle lookahead as the board source port.
 wire [3:0] next_index=valid ? index[3:0]+1'b1 : index[3:0]; assign next_alt=next_index[3:1];
 integer inp,outp,frame,n,g,value,rc,count=0,high_reads=0;
 reg [7:0] bytes_in[0:31];
 task send;
  begin
   for(integer j=0;j<n;j++)begin
    @(negedge host_clk);while(!write_ready)@(negedge host_clk);
    write_valid=1;write_data=bytes_in[j];
   end
   @(negedge host_clk);write_valid=0;seal=1;
   @(negedge host_clk);seal=0;
  end
 endtask
 always @(posedge nes_clk)begin
  if(request && address[17])high_reads++;
  if(valid && !stop && !corrupt)$fwrite(outp,"%0d %0d %0d %0d %02h\n",frame,kind,slot,index,data);
 end
 initial begin
  $readmemh("chr.hex",rom);
  inp=$fopen("plans.txt","r");outp=$fopen("tiles.txt","w");if(!inp||!outp)$fatal;
  repeat(4)@(negedge nes_clk);reset=0;
  while($fscanf(inp,"%d %d %d %h",frame,g,n,crc)==4)begin
   gen=g;length=n;
   for(integer j=0;j<n;j++)begin rc=$fscanf(inp,"%h",value);if(rc!=1)$fatal;bytes_in[j]=value;end
   send();wait(done||fault||tile_fault);if(!done || fault || tile_fault)$fatal(1,"plan %0d",count);
   @(negedge nes_clk);count++;
  end
  if(!count || !high_reads)$fatal;
  $fclose(outp);
  // Repeat the final nonzero descriptor and inject a sibling-bank response.
  corrupt=1;send();wait(tile_fault);if(!cancel||valid)$fatal;
  @(negedge nes_clk);stop=1;repeat(3)@(negedge nes_clk);
  if(request||valid||tile_fault||!cancel)$fatal;
  stop=0;corrupt=0;send();wait(request);@(negedge nes_clk);stop=1;#1;
  if(!cancel||request||valid)$fatal;
  $display("PASS1023 tiles=%0d upper_reads=%0d wrong_bank_rejected STOP",count,high_reads);$finish;
 end
 initial begin #20000000;$fatal(1,"timeout frame=%d count=%d",frame,count);end
endmodule
