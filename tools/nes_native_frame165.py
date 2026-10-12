# SPDX-License-Identifier: MIT
"""Replace old snapshot observers with the evaluated native frame lease.

Control/query ports are NES-clock only. This is not host CDC or an SD build.
"""
from pathlib import Path
import difflib,shutil
from nes_game147 import ROOT
from nes_native_fetch165 import prepare as prepare_fetch,OUT as FETCH_OUT
from nes_native_scene165 import PORTS as SCENE_PORTS

FILES=['nes_native_planes165.sv','nes_native_compact_planes165.sv','nes_native_raster_frame165.sv','nes_native_frame165.sv']
PORTS='''input wire native_release_frame,native_query,
input wire [2:0] native_query_kind,input wire [12:0] native_query_index,input wire [15:0] native_query_generation,
output wire native_frame_owned,native_geometry_valid,native_initialized,native_active,native_response,native_hit,native_scroll_seen,
output wire [15:0] native_generation,output wire [24:0] native_errors,output wire [63:0] native_data,
output wire [7:0] native_row_count,native_object_count,native_exception_count,
output wire [5:0] native_group_count,native_palette_count,
'''
BINDING='''
nes_native_frame165 native_frame(
 .clk(clk),.reset(reset),.release_frame(native_release_frame),.ppu_ce(tap_ce),.rom_fault(rom_fault),
 .scanline(scanline),.dot(cycle),.bg_low(native_bg_low),.bg_high(native_bg_high),
 .obj_low(native_obj_low),.obj_high(native_obj_high),.obj_valid(native_obj_valid),.extra_sprites(native_extra_sprites),
 .bg_attribute(tap_attribute),.obj_attribute(native_obj_attribute),.obj_x(native_obj_x),
 .ppu_read(ppumem_read),.ppu_valid(rom_ppu_valid),.logical_address(native_chr_logical),.physical_address(ppumem_addr),
 .scroll_v(native_scroll_v),.scroll_t(native_scroll_t),.fine_x(native_fine_x),.pattern_mode(native_pattern_mode),
 .display_mask(native_display_mask),.palette(native_palette),.scroll_access(native_scroll_access),
 .query(native_query),.query_kind(native_query_kind),.query_index(native_query_index),.query_generation(native_query_generation),
 .owned(native_frame_owned),.geometry_valid(native_geometry_valid),.initialized(native_initialized),.active(native_active),
 .generation(native_generation),.errors(native_errors),.scroll_seen(native_scroll_seen),.row_count(native_row_count),
 .object_count(native_object_count),.exception_count(native_exception_count),.group_count(native_group_count),.palette_count(native_palette_count),
 .response(native_response),.hit(native_hit),.data(native_data));
'''

def prepare(evidence,out):
 inputs=prepare_fetch(evidence,out);p=out/'nes_live_joint.sv';old=s=p.read_text()
 assert s.count(FETCH_OUT)==1 and s.count(SCENE_PORTS)==1
 s=s.replace(FETCH_OUT,PORTS).replace(SCENE_PORTS,'')
 begin=s.index('wire native_required_initialized,native_required_active;')
 end=s.index('// Raster and CHR now share the scene instance above.',begin)
 s=s[:begin]+BINDING+'\nassign native_nt_address=0;assign native_oam_address=0;\n'+s[end:]
 s=s.replace('// Raster and CHR now share the scene instance above.','// Evaluated geometry replaces the old unchanged CIRAM/OAM snapshot requirement.')
 assert 'nes_native_scene_fetch165 native_scene(' not in s and 'nes_native_fetch165 native_fetch(' not in s
 p.write_text(s,encoding='utf8')
 for n in FILES:shutil.copy2(ROOT/'src/nes/diagnostic'/n,out/n)
 (out/'native-frame-binding.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='fetch165/nes_live_joint.sv',tofile='frame165/nes_live_joint.sv')),encoding='utf8')
 return inputs
