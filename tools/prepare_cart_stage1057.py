"""Generate both ARM profiles and game-specific boards from the fitted 1056 inputs."""
import argparse
import shutil
from prepare_nes_carts1056 import OUT as BASE
from prepare_nes_kirby1023 import edit

OUT = BASE.parent / "nes-carts1057"


def arm(profile):
    link = OUT / profile / "link"
    shutil.copytree(BASE / profile / "link", link, dirs_exist_ok=True)
    src = link / "src"
    if profile == "release":
        edit(src, "nes_native_runtime165.c",
             ("if((uint32_t)(s->ticks(s->ctx)-s->started)>=s->limit)",
              "if(s->limit && (uint32_t)(s->ticks(s->ctx)-s->started)>=s->limit)"),
             ("||!limit||limit>=", "||limit>="),
             ("if(s->steps++==4194304u)", """static uint32_t watchdog_tick;
 uint32_t now=s->ticks(s->ctx);
 if(now!=watchdog_tick){watchdog_tick=now;s->steps=0;}
 if(s->steps++==4194304u)"""),
             ("nes_budget210_frame(s->ticks(s->ctx)-s->started)", "nes_budget210_frame(now-s->started)"))
        edit(src, "nes_cf86_session094.c",
             ("static enum phase094 phase094;", """static enum phase094 phase094;
bool nes_allow_cart_reset1057,nes_cart_reset1057;"""),
             ("bool reset_ok=phase094==RELEASING146 || (phase094==DISPLAY146 ? !get_snes_reset() : get_snes_reset());",
              """bool asserted=get_snes_reset();
 if(phase094==DISPLAY146 && nes_allow_cart_reset1057 && asserted && !nes_cart_reset1057){
  snes_reset(1);nes_cart_reset1057=true;
 }
 bool reset_ok=phase094==RELEASING146 || (phase094==DISPLAY146 && !nes_cart_reset1057 ? !asserted : asserted);"""),
             ("if(phase094!=IDLE094||!owner094())", "nes_cart_reset1057=false;nes_allow_cart_reset1057=false;\n if(phase094!=IDLE094||!owner094())"))
        edit(src, "nes_runtime_board165.inc", ("NES_PATTERN_RAM?0x7fffffffu:6000", "0"),
             ("static bool native_first165;", "static bool native_first165;\nextern bool nes_allow_cart_reset1057,nes_cart_reset1057;"),
             ("(void)io;nes_cost471_scene_crc", "nes_allow_cart_reset1057=!NES_PATTERN_RAM;\n (void)io;nes_cost471_scene_crc"),
             ("uint32_t now=getticks();", """if(nes_cart_reset1057){
  native_runtime165.result=NES_RUNTIME165_DEADLINE;
  return false;
 }
 uint32_t now=getticks();"""))
    else:
        for name in ("nes_menu_diagnostic.c", "nes_checkpoint112.c"):
            edit(src, name, ("debug1056", "debug1057"))
        edit(src, "nes_budget210.c", ("log900p->edition=1054", "log900p->edition=1057"))
        # Only after STOP and base restoration. Keep the ordinary trace intact.
        # The report contains the validated fault address, PPU dot and reject ring.
        edit(src, "nes_menu_diagnostic.c",
             ('write_report893("/sd2snes/nes-frame-debug1057.bin"',
              'write_report893("/sd2snes/nes-stop-debug1057.bin","stop",(const char *)&nes_run136,sizeof nes_run136);\n write_report893("/sd2snes/nes-frame-debug1057.bin"'))


def axrom():
    dest = OUT / "board-7"
    shutil.copytree(BASE / dest.name, dest, dirs_exist_ok=True)
    edit(dest, "nes_live_joint.sv",
         ("nes_chr_snapshot snapshot(", """nes_chr_snapshot snapshot(
 .rendering(|native_display_mask[4:3]),.capture_end(tap_ce && scanline==232 && cycle==1),"""))
    edit(dest, "nes_chr_snapshot.sv",
         ("module nes_chr_snapshot (", "module nes_chr_snapshot (input wire rendering,capture_end,"),
         ("reg held;", """reg held, sealed, rendered;
 // Geometry starts at line 7. While both rendering planes are disabled the
 // PPU has not used pattern RAM. Let the mirror catch up to those writes.
 // Freeze the mirror at capture end, before any geometry lease can read it.
 always @(posedge clk)begin
   if(reset || discard || (retire && retire_gen==owner))begin sealed<=0;rendered<=0;end
   else if(start && can_start)begin sealed<=0;rendered<=rendering;end
   else if(held && !sealed)begin
     if(rendering)rendered<=1;
     if(capture_end)sealed<=1;
   end
 end"""),
         ("reg [15:0] owner;", ""),
         ("reg held, sealed, rendered;", "reg [15:0] owner;reg held, sealed, rendered;"),
         ("assign can_start=!reset && !held && state==CLEAN && !dirty && !changed;",
          "assign can_start=!reset && !held;"),
         ("!cancel && held && state==CLEAN", "!cancel && held && sealed && !conflict && state==CLEAN"),
         ("if(held && collecting) conflict<=1;", "if(held && !sealed && (rendered || rendering)) conflict<=1;"),
         ("if(start && can_start)begin held<=1;owner<=start_gen;conflict<=0;end",
          """if(start && can_start)begin held<=1;owner<=start_gen;conflict<=changed && rendering;end
   if(held && capture_end && !sealed && (changed || |dirty || state!=CLEAN))conflict<=1;"""),
         ("if(!held && (dirty||changed))", "if(!sealed && (dirty||changed))"),
         ("else after_capture<=after_capture|write_mask;", """else after_capture<=after_capture|write_mask;
   // A prefix write postdates the receipt taken when geometry started.
   if(changed && ((held && !sealed) || (start && can_start)))begin
     clean_pages<=0;fine_receipt<=0;
   end"""))


def vrc():
    dest = OUT / "board-21"
    shutil.copytree(BASE / dest.name, dest, dirs_exist_ok=True)
    # CHR physical bit 3 selects a byte lane. Both lanes are already sampled
    # on the same PSRAM read; normalise CHR addresses before issuing a request.
    # PRG traffic, owner checks, response address validation and STOP stay exact.
    edit(dest, "nes_live_joint.sv",
         ("nes_rom_early rom_service(", "nes_rom_early rom_service(.chr_plane1(bg_word),"))
    edit(dest, "nes_rom_service.sv",
         ("module nes_rom_early(", "module nes_rom_early(input wire [7:0] chr_plane1,"),
         ("reg [7:0] ppu_previous_byte;", "reg [15:0] ppu_previous_byte;"),
         ("reg [7:0] cpu_byte,ppu_byte;", "reg [7:0] cpu_byte;reg [15:0] ppu_byte;"),
         ("wire ppu_reply=", """wire [21:0] row_address={ppumem_addr[21:4],1'b0,ppumem_addr[2:0]};
 wire [21:0] hint_address={ppu_prefetch_address[21:4],1'b0,ppu_prefetch_address[2:0]};
 wire ppu_reply="""),
         ("pending_address==ppumem_addr", "pending_address==row_address"),
         ("==ppumem_addr[17:0]", "==row_address[17:0]"),
         ("==ppu_prefetch_address[17:0]", "==hint_address[17:0]"),
         ("pending_address==ppu_prefetch_address", "pending_address==hint_address"),
         ("use_prefetch ? ppu_prefetch_address[17:0] : ppumem_addr[17:0]",
          "use_prefetch ? hint_address[17:0] : row_address[17:0]"),
         ("assign ppu_data=ppu_reply?rom_data:", "wire [15:0] selected_row=ppu_reply?{chr_plane1,rom_data}:"),
         ("wire cpu_pending=", "assign ppu_data=ppumem_addr[3]?selected_row[15:8]:selected_row[7:0];\n wire cpu_pending="),
         ("ppu_byte<=rom_data;", "ppu_byte<={chr_plane1,rom_data};"))
    # Decode the sampled address/data on the same edge as tag/data_previous.
    # STOP and fault still qualify the retiring write on the original edge.
    edit(dest, "nes_sink_bus165.sv",
         ("reg [7:0] control_data;", """reg [7:0] control_data;
 reg map_command;
 always @(posedge clk)map_command<=address_sync==24'h00601d && data_sync==8'ha5;"""),
         ("if(address_previous==24'h006002)", "if(sample_valid[1] && map_command && !stop && !fault)map_progress<=1;\n    if(address_previous==24'h006002)"),
         ("if(address_previous[3:0]==13&&!stop&&!fault)map_progress<=1;", ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=("axrom", "vrc", "debug", "release"))
    target = parser.parse_args().target
    if target == "axrom":
        axrom()
    elif target == "vrc":
        vrc()
    else:
        arm(target)
