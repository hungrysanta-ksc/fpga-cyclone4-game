// SPDX-License-Identifier: MIT
// Production board join: SPI plans -> source192/core-priority reader -> bulk193
// -> SNES descriptor/control/aperture. Only final C/SNES ACK permits EA retire.
module nes_direct204(
 input wire nes_clk,host_clk,reset,transport_fault,
 input wire lease_valid,lease_fault,retire_permitted,
 input wire [15:0] captured_generation,input wire [31:0] captured_epoch,live_epoch,
 input wire source_ready,source_is_rom,source_writing,
 output wire reader_drained,retire_commit,output wire [15:0] retire_generation,
 input wire core_fault,qualified_slot,core_safe,core_request,input wire [21:0] core_address,
 output wire core_ready,core_response,core_error,output wire [21:0] core_response_address,output wire [7:0] core_data,
 input wire mem_ready,mem_response,mem_error,input wire [21:0] mem_response_address,input wire [7:0] mem_data,
 output wire mem_request,output wire [21:0] mem_address,
 input wire SPI_SS,SPI_SCK,SPI_MOSI,output wire spi_selected,spi_miso,
 input wire [23:0] address,input wire read_n,write_n,input wire [7:0] data_in,
 output wire [7:0] data_out,output wire oe_n,dir,
 output wire host_fault,nes_fault
);
 wire spi_fault,batch_fault,bulk_fault,tile_fault,consume_error,command_error;
 reg hf,nf;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] n_to_h,h_to_n,errors_h;
 // Latch before feeding cancellation back. No combinational fault/reset loop.
 always @(posedge host_clk or posedge reset)begin
  if(reset)begin hf<=0;n_to_h<=0;errors_h<=0;end
  else begin
   n_to_h<={n_to_h[0],nf};errors_h<={errors_h[0],transport_fault||spi_fault||batch_fault||bulk_fault||consume_error||command_error};
   if(n_to_h[1]||errors_h[1])hf<=1;
  end
 end
 always @(posedge nes_clk or posedge reset)begin
  if(reset)begin nf<=0;h_to_n<=0;end
  else begin h_to_n<={h_to_n[0],hf};if(h_to_n[1]||lease_fault||tile_fault||core_fault)nf<=1;end
 end
 assign host_fault=hf;assign nes_fault=nf;
 wire cancel=hf||nf;
 wire pw,pr,ps,pi,pv,ev,er,rf,rd,end_sealed;
 wire [7:0] pd;wire [9:0] pl;wire [4:0] pn;wire [15:0] pc,eg,sg;
 wire [1:0] pk,tk;wire [15:0] pg,tg;wire [9:0] slot,ts;wire [12:0] tag;
 wire [47:0] rows;wire [7:0] mask,altmask;wire [103:0] tags;
 wire tr,td,tv,otready;wire [7:0] pixels;wire [4:0] ti;wire [5:0] tl;
 wire chunk_ready,chunk_kind,consume;wire [11:0] chunk_length;wire [9:0] chunk_slot;
 wire [15:0] chunk_generation;wire [31:0] chunk_token,consume_token;
 wire [7:0] aperture_data,control_data;wire aperture_oe,aperture_dir,control_oe,control_dir;
 nes_plan_spi200 endpoint(.clk(host_clk),.reset(reset),.enable(1'b1),.stop(1'b0),.source_fault(cancel),
  .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.selected(spi_selected),.miso(spi_miso),.fault(spi_fault),
  .plan_idle(pi),.plan_ready(pr),.plan_write(pw),.plan_data(pd),.plan_seal(ps),.plan_length(pl),.plan_plans(pn),.plan_crc(pc),
  .retire_done(rd),.retire(rf),.end_generation(sg),.chunk_ready(chunk_ready),.chunk_kind(chunk_kind),.chunk_length(chunk_length),
  .chunk_slot(chunk_slot),.chunk_generation(chunk_generation),.chunk_token(chunk_token),.end_sealed(end_sealed));
 nes_plan_batch201 transport(.host_clk(host_clk),.nes_clk(nes_clk),.reset(reset),.active(1'b1),.stop(1'b0),.source_fault(cancel),
  .write_valid(pw),.write_ready(pr),.write_data(pd),.retire(rf),.retire_done(rd),
  .retire_permitted(retire_permitted),.retire_commit(retire_commit),.seal(ps),.seal_length(pl),.seal_plans(pn),.seal_crc(pc),
  .host_idle(pi),.fault(batch_fault),.lease_valid(lease_valid),.lease_generation(captured_generation),
  .plan_valid(pv),.plan_ready(tr),.tile_done(td),.plan_kind(pk),.plan_generation(pg),.plan_slot(slot),.plan_tag(tag),
  .plan_rows(rows),.plan_mask(mask),.plan_alt_mask(altmask),.plan_alt_tags(tags),
  .end_valid(ev),.end_ready(er),.end_generation(eg));
 assign retire_generation=eg;
 nes_source_tile192 #(.EXTERNAL_PLAN(1)) source(.clk(nes_clk),.reset(reset),.stop(cancel),
  .frame_owned(lease_valid),.geometry_valid(lease_valid),.frame_generation(captured_generation),
  .source_ready(source_ready),.source_is_rom(source_is_rom),.source_writing(source_writing),.captured_epoch(captured_epoch),.live_epoch(live_epoch),
  .plan_valid(pv),.plan_ready(tr),.plan_kind(pk),.plan_generation(pg),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(altmask),.plan_alt_tags(tags),
  .qualified_slot(qualified_slot),.core_safe(core_safe),.core_request(core_request),.core_address(core_address),
  .core_ready(core_ready),.core_response(core_response),.core_error(core_error),.core_response_address(core_response_address),.core_data(core_data),
  .mem_ready(mem_ready),.mem_response(mem_response),.mem_error(mem_error),.mem_response_address(mem_response_address),.mem_data(mem_data),.mem_request(mem_request),.mem_address(mem_address),
  .out_valid(tv),.out_ready(otready),.out_data(pixels),.out_index(ti),.out_length(tl),.out_kind(tk),.out_slot(ts),.out_generation(tg),
  .busy(),.done(td),.fault(tile_fault),.drained(reader_drained));
 nes_tile_bulk193 bulk(.nes_clk(nes_clk),.host_clk(host_clk),.reset(reset),.active(1'b1),.stop(1'b0),.source_fault(cancel),
  .tile_valid(tv),.tile_ready(otready),.tile_data(pixels),.tile_index(ti),.tile_length(tl),.tile_kind(tk),.tile_slot(ts),.tile_generation(tg),
  .end_valid(ev),.end_ready(er),.end_generation(eg),.token_seed(32'd1),
  .chunk_ready(chunk_ready),.chunk_length(chunk_length),.chunk_token(chunk_token),.chunk_kind(chunk_kind),.chunk_slot(chunk_slot),.chunk_generation(chunk_generation),
  .consume(consume),.consume_token(consume_token),.consume_error(consume_error),.address(address),.read_n(read_n),.write_n(write_n),
  .data_out(aperture_data),.oe_n(aperture_oe),.dir(aperture_dir),.fault(bulk_fault),.end_sealed(end_sealed),.sealed_generation(sg));
 nes_bulk_control194 control(.clk(host_clk),.reset(reset),.active(1'b1),.stop(cancel),.fault(1'b0),
  .chunk_ready(chunk_ready),.chunk_kind(chunk_kind),.chunk_length(chunk_length),.chunk_slot(chunk_slot),.chunk_generation(chunk_generation),.chunk_token(chunk_token),
  .address(address),.read_n(read_n),.write_n(write_n),.data_in(data_in),.data_out(control_data),.oe_n(control_oe),.dir(control_dir),
  .consume(consume),.consume_token(consume_token),.command_error(command_error));
 // Disjoint6040..6050 and400800..400fff owners; release on any collision.
 assign oe_n=reset||cancel||(aperture_oe==control_oe);
 assign dir=!oe_n&&(aperture_oe?control_dir:aperture_dir);
 assign data_out=aperture_oe?control_data:aperture_data;
endmodule
