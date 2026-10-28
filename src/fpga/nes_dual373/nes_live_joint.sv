// Original047 joint resource wrapper; RAM service is resource-only.
module nes_live_joint(
output wire out_native_spi_fault,
input wire ext_sink_fault,

output wire native_bg_low,native_bg_high,native_obj_low,native_obj_high,native_obj_valid,
output wire native_extra_sprites,
output wire [7:0] native_obj_attribute,native_obj_x,

output wire [14:0] native_scroll_v,native_scroll_t,
output wire [2:0] native_fine_x,native_pattern_mode,
output wire [7:0] native_display_mask,
output wire [191:0] native_palette,
output wire native_scroll_access,
// Common scene ownership ports follow.


input wire  ext_clk,
input wire CLKIN,
input wire ext_chr32,
input wire  ext_reset,
input wire [15:0] ext_reset_epoch,
input wire  ext_arm,
input wire  ext_immutable_chr,
input wire [23:0] ext_snes_addr,
input wire  ext_read_n,
input wire  ext_write_n,
input wire  ext_romsel_n,
input wire [7:0] ext_snes_data_in,
input wire ext_SPI_SS,ext_SPI_SCK,ext_SPI_MOSI,
output wire out_spi_miso,out_spi_selected,out_spi_fault,
output wire [3:0] out_spi_error,
output wire out_load_ready,out_loaded,out_run_enable,out_boot_fault,
output wire [3:0] out_boot_error,
output wire [18:0] out_loaded_bytes,

inout wire [15:0] ext_psram_data,
output wire [21:0] out_psram_address,
output wire out_psram_1ce,out_psram_2ce,out_psram_oe,out_psram_we,out_psram_bhe,out_psram_ble,
output wire [63:0] out_ppu_fault_state154,
output wire [95:0] out_history157,output wire out_history_enable180,
output wire out_fault_trigger,output wire [63:0] out_fault_context,
output wire out_rom_fault,
output wire [3:0] out_rom_error_code,

input wire [4:0] ext_joypad1,
input wire [4:0] ext_joypad2,
output wire [24:0] out_cpumem_addr,
output wire [21:0] out_ppumem_addr,
output wire  out_cpumem_read,
output wire  out_cpumem_write,
output wire  out_ppumem_read,
output wire  out_ppumem_write,
output wire [7:0] out_cpumem_dout,
output wire [7:0] out_ppumem_dout,
output wire [15:0] out_sample,
output wire [5:0] out_color,
output wire [2:0] out_emphasis,
output wire [8:0] out_cycle,
output wire [8:0] out_scanline,
output wire [1:0] out_joypad_clock,
output wire [2:0] out_joypad_out,
output wire  out_hsync,
output wire  out_vsync,
output wire  out_hblank,
output wire  out_vblank,
output wire [7:0] out_bus_data,
output wire  out_databus_oe_n,
output wire  out_databus_dir,
output wire  out_ready,
output wire  out_busy,
output wire  out_fault,
output wire  out_encoder_fault,
output wire  out_producer_fault,
output wire  out_tap_fault,
output wire [7:0] out_tap_error,
output wire [15:0] out_published
,output wire out_host_locked,output wire out_host_clk,output wire out_observe_reset,out_observe_sample,out_observe_ready
);

wire native_release_frame,native_query;
wire [2:0] native_query_kind;wire [12:0] native_query_index;wire [15:0] native_query_generation;
wire native_frame_owned,native_geometry_valid,native_initialized,native_active,native_response,native_hit,native_scroll_seen;
wire [15:0] native_generation;wire [24:0] native_errors;wire [63:0] native_data;
wire [7:0] native_row_count,native_object_count,native_exception_count;
wire [5:0] native_group_count,native_palette_count;
wire native_fill_slot,native_core_safe;
wire native_mem_ready,native_mem_request,native_mem_response,native_mem_error;
wire [21:0] native_mem_address,native_mem_response_address;wire [7:0] native_mem_data;
wire native_frame_response,native_frame_hit;wire [63:0] native_frame_data;
wire native_frame_query=native_query;
wire [2:0] native_frame_query_kind=native_query_kind;
wire [12:0] native_frame_query_index=native_query_index;
wire [15:0] native_frame_query_generation=native_query_generation;
assign native_response=native_frame_response;assign native_hit=native_frame_hit;
assign native_data=native_hit?native_frame_data:64'd0;
wire source_ready204,source_rom204,source_write204;wire [31:0] source_epoch204;
wire lease204,lease_fault204,export_release204,export_permitted204,retire_permitted204,retire_commit204,reader_drained204;
wire [15:0] captured_gen204,retire_gen204;wire [31:0] captured_epoch204;wire [31:0] display_serial373;wire [2:0] display_raw373;
 wire [15:0] dispatch_gen373;
 wire [31:0] dispatch_epoch373;
 wire [31:0] dispatch_serial373;
wire [3:0] native_export_error;
wire direct_miso204,direct_selected204,direct_fault204,direct_nes_fault204;
wire native_spi_miso,native_spi_selected,native_spi_fault;
wire native_boot_miso,native_boot_selected;
wire guard_allow,guard_fault,external_memory_ready,startup_ready,release_memory;
wire rom_cpu_sample,rom_cpu_valid,rom_ppu_valid,rom_fault;
wire [3:0] rom_error_code;
wire rom_request;wire [21:0] rom_address;
wire ext_host_clk,ext_mem_clk,locked;
 nes_clock_pll123 pll(.areset(ext_reset),.inclk0(CLKIN),.c0(ext_host_clk),.c1(ext_mem_clk),.locked(locked));
 wire queue_clk=ext_clk,clk=ext_clk,host_clk=ext_host_clk,boot_reset=ext_reset||!locked||!external_memory_ready;wire run_enable;wire raw_stop=boot_reset || !run_enable;wire reset_request;
 nes_domain_reset124 init_release(.clk(clk),.raw_reset(raw_stop),.reset(reset_request));
wire memory_ready;wire common_reset=raw_stop || !memory_ready;wire reset;
 nes_domain_reset124 core_release(.clk(clk),.raw_reset(common_reset),.reset(reset));
 wire reset_nes=reset,cold_reset=reset;
wire [15:0] reset_epoch=ext_reset_epoch;
 wire frame_start,frame_end,supported_mode;
 wire [7:0] frame_id;wire [2:0] fine_x;wire chr_32k;
 wire [63:0] palette_snes;
 wire bg_valid;wire signed [8:0] bg_line;wire [8:0] bg_dot;
 wire [14:0] bg_chr_address;wire [1:0] bg_palette;wire [31:0] bg_tick;
 wire frame_ready,encoder_fault;wire [7:0] encoder_error;
 wire desc_valid,desc_ready;wire [15:0] desc_epoch,desc_seq;wire [23:0] desc_base;wire [11:0] desc_length;
 wire mem_req_valid,mem_req_ready,mem_rsp_valid,mem_rsp_ready,mem_rsp_error;
 wire [23:0] mem_req_address,mem_rsp_address;wire [15:0] mem_req_epoch,mem_rsp_epoch;wire [7:0] mem_rsp_data;
 wire [1:0] p_op;wire [15:0] p_epoch,p_seq;wire [11:0] p_length;wire [7:0] p_data;
 wire p_accept,done,producer_fault,exhausted;wire [3:0] p_error;wire [7:0] producer_error;wire [15:0] published;
 wire ready,busy,fault,host_read_owned;wire [3:0] bus_error,frontend_error;wire [127:0] frontend_snapshot;
 wire [23:0] snes_addr=ext_snes_addr;wire read_n=ext_read_n,write_n=ext_write_n,romsel_n=ext_romsel_n;wire [7:0] snes_data_in=ext_snes_data_in;
 wire [7:0] bus_data;wire databus_oe_n,databus_dir;
 wire [7:0] cpumem_din,ppumem_din;
 wire [4:0] joypad1_data=ext_joypad1,joypad2_data=ext_joypad2;
 wire [24:0] cpumem_addr;wire [21:0] ppumem_addr;
 wire cpumem_read,cpumem_write,ppumem_read,ppumem_write;wire [7:0] cpumem_dout,ppumem_dout;
 wire [5:0] color;wire [2:0] emphasis;wire [8:0] cycle,scanline;wire [15:0] sample;
 wire [1:0] joypad_clock;wire [2:0] joypad_out;wire apu_ce,hsync,hblank,vsync,vblank;
 wire tap_ce,tap_bgp,tap_mode,tap_ppu_change,tap_mapper_change;
 wire [2:0] tap_fine;wire [14:0] tap_scroll;wire [95:0] tap_palette;wire [1:0] tap_attribute;
 wire tap_fault;wire [7:0] tap_error;
 wire immutable_chr=ext_immutable_chr;
 
 //137 Admit only initialized supported frames when the encoder is free.
 wire arm=1'b0;
 wire [63:0] ppu_fault_state154;
 assign out_ppu_fault_state154=ppu_fault_state154;
 wire [13:0] native_chr_logical;
 wire [7:0] native_oam_address,native_oam_data,native_nt_data;
 wire [10:0] native_nt_address;
 wire native_oam_write,native_nt_write;
 nes_probe dut(.*);

 assign ready=0;assign busy=0;assign fault=0;assign encoder_fault=0;
 assign producer_fault=0;assign tap_fault=0;assign tap_error=0;assign published=0;

wire [7:0] external_cpu_data,external_ppu_data;
wire load_ready,loaded,boot_fault;wire [3:0] boot_error;wire [18:0] loaded_bytes;
assign out_load_ready=load_ready;
assign out_loaded=loaded;
assign out_run_enable=run_enable;
assign out_boot_fault=boot_fault;
assign out_boot_error=boot_error;
assign out_loaded_bytes=loaded_bytes;
wire mem_clk=ext_mem_clk;
wire rom_ready,rom_response,rom_error;wire [21:0] rom_response_address;wire [7:0] rom_data;
wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;

assign out_psram_address=psram_address;
assign out_psram_1ce=psram_1ce;
assign out_psram_2ce=psram_2ce;
assign out_psram_oe=psram_oe;
assign out_psram_we=psram_we;
assign out_psram_bhe=psram_bhe;
assign out_psram_ble=psram_ble;
assign out_rom_fault=rom_fault;
assign out_rom_error_code=rom_error_code;
// Diagnostic127: actual loader/CHECK/RUN owns the single PSRAM bus.
 
 wire guard_reset=ext_reset||!locked;
 nes_diag_clock_guard127 clock_guard(.mem_clk(mem_clk),.ref_clk(clk),.reset(guard_reset),.allow_memory(guard_allow),.fault(guard_fault));
 nes_domain_reset124 memory_release(.clk(mem_clk),.raw_reset(guard_reset||!guard_allow),.reset(release_memory));
 nes_diag_startup_guard #(.WAIT_CYCLES(33603)) startup(.clk(mem_clk),.reset(release_memory),.ready(startup_ready));
 assign external_memory_ready=guard_allow && !release_memory && startup_ready;
 wire diagnostic_reset;
 nes_domain_reset124 diagnostic_release(.clk(mem_clk),.raw_reset(!external_memory_ready),.reset(diagnostic_reset));
 nes_spi_boot loader_boot(.source_local_reset207(reset),.source_ready204(source_ready204),.source_rom204(source_rom204),
 .source_write204(source_write204),.source_epoch204(source_epoch204),.clk(clk),.mem_clk(mem_clk),.reset(diagnostic_reset),.read_reset(common_reset),
 .SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),
 .spi_miso(native_boot_miso),.spi_selected(native_boot_selected),.spi_fault(out_spi_fault),.spi_error(out_spi_error),
 .load_ready(load_ready),.loaded(loaded),.run_enable(run_enable),.boot_fault(boot_fault),.boot_error(boot_error),.loaded_bytes(loaded_bytes),.rom_chr32(chr_32k),
 .rom_request(native_mem_request),.rom_address(native_mem_address),.rom_ready(native_mem_ready),.rom_response(native_mem_response),.rom_error(native_mem_error),.rom_response_address(native_mem_response_address),.rom_data(native_mem_data),
 .psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),.psram_oe(psram_oe),.psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(ext_psram_data));
 wire rom_cpu_address_valid,rom_ppu_address_valid,game147_prefetch_hint;
 wire [21:0] game148_hint_physical;

 
 

wire game160_restart_hint;
wire [11:0] history_flags157;
//180: passive admission transitions, same 16x96 observer RAM.
wire [24:0] native_observe_errors180;wire native_collecting180;
nes_reject_witness180 witness(
 .clk(clk),.reset(reset),.release_frame(native_release_frame),.collecting(native_collecting180),
 .owned(native_frame_owned),.valid(native_geometry_valid),.generation(native_generation),
 .live_errors(native_observe_errors180),.final_errors(native_errors),
 .scanline(scanline),.dot(cycle),.mask(native_display_mask),
 .rows(native_row_count),.groups(native_group_count),.objects(native_object_count),
 .exceptions(native_exception_count),.palettes(native_palette_count),
 .sample_enable(out_history_enable180),.sample(out_history157));
nes_rom_early rom_service(.native_core_safe(native_core_safe),.history_flags157(history_flags157),
 .ppu_prefetch_valid(game147_prefetch_hint && (game160_restart_hint || rom_ppu_valid || (ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800))),.ppu_prefetch_address(game148_hint_physical),
.fault_trigger(out_fault_trigger),.fault_context(out_fault_context),
.cpu_address_valid(rom_cpu_address_valid),.ppu_address_valid(rom_ppu_address_valid),.clk(clk),.reset(reset),
 .cpumem_addr(cpumem_addr),.cpumem_read(cpumem_read),.cpu_sample(rom_cpu_sample),
 .ppumem_addr(ppumem_addr),.ppumem_read(ppumem_read),.ppu_sample(tap_ce && ppumem_read),
 .cpu_data(external_cpu_data),.ppu_data(external_ppu_data),.cpu_valid(rom_cpu_valid),.ppu_valid(rom_ppu_valid),
 .rom_ready(rom_ready),.rom_request(rom_request),.rom_address(rom_address),
 .rom_response(rom_response),.rom_error(rom_error),.rom_response_address(rom_response_address),.rom_data(rom_data),
 .fault(rom_fault),.error_code(rom_error_code));


nes_local_memory local_memory(
.native_nt_address(native_nt_address),.native_nt_data(native_nt_data),.native_nt_write(native_nt_write),.clk(clk),.reset(reset_request),
 .cpumem_addr(cpumem_addr),.cpumem_write(cpumem_write),.cpumem_dout(cpumem_dout),
 .ppumem_addr(ppumem_addr),.ppumem_write(ppumem_write),.ppumem_dout(ppumem_dout),
 .external_cpu_data(external_cpu_data),.external_ppu_data(external_ppu_data),
 .cpumem_din(cpumem_din),.ppumem_din(ppumem_din),.init_done(memory_ready));



wire waiting267;
wire [2:0] native_patch_count181;
wire source_start_ready267,source_done267,flow_retired267,flow_ack267,flow_fault267,bus_valid267;
wire identity_ready267,plan_fault267,plan_commit267,plan_done267;
wire source_start365,prelease365,capture_begin365,identity_pending267,source_owned365,materialized366;
wire cancel_host267,cancel_nes267;
nes_native_capture365 #(.EARLY_RELEASE(1),.REQUIRED_BITMAP(0)) native_frame(.capture_materialized366(materialized366),.source_owned365(source_owned365),
 .stop(cancel_nes267),.source_start_ready(source_start_ready267),.source_done(source_done267),
 .identity_ready(identity_ready267),.display_ack(flow_ack267),.flow_error(flow_fault267||plan_fault267),
 .source_start(source_start365),.identity_valid(identity_pending267),.prelease(prelease365),
 .source_epoch(source_epoch365),.source_generation(source_generation365),.source_serial(source_serial267),
 .capture_begin(capture_begin365),.source_ready(source_ready204),.source_is_rom(source_rom204),.source_writing(source_write204),.live_epoch(source_epoch204),
 .export_error(native_export_error),.reader_drained(reader_drained204),.retire_commit(retire_commit204),.retire_generation(retire_gen204),
 .effective_release(native_release_frame),.lease_valid(lease204),.retire_permitted(retire_permitted204),.export_permitted(export_permitted204),.waiting_display(waiting267),.lease_fault(lease_fault204),
 .captured_epoch(captured_epoch204),.captured_generation(captured_gen204),.display_serial373(display_serial373),.display_raw373(display_raw373),
 .clk(clk),.reset(reset),.ppu_ce(tap_ce),.rom_fault(rom_fault),
 .color(color),.emphasis(emphasis),.patch_count(native_patch_count181),.patch_errors(),
 .scanline(scanline),.dot(cycle),.bg_low(native_bg_low),.bg_high(native_bg_high),
 .obj_low(native_obj_low),.obj_high(native_obj_high),.obj_valid(native_obj_valid),.extra_sprites(native_extra_sprites),
 .bg_attribute(tap_attribute),.obj_attribute(native_obj_attribute),.obj_x(native_obj_x),
 .ppu_read(ppumem_read),.ppu_valid(rom_ppu_valid),.logical_address(native_chr_logical),.physical_address(ppumem_addr),
 .scroll_v(native_scroll_v),.scroll_t(native_scroll_t),.fine_x(native_fine_x),.pattern_mode(native_pattern_mode),
 .display_mask(native_display_mask),.palette(native_palette),.scroll_access(native_scroll_access),
 .query(native_frame_query),.query_kind(native_frame_query_kind),.query_index(native_frame_query_index),.query_generation(native_frame_query_generation),
 .owned(native_frame_owned),.geometry_valid(native_geometry_valid),.initialized(native_initialized),.active(native_active),
 .observe_errors180(native_observe_errors180),.observe_collecting180(native_collecting180),
 .generation(native_generation),.errors(native_errors),.scroll_seen(native_scroll_seen),.row_count(native_row_count),
 .object_count(native_object_count),.exception_count(native_exception_count),.group_count(native_group_count),.palette_count(native_palette_count),
 .response(native_frame_response),.hit(native_frame_hit),.data(native_frame_data));

assign native_nt_address=0;assign native_oam_address=0;
// Evaluated geometry replaces the old unchanged CIRAM/OAM snapshot requirement.

assign out_cpumem_addr=cpumem_addr;
(* preserve *) reg [21:0] debug_ppu_address;
 always @(posedge clk) debug_ppu_address<=ppumem_addr;
 assign out_ppumem_addr=debug_ppu_address;
assign out_cpumem_read=cpumem_read;
assign out_cpumem_write=cpumem_write;
assign out_ppumem_read=ppumem_read;
assign out_ppumem_write=ppumem_write;
assign out_cpumem_dout=cpumem_dout;
assign out_ppumem_dout=ppumem_dout;
assign out_sample=sample;
assign out_color=color;
assign out_emphasis=emphasis;
assign out_cycle=cycle;
assign out_scanline=scanline;
assign out_joypad_clock=joypad_clock;
assign out_joypad_out=joypad_out;
assign out_hsync=hsync;
assign out_vsync=vsync;
assign out_hblank=hblank;
assign out_vblank=vblank;
assign out_bus_data=bus_data;
assign out_databus_oe_n=databus_oe_n;
assign out_databus_dir=databus_dir;
assign out_ready=ready;
assign out_busy=busy;
assign out_fault=fault;
assign out_encoder_fault=encoder_fault;
assign out_producer_fault=producer_fault;
assign out_tap_fault=tap_fault;
assign out_tap_error=tap_error;
assign out_published=published;
assign out_host_locked=locked;
assign out_host_clk=ext_host_clk;
assign out_observe_reset=reset;
assign out_observe_sample=rom_cpu_sample && rom_cpu_valid && !reset;
wire progress_irq284,progress_mode284,source_mode367;
wire [199:0] source_status270;
assign out_observe_ready=source_mode367?source_status270[0]:progress_mode284?progress_irq284:external_memory_ready;


//267 resource integration: source input commit and final display are distinct.
 wire [31:0] source_epoch365,source_serial267;wire [15:0] source_generation365;
 assign retire_commit204=plan_commit267;
assign retire_gen204=captured_gen204;
assign native_spi_fault=|native_export_error||flow_fault267||plan_fault267;
nes_fault267 retained_fault267(.nes_clk(clk),.host_clk(host_clk),.reset(reset),
 .transport_fault(native_spi_fault||ext_sink_fault),.lease_fault(lease_fault204),.core_fault(rom_fault),
 .spi_fault(plan_fault267),.batch_fault(1'b0),.bulk_fault(flow_fault267),.tile_fault(1'b0),.consume_error(1'b0),.command_error(1'b0),
 .host_fault(direct_fault204),.nes_fault(direct_nes_fault204),.hc(cancel_host267),.nc(cancel_nes267));
assign databus_oe_n=!bus_valid267;assign databus_dir=bus_valid267;
wire tv267,tr267,ev267,er267,ep295;wire [7:0] td267;wire [4:0] ti267;wire [5:0] tl267;wire [1:0] tk267;wire [9:0] ts267;
wire tile_closed267;
wire queue_admit319,plan_admit319,plan_zero319,plan_step319;wire [9:0] plan_cursor319;
wire [113:0] link270;wire [199:0] output_status270,plan_status270;
 wire source_crc270,output_crc270,plan_crc270;
 nes_spi270 spi_front270(.queue_admit319(queue_admit319),.plan_admit319(plan_admit319),.progress_irq284(progress_irq284),.progress_mode284(progress_mode284),.source_mode367(source_mode367),.clk(host_clk),.reset(reset),.SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),
 .source_status(source_status270),.output_status(output_status270),.plan_status(plan_status270),
 .request_crc_enable(source_crc270||plan_crc270),.link(link270));
nes_joint267_board native_joint267(.display_serial373(display_serial373),.display_epoch373(captured_epoch204),.display_generation373(captured_gen204),.display_raw373(display_raw373),.capture_materialized366(materialized366),.queue_admit319(queue_admit319),.plan_cursor319(plan_cursor319),.plan_zero319(plan_zero319),.plan_step319(plan_step319),.link270(link270),.source_status270(source_status270),.output_status270(output_status270),.source_crc270(source_crc270),.output_crc270(output_crc270),.clk(clk),.host_clk(host_clk),.reset(reset),.abort_source(direct_nes_fault204),
 .start(source_start365),.start_ready(source_start_ready267),
 .frame_owned(source_owned365),.geometry_valid(source_owned365),.frame_generation(source_generation365),.content_epoch(source_epoch365),.frame_serial(source_serial267),
 .patch_count(native_patch_count181),.row_count(native_row_count),.object_count(native_object_count),.exception_count(native_exception_count),.group_count(native_group_count),.palette_count(native_palette_count),
 .query(native_query),.query_kind(native_query_kind),.query_index(native_query_index),.query_generation(native_query_generation),.response(native_response),.hit(native_hit),.data(native_data),
 .SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),.selected(native_spi_selected),.miso(native_spi_miso),.done(source_done267),.fault(native_export_error),
 .capture_begin(capture_begin365),.source_ready(source_ready204),.source_is_rom(source_rom204),.source_writing(source_write204),.reader_drained(reader_drained204),
 .release_frame(),.lease_valid(lease204),.waiting_display(waiting267),.lease_fault(lease_fault204),.retired(flow_retired267),.display_ack(flow_ack267),
 .identity_valid(identity_pending267),.identity_ready(identity_ready267),.bank(~display_serial373[0]),
 .address(snes_addr),.read_n(read_n),.write_n(write_n),.data_in(snes_data_in),.data_out(bus_data),.bus_valid(bus_valid267),
 .staged(),.receipt_committed(),.flow_fault(flow_fault267),.tile_closed267(tile_closed267),
 .tile_valid(tv267),.tile_ready(tr267),.tile_data(td267),.tile_index(ti267),.tile_length(tl267),.tile_kind(tk267),.tile_slot(ts267),.tile_generation(dispatch_gen373),
 .end_valid(ev267),.end_partial295(ep295),.end_ready(er267),.end_generation(dispatch_gen373),.ordinary_ready(),.next_token(),
 .sink_ready(1'b1),.sink_valid(),.sink_data(),.sink_kind(),.sink_unit(),.sink_lane(),.stream_ready(),.v_ready(),.v_sealed(),.h_ready(),.context_ready(),.output_phase());
nes_plan_path267 retained_plan267(.prelease361(prelease365),.epoch361(dispatch_epoch373),.serial361(dispatch_serial373),.plan_admit319(plan_admit319),.plan_cursor319(plan_cursor319),.plan_zero319(plan_zero319),.plan_step319(plan_step319),.link270(link270),.status270(plan_status270),.crc_take270(plan_crc270),.clk(clk),.host_clk(host_clk),.reset(reset),.stop(cancel_host267||cancel_nes267),
 .lease(lease204),.retire_permitted(flow_retired267&&retire_permitted204),.retire_commit(plan_commit267),.generation(dispatch_gen373),
 .source_ready(source_ready204),.source_is_rom(source_rom204),.source_writing(source_write204),.captured_epoch(dispatch_epoch373),.live_epoch(source_epoch204),
 .SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),.selected(direct_selected204),.miso(direct_miso204),.tile_closed(tile_closed267),
 .tv(tv267),.tr(tr267),.td(td267),.ti(ti267),.tl(tl267),.tk(tk267),.ts(ts267),.ev(ev267),.ep295(ep295),.er(er267),
 .qualified(native_fill_slot),.core_safe(native_core_safe),.core_request(rom_request),.core_address(rom_address),.core_ready(rom_ready),.core_response(rom_response),.core_data(rom_data),
 .core_error267(rom_error),.core_response_address267(rom_response_address),
 .mem_ready(native_mem_ready),.mem_response(native_mem_response),.mem_error(native_mem_error),.mem_response_address(native_mem_response_address),.mem_data(native_mem_data),
 .mem_request(native_mem_request),.mem_address(native_mem_address),.fault(plan_fault267),.drained(reader_drained204),.retire_done(plan_done267));

wire spi_collision204=(native_boot_selected&&native_spi_selected)||(native_boot_selected&&direct_selected204)||(native_spi_selected&&direct_selected204);
assign out_native_spi_fault=native_spi_fault||direct_fault204||spi_collision204;
assign out_spi_selected=native_boot_selected||native_spi_selected||direct_selected204;
assign out_spi_miso=spi_collision204?1'b0:native_boot_selected?native_boot_miso:native_spi_selected?native_spi_miso:direct_miso204;
assign dispatch_gen373=captured_gen204;
 assign dispatch_epoch373=captured_epoch204;
 assign dispatch_serial373=display_serial373;
 endmodule

