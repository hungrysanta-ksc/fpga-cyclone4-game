"""Build the FF3 CHR-RAM display profile from the same board as the .nes loader."""
import argparse
import shutil
from pathlib import Path
from prepare_nes_ff3_checkpoint import prepare, ROOT
from prepare_nes_kirby1023 import edit

SRAM_PORTS = """output wire [18:0] RAM_ADDR, output wire RAM_OE,RAM_WE, inout wire [7:0] RAM_DATA,"""
READER_PORTS = """output wire chr_req,chr_cancel,output wire [17:0] chr_addr,output wire [15:0] chr_gen,
 input wire chr_ready,chr_idle,chr_reply,chr_error,input wire [7:0] chr_q,
 input wire [17:0] chr_reply_addr,input wire [15:0] chr_reply_gen,"""
READER_MAP = """.chr_req(chr_req),.chr_cancel(chr_cancel),.chr_addr(chr_addr),.chr_gen(chr_gen),
 .chr_ready(chr_ready),.chr_idle(chr_idle),.chr_reply(chr_reply),.chr_error(chr_error),.chr_q(chr_q),
 .chr_reply_addr(chr_reply_addr),.chr_reply_gen(chr_reply_gen),"""

def build(board):
    prepare(board)
    from prepare_ff3_scratch1038 import share_map_scratch
    share_map_scratch(board)
    from prepare_ff3_mixrom1038 import map_mix_rom
    map_mix_rom(board)
    # The extra-sprite prefetch frees two M9Ks for the concurrent
    # accept and return timestamp writers in the 84 MHz host domain.
    from prepare_ff3_rank1043 import pack_rank_row
    pack_rank_row(board)
    shutil.copy2(ROOT/"src/nes/nes_chr_snapshot.sv",board)
    shutil.copy2(ROOT/"src/nes/nes_checkpoint_spi.sv",board)
    with (board/"board.qsf").open("a") as f:
        for name in ("nes_chr_snapshot","nes_checkpoint_memory","nes_checkpoint_spi"):
            f.write(f"\nset_global_assignment -name SYSTEMVERILOG_FILE {name}.sv\n")
    edit(board,"fxpak_nes_screen137_top.sv",
         ("nes_live_joint core(","nes_live_joint core(.RAM_ADDR(RAM_ADDR),.RAM_OE(RAM_OE),.RAM_WE(RAM_WE),.RAM_DATA(RAM_DATA),"),
         ("assign RAM_ADDR=0;assign RAM_OE=1;assign RAM_WE=1;assign RAM_DATA=8'hzz;",""))
    edit(board,"nes_live_joint.sv",
         ("module nes_live_joint(","module nes_live_joint("+SRAM_PORTS),
         ("wire reset_nes=reset,cold_reset=reset;","wire boot_hold;wire reset_nes=reset||boot_hold,cold_reset=reset||boot_hold;"),
         ("nes_probe dut(.*);","""wire hold_core, request_pause,request_load,request_save,stream_done;
 wire [63:0] stream_read,stream_write;wire [25:0] stream_addr;
 wire [7:0] stream_be,state_wdata,state_rdata;wire [24:0] state_address;
 wire state_read,state_write,paused,state_sleep,restored,stream_rnw,stream_ena;
 wire bat_read,bat_write,local_rvalid;wire [12:0] bat_addr;wire [7:0] bat_data;
 reg bat_pending;
 always @(posedge clk)bat_pending<=!reset && bat_read;
 wire lifecycle_idle=!native_active && !native_frame_owned && !lease204 && reader_drained204;
 assign request_pause=hold_core && lifecycle_idle;
 wire state_selected,state_miso;
 nes_checkpoint_spi #(.BOOT_HOLD(1)) state_port(.boot_hold(boot_hold),.clk(clk),.reset(reset),.ss(ext_SPI_SS),.sck(ext_SPI_SCK),.mosi(ext_SPI_MOSI),
 .selected(state_selected),.miso(state_miso),.paused(paused),.sleeping(state_sleep),.restored(restored),
 .drained(lifecycle_idle),.hold_core(hold_core),.save(request_save),.load(request_load),
 .stream_ena(stream_ena),.stream_rnw(stream_rnw),.stream_addr(stream_addr),.stream_write(stream_write),
 .stream_be(stream_be),.stream_done(stream_done),.stream_read(stream_read),.bat_read(bat_read),.bat_write(bat_write),
 .bat_addr(bat_addr),.bat_data(bat_data),.bat_valid(bat_pending && local_rvalid),.bat_q(state_rdata));
 nes_probe dut(.*);"""),
         ("nes_local_memory local_memory(","""wire [12:0] scan_addr;wire [7:0] scan_q;wire chr_changed;
 nes_checkpoint_memory #(.DEVICE_CHR(1)) local_memory(.chr_scan_address(scan_addr),.chr_scan_data(scan_q),.chr_changed(chr_changed),
 .paused(paused||boot_hold),.state_address((bat_read||bat_write)?{12'h1e0,bat_addr}:state_address),
 .state_read(state_read||bat_read),.state_write(state_write||bat_write),
 .state_wdata(bat_write?bat_data:state_wdata),.state_rvalid(local_rvalid),.state_rdata(state_rdata),"""),
         (".ppu_valid(rom_ppu_valid),\n .rom_ready", ".ppu_valid(),\n .rom_ready"),
         ("nes_rom_early rom_service(", """assign rom_ppu_valid=memory_ready && ppumem_addr[21:13]==9'h100;
 nes_rom_early rom_service("""),
         ("wire capture_begin611;","""wire capture_begin611,snapshot_ready,snapshot_conflict;
 wire chr_req,chr_cancel,chr_ready,chr_idle,chr_reply,chr_error;
 wire [17:0] chr_addr,chr_reply_addr;wire [15:0] chr_gen,chr_reply_gen;
 wire [7:0] chr_q,sram_data;wire sram_drive;
 assign RAM_DATA=sram_drive?sram_data:8'hzz;
 nes_chr_snapshot snapshot(.clk(clk),.reset(reset),.changed(chr_changed),.start(capture_begin611),
 .collecting(native_active),.discard(native_release_frame && (!native_geometry_valid || native_export_error!=0)),
 .retire(retire_commit204 && retire_permitted204),.start_gen(native_generation+16'd1),.retire_gen(retire_gen204),
 .can_start(snapshot_ready),.conflict(snapshot_conflict),.scan_addr(scan_addr),.scan_data(scan_q),
 .read_req(chr_req),.cancel(chr_cancel),.read_addr(chr_addr),.read_gen(chr_gen),.ready(chr_ready),.idle(chr_idle),
 .response(chr_reply),.error(chr_error),.data(chr_q),.reply_addr(chr_reply_addr),.reply_gen(chr_reply_gen),
 .ram_addr(RAM_ADDR),.oe_n(RAM_OE),.we_n(RAM_WE),.drive_data(sram_drive),.write_data(sram_data),.ram_q(RAM_DATA));"""),
         ("nes_native_capture201 native_frame(","nes_native_capture201 native_frame(.snapshot_conflict(snapshot_conflict),"),
         (".ppu_ce(tap_ce),.rom_fault(rom_fault)",".ppu_ce(tap_ce && (scanline!=7 || cycle!=257 || (snapshot_ready && !hold_core))),.rom_fault(rom_fault)"),
         ("assign out_spi_selected=native_boot_selected", "assign out_spi_selected=state_selected||native_boot_selected"),
         ("assign out_spi_miso=spi_collision204?1'b0:", "assign out_spi_miso=state_selected?state_miso:spi_collision204?1'b0:"),
         ("nes_direct206 direct_path(","nes_direct206 direct_path("+READER_MAP))
    # Only CPU PRG reads use PSRAM. Pattern reads use the real MMC3 translation
    # and the live synchronous RAM; OBJ/BG output consumes the frozen SRAM copy.
    edit(board,"nes_rom_service.sv",
         ("wire ppu_rom=ppumem_addr>=22'h200000 && ppumem_addr<22'h240000;","wire ppu_rom=1'b0;"),
         ("ppu_prefetch_valid &&","1'b0 &&"))
    edit(board,"nes_native_capture201.sv",("module nes_native_capture201(","module nes_native_capture201(input wire snapshot_conflict,"))
    edit(board,"nes_native_frame201.sv",("parameter TILE_QUERY=1)(","parameter TILE_QUERY=1)(input wire snapshot_conflict,"),
         ("geometry_valid<=patch_generation","geometry_valid<=!snapshot_conflict && patch_generation"))
    edit(board,"nes_direct206.sv",("module nes_direct206(","module nes_direct206("+READER_PORTS),
         (" source(.page963"," source("+READER_MAP+".page963"))
    path=board/"nes_source_tile192.sv"
    source=path.read_text().replace(" input wire hint,", " "+READER_PORTS+"\n input wire hint,",1)
    header=source[:source.index(" wire immutable=")]
    start=source.index(" nes_tile205 #")
    tile=source[start:source.index(" wire shared_reply;",start)]
    tile=tile.replace(".plan_short(plan_short)",".plan_short(1'b0)").replace(".lease_valid(lease&&!fault)",".lease_valid(lease)")
    for old,new in (("tile_idle","chr_idle"),("tile_ready","chr_ready"),("tile_request","chr_req"),
                    ("tile_cancel","chr_cancel"),("tile_address","chr_addr"),("tile_generation","chr_gen"),
                    ("tile_response","chr_reply"),("tile_error||reply_address[21:18]!=4'h8","chr_error"),
                    ("reply_address[17:0]","chr_reply_addr"),("reply_generation","chr_reply_gen"),
                    ("reply_data","chr_q"),("pair_hi","8'd0"),("arb_response","1'b0")):
        tile=tile.replace(old,new)
    path.write_text(header+"""wire lease=frame_owned && geometry_valid && source_ready && !source_writing
                    && captured_epoch==live_epoch;
 wire ready_internal,tile_fault;
 assign fault=tile_fault || (plan_valid && !lease);
 assign plan_ready=ready_internal && !fault;
 assign hint_ready=1;assign cap_ready=1;assign cap_sample_ready=1;assign drained=chr_idle;
 always @(posedge clk) evt905<=reset||stop?0:{done,chr_req&&chr_ready,chr_req};
 assign mem_request=core_request;assign mem_address=core_address;assign core_ready=mem_ready;
 assign core_response=mem_response;assign core_error=mem_error;
 assign core_response_address=mem_response_address;assign core_data=mem_data;
"""+tile+"endmodule\n")
    # The hint mailbox fed only the removed ROM prefetch engine. Its
    # source and destination are both absent in this SRAM profile.
    p=board/"board.sdc"
    p.write_text("".join(line for line in p.read_text().splitlines(keepends=True)
                         if "nes_native_mailbox206:page_mail963" not in line))
    # The paired immutable-CHR PSRAM lane had one consumer. This profile
    # reads individual planes from SRAM and the reader no longer exports it.
    code=(board/"nes_rom_physical.sv").read_text()
    start=code.index(" (* preserve *) reg [7:0] bg_hold;")
    last="always @(posedge clk)bg_word<=bg_hold;"
    end=code.index(last,start)+len(last)
    (board/"nes_rom_physical.sv").write_text(code[:start]+" assign bg_word=8'd0;\n "+code[end:])
    code=p.read_text()
    start=code.index("# The sampled pair is held")
    end=code.index("\n}",start)+2
    assert "bg_hold[%d]" in code[start:end] and "bg_word[%d]" in code[start:end]
    p.write_text(code[:start]+code[end:])

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("board",type=Path)
    build(p.parse_args().board)
