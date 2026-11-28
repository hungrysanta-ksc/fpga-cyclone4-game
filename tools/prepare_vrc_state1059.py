"""Fit the CHR-ROM VRC4 renderer with the pause, snapshot and quick-menu endpoint."""
from shutil import copy2, copytree
from prepare_cart_state1059 import BASE, OUT, edit


def prepare():
    src=BASE/"board-7"
    dst=OUT/"board-21"
    copytree(BASE/"board-21",dst,dirs_exist_ok=True)
    for name in ("nes_probe.sv","nes_checkpoint_memory.sv","nes_checkpoint_spi.sv",
                 "nes_menu_reply.sv","nes_screen_status151.sv","nes_sink_bridge165.sv",
                 "nes_sink_bus165.sv","sink-program.hex","rtl/nes.v","rtl/ppu.sv","rtl/apu.sv",
                 "rtl/savestates.vhd","rtl/t65/T65.vhd"):
        copy2(src/name,dst/name)
    edit(dst,"nes_probe.sv",("64'h8007","64'h0015"),("21'h07ffff","21'h03ffff"),("20'h01fff","20'h3ffff"))
    edit(dst/"rtl","nes.v",("prg_write && prg_addr[15];",
         "prg_write && (prg_addr[15:12]==9 || (prg_addr[15:12]>=11 && prg_addr[15:12]<=14));"),
         ("(Savestate_RAMType == 0) ? Savestate_OAMReadData", "(Savestate_RAMType == 2) ? 8'd0 : (Savestate_RAMType == 0) ? Savestate_OAMReadData"))
    edit(dst/"rtl","ppu.sv",("earlynormal707=re_sr[1] && !re_sr[2] && scanline<240",
         "earlynormal707=re_sr[1] && !re_sr[2] && in_rendering_frame"),
         ("restart160 = !re_sr[2] && scanline<240","restart160 = !re_sr[2] && in_rendering_frame"),
         ("assign game160_restart_hint=restart160 || (earlynormal707 && normal155);",
          "assign game160_restart_hint=restart160 || (earlynormal707 && normal155) || (is_pre_render_line && normal155 && cycle[2:0]==3);"))
    joint=(src/"nes_live_joint.sv").read_text()
    control=joint[joint.index(" wire hold_core"):joint.index(" nes_probe dut")]
    edit(dst,"nes_live_joint.sv",("wire reset_nes=reset,cold_reset=reset;",
         "wire boot_hold;wire reset_nes=reset||boot_hold,cold_reset=reset||boot_hold;"),
         (" nes_probe dut",control+" nes_probe dut"),
         ("nes_local_memory local_memory(", """nes_checkpoint_memory #(.CHR_RAM(0)) local_memory(.chr_scan_address(13'd0),
 .paused(paused||boot_hold),.state_address((bat_read||bat_write)?{12'h1e0,bat_addr}:state_address),
 .state_read(state_read||bat_read),.state_write(state_write||bat_write),
 .state_wdata(bat_write?bat_data:state_wdata),.state_rvalid(local_rvalid),.state_rdata(state_rdata),"""),
         (".ppu_ce(tap_ce),.rom_fault",".ppu_ce(tap_ce && (scanline!=7 || cycle!=257 || !hold_core)),.rom_fault"),
         ("out_spi_selected=native_boot_selected","out_spi_selected=state_selected||native_boot_selected"),
         ("out_spi_miso=spi_collision204","out_spi_miso=state_selected?state_miso:spi_collision204"))
    edit(dst,"fxpak_nes_screen137_top.sv",("nes_screen_status151 screen_status(","wire [7:0] menu_status;\n nes_screen_status151 screen_status(.menu_status(menu_status),"),
         ("nes_sink_bridge165 sink(","nes_sink_bridge165 sink(.menu_status(menu_status),"))
    with (dst/"board.qsf").open("a") as stream:
        for name in ("nes_checkpoint_memory","nes_checkpoint_spi","nes_menu_reply"):
            stream.write(f"\nset_global_assignment -name SYSTEMVERILOG_FILE {name}.sv\n")
    pins=""".state_write(SaveStateBus_load && SaveStateBus_wren),
 .state_reg(SaveStateBus_Adr),.state_lane(Savestate_MAPRAMAddr[2:0]),
 .state_word(SaveStateBus_Din),.state_byte(SaveStateBus_Dout[7:0]),"""
    edit(dst,"cart_nrom.sv",(" cartridge("," cartridge("+pins),
         ("SaveStateBus_Dout,Savestate_MAPRAMReadData}","SaveStateBus_Dout[63:8],Savestate_MAPRAMReadData}"),
         ("input wire clk, reset, ce,", """input wire state_write,input wire [9:0] state_reg,input wire [2:0] state_lane,
 input wire [63:0] state_word,output wire [7:0] state_byte,
 input wire clk, reset, ce,"""),
         ("integer i;", """wire [63:0] vrc_control={22'd0,pending,cycle_mode,after_ack,enabled,prescaler,counter,reload_value,mirror,swap,bank1,bank0};
 wire [7:0] byte_out=state_reg==32 ? vrc_control[8*state_lane +: 8] : {1'b0,patterns[state_lane]};
 assign state_byte=(state_reg==32 || state_reg==33) ? byte_out : 8'd0;
 integer i;"""),
         ("end else if(ce) begin","""end else if(state_write && state_reg==32)begin
       {pending,cycle_mode,after_ack,enabled,prescaler,counter,reload_value,mirror,swap,bank1,bank0}<=state_word[41:0];
     end else if(state_write && state_reg==33)begin
       for(i=0;i<8;i=i+1)patterns[i]<=state_word[8*i +: 7];
     end else if(ce) begin"""))
    # Share compact map/rank RAM with the checkpoint profiles. Rank is read
    # on the plane assembler edge preceding its registered fetch event.
    copy2(src/"nes_native_compact181.sv",dst/"nes_native_compact181.sv")
    edit(dst,"nes_native_planes165.sv",("output reg event_valid","output wire [2:0] next_rank,output reg event_valid"),
         ("endmodule","assign next_rank=rank;\nendmodule"))
    edit(dst,"nes_native_frame201.sv",(".event_valid(fetch_event),.event_data(fetch_data),.response(fetch_response)",
         ".next_rank(next_rank),.event_valid(fetch_event),.event_data(fetch_data),.response(fetch_response)"),
         ("wire [1:0] required_kind","wire [2:0] next_rank;wire [1:0] required_kind"),
         (".event_valid(fetch_event),.event_data(fetch_data),.query(", ".blank_no_fetch(1'b0),.next_rank(next_rank),.event_valid(fetch_event),.event_data(fetch_data),.query("))
    # Demand reads retain the existing generation, address and lease checks.
    # Drop speculative fill on this immutable cartridge to budget the menu.
    tile=dst/"nes_source_tile192.sv"
    source=tile.read_text().replace("parameter integer USE_CACHE=1","parameter integer USE_CACHE=0")
    a=source.index(" wire invalidate=")
    b=source.index(" nes_native_arbiter165",a)
    tile.write_text(source[:a]+""" wire invalidate=arb_abort||!lease||cap_release||fault;
 assign cap_ready=!reset && !stop;
 assign cap_sample_ready=1'b0;
 assign hint_ready=!reset && !stop;
 assign shared_req=arb_request;
 assign shared_address=arb_address;
 assign arb_ready=shared_ready;
 assign arb_response=shared_reply;
 assign arb_data=actual_lo;
 assign pair_hi=bg_word;
 assign arb_reply_address=actual_address;
 assign arb_reply_generation=actual_generation;
"""+source[b:])
    top=dst/"nes_direct206.sv"
    body=top.read_text()
    a=body.index(" nes_native_mailbox206 #(.WIDTH(27)")
    b=body.index(" nes_plan_spi200 endpoint",a)
    top.write_text((body[:a]+body[b:]).replace("page_dst963 && payload_dst963[26:11]==captured_generation","1'b0").replace("payload_dst963[10:0]","11'd0"))
    sdc=dst/"board.sdc"
    lines=sdc.read_text().splitlines(keepends=True)
    sdc.write_text("".join(line for line in lines if ":page_mail963|" not in line))
if __name__=="__main__": prepare()
