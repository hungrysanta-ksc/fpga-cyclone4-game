"""Prepare a dedicated FF3 CPU/PPU/mapper checkpoint test using the MMC1035 sources."""
from pathlib import Path
import shutil
from prepare_nes_kirby1023 import edit
from prepare_ff3_oam1037 import share_oam
from prepare_ff3_direct1039 import direct_state
from prepare_ff3_alu1041 import bind_cpu
from prepare_ff3_core1040 import bind as bind_core_state

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / "probes" / "nes-kirby1035"
OUT = BASE.parent / "nes-ff3-checkpoint"


def prepare(board, cpu_writer=bind_cpu):
    shutil.copytree(BASE/"board-times",board)
    share_oam(board)
    # The core restores no fields from these reserved bits. Drive them
    # explicitly so the physical-word CRC and the file stream are deterministic.
    edit(board/"rtl","ppu.sv",("assign SS_PPU_BACK[57:50] = vram_a_byte;",
         "assign SS_PPU_BACK[49:47] = 3'b0;\nassign SS_PPU_BACK[57:50] = vram_a_byte;"),
         ("assign SS_vram_BACK[52:51] = write_shift;",
          "assign SS_vram_BACK[54:53] = 2'b0;\nassign SS_vram_BACK[50:35] = 16'd0;\nassign SS_vram_BACK[52:51] = write_shift;"))
    shutil.copy2(ROOT/"src/nes/nes_checkpoint_memory.sv",board)
    edit(board,"nes_probe.sv",
         ("module nes_probe(", """module nes_probe(
 input wire request_pause, request_save, request_load,
 output wire paused, state_sleep, restored,
 output wire [24:0] state_address, output wire state_read,state_write,
 output wire [7:0] state_wdata, input wire [7:0] state_rdata,
 output wire [63:0] stream_write, input wire [63:0] stream_read,
 output wire [25:0] stream_addr, output wire stream_rnw, stream_ena,
 output wire [7:0] stream_be, input wire stream_done,"""),
         (".pausecore('0)",".pausecore(request_pause || state_sleep)"),
         (".corepaused()",".corepaused(paused)"),
         (".save_state('0)",".save_state(request_save)"),
         (".load_state('0)",".load_state(request_load)"),
         (".sleep_savestate()",".sleep_savestate(state_sleep)"),
         (".state_loaded()",".state_loaded(restored)"),
         (".mapper_flags(64'd4)",".mapper_flags(64'h8004)"),
         (".chr_mask(20'h3ffff)",".chr_mask(20'h01fff)"),
         (".Savestate_SDRAMAddr()",".Savestate_SDRAMAddr(state_address)"),
         (".Savestate_SDRAMRdEn()",".Savestate_SDRAMRdEn(state_read)"),
         (".Savestate_SDRAMWrEn()",".Savestate_SDRAMWrEn(state_write)"),
         (".Savestate_SDRAMWriteData()",".Savestate_SDRAMWriteData(state_wdata)"),
         (".Savestate_SDRAMReadData('0)",".Savestate_SDRAMReadData(state_rdata)"),
         (".SAVE_out_Din()",".SAVE_out_Din(stream_write)"),(".SAVE_out_Dout('0)",".SAVE_out_Dout(stream_read)"),
         (".SAVE_out_Adr()",".SAVE_out_Adr(stream_addr)"),(".SAVE_out_rnw()",".SAVE_out_rnw(stream_rnw)"),
         (".SAVE_out_ena()",".SAVE_out_ena(stream_ena)"),(".SAVE_out_be()",".SAVE_out_be(stream_be)"),
         (".SAVE_out_done('0)",".SAVE_out_done(stream_done)"))
    edit(board,"cart_nrom.sv",(".flags(32'd4)",".flags(flags[31:0])"),
         (".SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),.SaveStateBus_rst(1'b0),.SaveStateBus_load(1'b0),.SaveStateBus_Dout(ignored_state)",
          ".SaveStateBus_Din(SaveStateBus_Din),.SaveStateBus_Adr(SaveStateBus_Adr),.SaveStateBus_wren(SaveStateBus_wren),.SaveStateBus_rst(SaveStateBus_rst),.SaveStateBus_load(SaveStateBus_load),.SaveStateBus_Dout(ignored_state)"),
         ("assign SaveStateBus_Dout = '0;","assign SaveStateBus_Dout = ignored_state;"),
         ("assign has_savestate = '0;","assign has_savestate = ignored_flags[3];"))
    direct_state(board)
    state_engine=board/"rtl/savestates.vhd"
    entity, marker, _ = state_engine.read_text().partition("architecture arch of savestates is")
    assert marker
    state_engine.write_text(entity+(ROOT/"src/nes/ff3_checkpoint_walk.vhd").read_text())
    # Align CPU, PPU and external bus dividers at cold release. The native
    # pause handshake samples a particular phase of all three simultaneously.
    edit(board/"rtl","nes.v",
         ("reg [1:0] last_sys_type;", "reg [1:0] last_sys_type;\nreg was_cold;"),
         ("last_sys_type <= sys_type;", "was_cold <= cold_reset;\n\tlast_sys_type <= sys_type;"),
         ("if (last_sys_type != sys_type) begin",
          "if ((was_cold && !cold_reset) || last_sys_type != sys_type) begin"))
    # The checkpoint engine pulses reset_ss while the machine is paused.
    # Release T65's two-stage reset synchronizer under the load handshake.
    # Otherwise the first two real CPU enables after resume replay saved
    # microcycles as resets and the next opcode fetch diverges.
    edit(board/"rtl"/"t65","T65.vhd",
         ("elsif Clk'event and Clk = '1' and Enable = '1' then\n      Res_n_i <= Res_n_d;",
          "elsif rising_edge(Clk) and (Enable = '1' or SaveStateBus_load = '1') then\n      Res_n_i <= Res_n_d;"))
    for name in ("nes_rom_loader","nes_rom_boot","nes_source_epoch207"):
        edit(board,name+".sv",("20'hc0000","20'h80000"))
    edit(board,"nes_rom_spi.sv",("8'h7c,flags","8'h7d,flags"))
    bind_core_state(board, cpu_writer)


if __name__=="__main__":
    OUT.mkdir(exist_ok=True)
    prepare(OUT/"core")

