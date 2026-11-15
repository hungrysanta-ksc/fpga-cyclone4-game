"""Run the selected T65/PPU, MMC3, ROM service, arbiter and dual-clock reader at the visible-line wrap."""
import argparse
import json
from pathlib import Path

import probe_nes_bg707_read_cpu as previous
from nes_raw506 import once, sha


def compact_reader(text):
    # Only two apertures can issue: PRG [0,0x40000) or CHR [0x200000,0x220000).
    # Keep the full returned address check, including otherwise-constant bits.
    text=once(text,"reg [21:0] pending_address;",
              "reg [17:0] pending_offset;wire [21:0] pending_address={pending_ppu,3'b000,pending_offset};")
    text=once(text,"pending_address<=0","pending_offset<=0")
    text=once(text,"pending_address<=rom_address","pending_offset<=rom_address[17:0]")
    text=once(text,"assign rom_address=rom_request?(use_prefetch?ppu_prefetch_address:(choose_ppu?ppumem_addr:cpumem_addr[21:0])):pending_address;",
              """wire next_ppu=choose_ppu || use_prefetch;
 wire [17:0] next_offset=next_ppu ? {1'b0,(use_prefetch ? ppu_prefetch_address[16:0] : ppumem_addr[16:0])} : cpumem_addr[17:0];
 assign rom_address=rom_request ? {next_ppu,3'b000,next_offset} : pending_address;""")
    return text


def preview_ppu(text):
    text = once(text, "assign game147_prefetch_hint=readtail707", '''// Dot 340 is a nametable read. The pending PPUDATA strobe will
// sample the dot-zero pattern address using the already latched low byte.
wire wrap800=cycle==340 && scanline<239 && is_rendering_d && is_rendering &&
    read_2007_delayed==5'b01000 && write_2007_delayed==0;
assign game147_prefetch_hint=wrap800 || readtail707''')
    return once(text, " : restart160 ?", " : (restart160 || wrap800) ?")


def prepare(board, rom, out, phase, preview, compact=False, abort=False):
    previous.prepare(board,rom,out,phase)
    tb=out/"game147_tb.sv"
    s=tb.read_text()
    # Use the original $A83C LDA $2007 as an instruction stimulus. Its PC is
    # not available in the physical fault record. Sweep its alignment to dot 0.
    s=once(s,"scenario<12","scenario<36")
    s=once(s,"initial begin #10000000;","initial begin #30000000;")
    # The old fixture primed the 707 scene's pattern cache. Use two initial
    # bytes for this scene instead. Never prime the demand byte at 0x204082.
    s=s.replace("1e160","04060").replace("1e168","04000")
    s=once(s,"15'h0b02","15'h0081")
    s=once(s,"bg_name_table=8'h16","bg_name_table=8'h00")
    s=once(s,"mem['h407]='h78","mem['h407]='h10")
    s=once(s,"221+step699/4","(333+scenario/12+step699/4)%341")
    s=once(s,"line699=start699<0?243:193;","")
    s=once(s,"render699=step699>=0;",
           "line699=start699<0?243:161+(333+scenario/12+step699/4)/341;render699=step699>=0;")
    s=once(s,"    if(rom_request && rom_address==22'h208fe7)",'''    if(step699>=0 && (dot699>=336 || dot699<=1))
      $display("WRAP800 s=%0d t=%0d line=%0d dot=%0d ce=%b pipe=%h a=%h latch=%h hint=%b/%h read=%b mapped=%h valid=%b core=%b/%b/%h mem=%b/%b/%h reply=%b/%h fill=%b/%b",
        scenario,step699,line699,dot699,ce699,dut.core.ppu.read_2007_delayed,dut.core.ppu.vram_a,
        dut.core.ppu.vram_a_byte,game147_prefetch_hint,game148_hint_physical,ppumem_read,ppumem_addr,rom_ppu_valid,
        rom_request,rom_ready,rom_address,mem_request699,mem_ready699,mem_address699,
        rom_response,rom_response_address,fill_ready699,fill_response699);
    if(rom_request && rom_address==22'h208fe7)''')
    if abort:
        # Cancel after an accepted speculative request, before its response.
        # The real core, arbiter and asynchronous reader all receive reset.
        s=once(s,"scenario=0;scenario<36","scenario=8;scenario<11")
        s=once(s,"if(step699>=79)break;",'''if(rom_request && rom_address==22'h204082 && line699==161 && dot699==340)begin
     $display("ABORT800 scenario=%0d step=%0d",scenario,step699);break;end
    if(step699>=79)$fatal(1,"expected in-flight preview");''')
        s=once(s,"   repeat(20)@(negedge clk);",'''   #0.001;
   if(rom_request || rom_response || rom_cpu_valid || rom_ppu_valid || !psram_oe)$fatal(1,"STOP did not isolate pins");
   repeat(20)begin @(negedge clk);
    if(rom_request || rom_response || rom_cpu_valid || rom_ppu_valid || !psram_oe)$fatal(1,"stale reply after STOP");
   end''')
    tb.write_text(s, newline="\n")
    ppu=out/"rtl/ppu.sv"
    if preview:
        ppu.write_text(preview_ppu(ppu.read_text()), newline="\n")
    if compact:
        service=out/"nes_rom_service.sv"
        service.write_text(compact_reader(service.read_text()),newline="\n")
    meta=json.loads((out/"inputs.json").read_bytes())
    meta.update(stage=800, phase=phase, preview=preview,compact_reader=compact,abort=abort,scope=__doc__)
    for name in ("rtl/ppu.sv","nes_rom_service.sv",tb.name):
        meta["sources"][name]=sha(out/name)
    (out/"inputs.json").write_text(json.dumps(meta,indent=2)+"\n")


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("board","rom","out"):
        ap.add_argument("--"+name,required=True,type=Path)
    ap.add_argument("--phase",type=float,default=3.5)
    ap.add_argument("--preview",action="store_true")
    ap.add_argument("--compact",action="store_true")
    ap.add_argument("--abort",action="store_true")
    a=ap.parse_args()
    prepare(a.board,a.rom,a.out,a.phase,a.preview,a.compact,a.abort)
