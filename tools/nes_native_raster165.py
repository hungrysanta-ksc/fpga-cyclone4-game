# SPDX-License-Identifier: MIT
"""Export actual PPU state without replacing original register/write behavior."""
from pathlib import Path
import difflib,shutil
from nes_native_tap165 import prepare as prepare_tap
from nes_game147 import ROOT

PORTS='''output wire [14:0] native_scroll_v,native_scroll_t,
output wire [2:0] native_fine_x,native_pattern_mode,
output wire [7:0] native_display_mask,
output wire [191:0] native_palette,
output wire native_scroll_access,
'''
CONNECT='''.native_scroll_v(native_scroll_v),.native_scroll_t(native_scroll_t),
.native_fine_x(native_fine_x),.native_pattern_mode(native_pattern_mode),
.native_display_mask(native_display_mask),.native_palette(native_palette),
.native_scroll_access(native_scroll_access),
'''
NEW=['src/nes/diagnostic/nes_native_raster165.sv']
PACKET_PORTS='''input wire native_release_packet,native_state_query,native_query_palette,
input wire [7:0] native_query_row,
input wire [4:0] native_query_bank,native_query_color,
output wire native_state_owned,native_state_valid,native_state_response,native_state_hit,
output wire [15:0] native_generation,
output wire [7:0] native_state_errors,native_row_count,
output wire [5:0] native_palette_count,
output wire [55:0] native_state_data,
'''
BINDING='''
nes_native_raster165 native_raster(
 .clk(clk),.reset(reset),.ppu_ce(tap_ce),.scanline(scanline),.dot(cycle),
 .scroll_v(native_scroll_v),.scroll_t(native_scroll_t),.fine_x(native_fine_x),
 .pattern_mode(native_pattern_mode),.display_mask(native_display_mask),.palette(native_palette),
 .scroll_access(native_scroll_access),.source_fault(rom_fault),
 .release_packet(native_release_packet),.query(native_state_query),.query_palette(native_query_palette),
 .query_row(native_query_row),.query_bank(native_query_bank),.query_color(native_query_color),
 .owned(native_state_owned),.valid(native_state_valid),.generation(native_generation),
 .errors(native_state_errors),.row_count(native_row_count),.palette_count(native_palette_count),
 .response(native_state_response),.hit(native_state_hit),.data(native_state_data));
'''

def prepare(evidence,out):
    inputs=prepare_tap(evidence,out)
    changes=[]
    def edit(n,pairs):
        p=out/n;raw=p.read_bytes();old=raw.decode('utf8');text=old
        for a,b in pairs:
            assert text.count(a)==1,(n,a,text.count(a))
            text=text.replace(a,b,1)
        undo=text
        for a,b in reversed(pairs):
            assert undo.count(b)==1,(n,b)
            undo=undo.replace(b,a,1)
        assert undo.encode('utf8')==raw
        p.write_bytes(text.encode('utf8'))
        changes.extend(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='tap165/'+n,tofile='raster165/'+n))
    # Effective logical colors include $3F10/$14/$18/$1C aliases. Reading the
    # actual array also includes reset/savestate and rendering corruption.
    palette='\n'.join(f'assign native_palette[{i*6}+:6]=palette[{i if i%4 else i&15}];' for i in range(32))+'\n'
    edit('rtl/ppu.sv',[
        ('module VramAddressGen (','module VramAddressGen (\noutput wire native_scroll_effect,\n'),
        ('assign write_2006b = write_shift[1];','assign native_scroll_effect=write_2006b || trigger_2007;\nassign write_2006b = write_shift[1];'),
        ('module PaletteRam\n(','module PaletteRam\n(\noutput wire [191:0] native_palette,\n'),
        ('assign tap_palette[0+:6]=palette[0];',palette+'assign tap_palette[0+:6]=palette[0];'),
        ('module PPU(','module PPU(\n'+PORTS),
        ('VramAddressGen vram0(','wire native_scroll_effect;\nVramAddressGen vram0(\n.native_scroll_effect(native_scroll_effect),'),
        ('PaletteRam palette_ram(', 'PaletteRam palette_ram(\n.native_palette(native_palette),'),
        ('assign tap_bgp=bgp_en;', '''assign native_scroll_v=vram;
assign native_scroll_t=tap_scroll;
assign native_fine_x=fine_x_scroll;
assign native_pattern_mode={obj_size1,bg_patt1,obj_patt1};
assign native_display_mask={emph_reg,enable_objects,enable_playfield,object_clip,playfield_clip,grayscale};
assign native_scroll_access=native_scroll_effect || tap_ppu_change;
assign tap_bgp=bgp_en;''')])
    edit('rtl/nes.v',[('module NES(','module NES(\n'+PORTS),('PPU ppu(','PPU ppu(\n'+CONNECT)])
    edit('nes_probe.sv',[('module nes_probe(','module nes_probe(\n'+PORTS),('NES core(','NES core(\n'+CONNECT)])
    # NES-clock packet controls only. No host CDC or common CHR/OAM/map lease.
    edit('nes_live_joint.sv',[
        ('module nes_live_joint(','module nes_live_joint(\n'+PORTS+PACKET_PORTS),
        ('assign out_cpumem_addr=cpumem_addr;',BINDING+'\nassign out_cpumem_addr=cpumem_addr;')])
    for n in NEW:shutil.copy2(ROOT/n,out/Path(n).name)
    (out/'native-raster-binding.diff').write_text(''.join(changes),encoding='utf8')
    return inputs
