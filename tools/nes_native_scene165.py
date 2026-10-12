# SPDX-License-Identifier: MIT
"""Materialize real CIRAM/OAM observation and one NES-domain graphics lease."""
from pathlib import Path
import difflib,shutil
from nes_game147 import ROOT
from nes_native_raster165 import prepare as prepare_raster,PACKET_PORTS,BINDING as RASTER_BINDING
from nes_native_tap165 import PORTS as CACHE_PORTS,BINDING as CACHE_BINDING
NEW=['src/nes/diagnostic/nes_native_ciram165.sv','src/nes/diagnostic/nes_native_scene165.sv']
OAM_PORTS='''input wire [7:0] native_oam_address,
output wire [7:0] native_oam_data,
output wire native_oam_write,
'''
OAM_CONNECT='''.native_oam_address(native_oam_address),.native_oam_data(native_oam_data),.native_oam_write(native_oam_write),
'''
PORTS='''input wire native_release_scene,
input wire native_query,native_query_obj4,native_state_query,native_query_palette,native_memory_query,
input wire [8:0] native_query_slot,input wire [17:0] native_query_tag,input wire [4:0] native_query_offset,
input wire [7:0] native_query_row,input wire [4:0] native_query_bank,native_query_color,
input wire [11:0] native_memory_address,
output wire native_scene_owned,native_snapshot_valid,native_response,native_hit,native_state_response,native_state_hit,
output wire native_memory_response,native_memory_hit,output wire [7:0] native_memory_data,native_data,
output wire [15:0] native_valid_bytes,native_generation,output wire [55:0] native_state_data,
output wire [7:0] native_state_errors,native_row_count,output wire [5:0] native_palette_count,
output wire [2:0] native_memory_errors,
'''
BINDING='''
nes_native_scene165 native_scene(
 .clk(clk),.reset(reset),.ppu_ce(tap_ce),.ppu_read(ppumem_read),.ppu_valid(rom_ppu_valid),.rom_fault(rom_fault),
 .ppu_logical(native_chr_logical),.ppu_physical(ppumem_addr),.ppu_data(ppumem_din),.scanline(scanline),.dot(cycle),
 .scroll_v(native_scroll_v),.scroll_t(native_scroll_t),.fine_x(native_fine_x),.pattern_mode(native_pattern_mode),
 .display_mask(native_display_mask),.palette(native_palette),.scroll_access(native_scroll_access),
 .nt_address(native_nt_address),.nt_data(native_nt_data),.nt_write(native_nt_write),
 .oam_address(native_oam_address),.oam_data(native_oam_data),.oam_write(native_oam_write),
 .release_scene(native_release_scene),.owned(native_scene_owned),.snapshot_valid(native_snapshot_valid),
 .generation(native_generation),.raster_errors(native_state_errors),.memory_errors(native_memory_errors),
 .row_count(native_row_count),.palette_count(native_palette_count),
 .chr_query(native_query),.chr_slot(native_query_slot),.chr_tag(native_query_tag),.chr_offset(native_query_offset),.chr_obj4(native_query_obj4),
 .chr_response(native_response),.chr_hit(native_hit),.chr_data(native_data),.chr_mask(native_valid_bytes),
 .state_query(native_state_query),.state_palette(native_query_palette),.state_row(native_query_row),.state_bank(native_query_bank),.state_color(native_query_color),
 .state_response(native_state_response),.state_hit(native_state_hit),.state_data(native_state_data),
 .memory_query(native_memory_query),.memory_address(native_memory_address),.memory_response(native_memory_response),.memory_hit(native_memory_hit),.memory_data(native_memory_data));
'''
def prepare(evidence,out):
 inputs=prepare_raster(evidence,out);diff=[]
 def edit(n,pairs):
  p=out/n;raw=p.read_bytes();original=text=raw.decode('utf8')
  for a,b in pairs:
   assert text.count(a)==1,(n,a,text.count(a));text=text.replace(a,b,1)
  undo=text
  for a,b in reversed(pairs):
   assert undo.count(b)==1,(n,b);undo=undo.replace(b,a,1)
  assert undo.encode()==raw
  p.write_bytes(text.encode());diff.extend(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='raster165/'+n,tofile='scene165/'+n))
 edit('rtl/ppu.sv',[
  ('module OAMEval(','module OAMEval(\n'+OAM_PORTS),
  ('reg sec_ovr;','assign native_oam_data=oam_read(native_oam_address);\nassign native_oam_write=Savestate_OAMWrEn || oam_copy_write || oam_cpu_write;\nreg sec_ovr;'),
  ('module PPU(','module PPU(\n'+OAM_PORTS),
  ('OAMEval spriteeval (', 'OAMEval spriteeval (\n'+OAM_CONNECT)])
 edit('rtl/nes.v',[('module NES(','module NES(\n'+OAM_PORTS),('PPU ppu(','PPU ppu(\n'+OAM_CONNECT)])
 edit('nes_probe.sv',[('module nes_probe(','module nes_probe(\n'+OAM_PORTS),('NES core(','NES core(\n'+OAM_CONNECT)])
 local='''input wire [10:0] native_nt_address,output wire [7:0] native_nt_data,output wire native_nt_write,
'''
 ciram='''nes_local_memory_ram #(.AW(11)) ciram(clk,
  !reset && (small_clearing || (init_done && ppumem_write && nt_selected)),
  init_done?ppumem_addr[10:0]:scrub_address[10:0],init_done?ppumem_dout:8'd0,nt_q);'''
 replacement='''assign native_nt_write=!reset && (small_clearing || (init_done && ppumem_write && nt_selected));
 nes_native_ciram165 ciram(clk,native_nt_write,
  init_done?ppumem_addr[10:0]:scrub_address[10:0],init_done?ppumem_dout:8'd0,nt_q,
  native_nt_address,native_nt_data);'''
 edit('nes_local_memory.sv',[('module nes_local_memory(','module nes_local_memory(\n'+local),(ciram,replacement)])
 edit('nes_live_joint.sv',[
  (CACHE_PORTS,PORTS),(PACKET_PORTS,'// Common scene ownership ports follow.\n'),
  (CACHE_BINDING,BINDING),(RASTER_BINDING,'// Raster and CHR now share the scene instance above.\n'),
  (' nes_probe dut(.*);',' wire [7:0] native_oam_address,native_oam_data,native_nt_data;\n wire [10:0] native_nt_address;\n wire native_oam_write,native_nt_write;\n nes_probe dut(.*);'),
  ('nes_local_memory local_memory(', 'nes_local_memory local_memory(\n.native_nt_address(native_nt_address),.native_nt_data(native_nt_data),.native_nt_write(native_nt_write),')])
 for n in NEW:shutil.copy2(ROOT/n,out/Path(n).name)
 (out/'native-scene-binding.diff').write_text(''.join(diff),encoding='utf8')
 return inputs
