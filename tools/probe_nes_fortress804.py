"""Exercise the MMC803 odd-dot PPUDATA collision with the selected 801I sources."""
import argparse
import json
import shutil
from pathlib import Path

from nes_raw506 import once, sha
from probe_nes_fortress800 import prepare


def preview_ppu(text):
    return once(text, "read_2007_delayed==0 && write_2007_delayed==0 &&\n    (cycle[2:0]>=3",
                """// At the attribute address phase the tile name is latched. A
    // newly started $2007 read will need this low-plane byte to form the
    // later ALE/read address. Keep demand arbitration and tag checks intact.
    (read_2007_delayed==0 || (cycle[2:0]==3 && read_2007_delayed==1)) &&
    write_2007_delayed==0 && (cycle[2:0]>=3""")


def generate(board, rom, out, phase, cold_plane=False, fix=False, wrap=False,
             abort=False, observe=False, alternate_bank=False, stop_low=False):
    prepare(board, rom, out, phase, False, abort=abort)
    tb = out / "game147_tb.sv"
    original = tb.read_text()
    s = original.replace("333+scenario/12", "327+scenario/12")
    s = once(s, "bg_name_table=8'h00", "bg_name_table=8'h02")
    s = once(s, "vram_a_byte=8'h60", "vram_a_byte=8'h28")
    s = s.replace("17'h04060", "17'h04020").replace("['h04060]", "['h04020]")
    s = s.replace("17'h04000", "17'h04028").replace("['h04000]", "['h04028]")
    if cold_plane:
        s = once(s, "rom_service.ppu_cached=1;", "rom_service.ppu_cached=0;")
    if alternate_bank:
        # Real CHR byte FE at bank 8 + 20 feeds the second physical address.
        s = once(s, "mem['h407]='h10", "mem['h407]='h08")
        s = s.replace("04028", "02028").replace("04020", "02020")
    if stop_low:
        s = once(s, "scenario=0;scenario<36", "scenario=9;scenario<10")
        s = once(s, "if(step699>=79)break;", """if(rom_request && rom_ready &&
      rom_address==22'h204020 && dot699==331)begin
     $display("STOP804 accepted=%h step=%0d",rom_address,step699);break;end
    if(step699>=79)$fatal(1,"missing low-plane request");""")
        # STOP precedes the phase in which this CPU transfer would commit.
        s = once(s, "||commit_tick<0", "")
        s = once(s, "repeat(20)@(negedge clk);", """#0.001;
   repeat(20)begin
    if(rom_fault||rom_request||rom_response||rom_cpu_valid||rom_ppu_valid||!psram_oe)
      $fatal(1,"STOP during low-plane read did not isolate");
    @(negedge clk);
   end""")
    s = once(s, "(dot699>=336 || dot699<=1)", "(dot699>=330 && dot699<=337)")
    s = once(s, "WRAP800 ", "TRACE804 ")
    if observe:
        s = once(s, " reg [63:0] first_fault,first_ppu;", """
 reg [63:0] first_fault,first_ppu;
 reg obs_reset=1,ss804=1,sck804=0,mosi804=0;
 wire miso804;
 nes_run_observer134 observer804(.clk(clk),.reset(obs_reset),.core_reset(reset),
  .cpu_sample(rom_cpu_sample),.rom_fault(rom_fault),.rom_error(rom_error_code),
  .history_sample157(96'b0),.history_enable180(1'b0),.pad_event(1'b0),.pad_buttons(8'b0),
  .ppu_fault_state154(ppu_fault_state154),.fault_trigger(fault_trigger),.fault_context(fault_context),
  .SPI_SS(ss804),.SPI_SCK(sck804),.SPI_MOSI(mosi804),.miso(miso804),.selected());
 task automatic stopped_page(input byte cmd,input [55:0] expected);
  reg [63:0] tx,rx;
  tx={cmd,56'd0};rx=0;ss804=0;#2000;
  for(integer i=63;i>=0;i--)begin
   mosi804=tx[i];#1000;sck804=1;#1000;rx[i]=miso804;#1000;sck804=0;#1000;
  end
  ss804=1;#2000;
  if(rx[55:0]!==expected)$fatal(1,"bad retained page %h got %h expected %h",cmd,rx,expected);
  $display("PAGE804 cmd=%h reply=%014h",cmd,rx[55:0]);
 endtask""")
        s = once(s, "wait(memory_ready);@(negedge clk);", "wait(memory_ready);@(negedge clk);obs_reset=0;")
        s = once(s, 'if(rom_fault||rom_request', '''if(first_ppu==64'h50d3ce0000a08001)begin
    stopped_page(8'h71,{16'he501,first_fault[63:24]});
    stopped_page(8'h72,{16'he501,first_fault[23:0],16'h0201});
    stopped_page(8'h74,{16'he501,first_ppu[63:24]});
    stopped_page(8'h75,{16'he501,first_ppu[23:0],16'h0201});
   end
   obs_reset=1;
   if(rom_fault||rom_request''')
    tb.write_text(original if wrap else s, newline="\n")
    manifest = out / "inputs.json"
    m = json.loads(manifest.read_bytes())
    m.update(stage=804, cold_plane=cold_plane, fix=fix, wrap=wrap, abort=abort,
             observe=observe, alternate_bank=alternate_bank, stop_low=stop_low, scope=__doc__)
    if observe:
        for name in ("nes_run_observer134.sv", "nes_ppu_history157.sv", "nes_pad_trace156.sv"):
            shutil.copyfile(board / name, out / name)
            m["sources"][name] = sha(out / name)
    if fix:
        ppu = out / "rtl/ppu.sv"
        ppu.write_text(preview_ppu(ppu.read_text()), newline="\n")
        m["sources"]["rtl/ppu.sv"] = sha(ppu)
    m["sources"][tb.name] = sha(tb)
    manifest.write_text(json.dumps(m, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("board", "rom", "out"):
        p.add_argument(name, type=Path)
    p.add_argument("phase", type=float)
    p.add_argument("--cold-plane", action="store_true")
    p.add_argument("--fix", action="store_true")
    p.add_argument("--wrap", action="store_true")
    p.add_argument("--abort", action="store_true")
    p.add_argument("--observe", action="store_true")
    p.add_argument("--alternate-bank", action="store_true")
    p.add_argument("--stop-low", action="store_true")
    a = p.parse_args()
    if a.abort and not a.wrap:
        p.error("--abort uses the existing dot-340 in-flight request")
    generate(a.board, a.rom, a.out, a.phase, a.cold_plane, a.fix, a.wrap, a.abort,
             a.observe, a.alternate_bank, a.stop_low)
