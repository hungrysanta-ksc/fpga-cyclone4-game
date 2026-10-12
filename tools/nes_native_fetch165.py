# SPDX-License-Identifier: MIT
"""Bind pattern-load observations to the real PPU and mapped same-edge bus."""
from pathlib import Path
import difflib,shutil
from nes_game147 import ROOT
from nes_native_scene165 import prepare as prepare_scene

NEW=['src/nes/diagnostic/nes_native_fetch165.sv']
PORTS='''output wire native_bg_low,native_bg_high,native_obj_low,native_obj_high,native_obj_valid,
output wire native_extra_sprites,
output wire [7:0] native_obj_attribute,native_obj_x,
'''
CONNECT='''.native_bg_low(native_bg_low),.native_bg_high(native_bg_high),
.native_obj_low(native_obj_low),.native_obj_high(native_obj_high),.native_obj_valid(native_obj_valid),
.native_extra_sprites(native_extra_sprites),.native_obj_attribute(native_obj_attribute),.native_obj_x(native_obj_x),
'''
OUT='''input wire native_required_query,input wire [12:0] native_required_tile,
output wire native_required_owned,native_required_valid,native_required_response,
output wire [1:0] native_required_kind,output wire [7:0] native_fetch_errors,
output wire native_fetch_event,output wire [63:0] native_fetch_data,
'''
BINDING='''
wire native_required_initialized,native_required_active;
wire native_scene_base_owned,native_scene_base_valid;
wire [15:0] native_required_generation,native_scene_generation;
// Descriptor stream is not yet stored or consumed by the SNES path.
nes_native_fetch165 native_fetch(
 .clk(clk),.reset(reset),.release_scene(native_release_scene),.ppu_ce(tap_ce),.rom_fault(rom_fault),
 .scanline(scanline),.dot(cycle),.bg_low(native_bg_low),.bg_high(native_bg_high),
 .obj_low(native_obj_low),.obj_high(native_obj_high),.obj_valid(native_obj_valid),.extra_sprites(native_extra_sprites),
 .bg_attribute(tap_attribute),.obj_attribute(native_obj_attribute),.obj_x(native_obj_x),
 .ppu_read(ppumem_read),.ppu_valid(rom_ppu_valid),.logical_address(native_chr_logical),.physical_address(ppumem_addr),
 .query(native_required_query && native_scene_owned),.query_tile(native_required_tile),
 .initialized(native_required_initialized),.active(native_required_active),.owned(native_required_owned),.valid(native_required_valid),
 .errors(native_fetch_errors),.generation(native_required_generation),.event_valid(native_fetch_event),.event_data(native_fetch_data),
 .response(native_required_response),.required_kind(native_required_kind));
assign native_scene_owned=native_required_owned && (!native_required_valid || native_scene_base_owned);
assign native_generation=native_required_generation;
// This is still not a complete-frame-ready flag: CHR fill, stream consumption,
// resource limits and host/SNES transfer have not been connected.
assign native_snapshot_valid=native_scene_base_valid && native_required_valid && native_scene_owned;
'''

def prepare(evidence,out):
 inputs=prepare_scene(evidence,out);diff=[]
 def edit(n,pairs):
  p=out/n;raw=p.read_bytes();original=text=raw.decode('utf8')
  for a,b in pairs:
   assert text.count(a)==1,(n,a,text.count(a));text=text.replace(a,b,1)
  undo=text
  for a,b in reversed(pairs):
   assert undo.count(b)==1,(n,b);undo=undo.replace(b,a,1)
  assert undo.encode()==raw
  p.write_bytes(text.encode());diff.extend(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='scene165/'+n,tofile='fetch165/'+n))
 edit('rtl/ppu.sv',[
  ('module SpriteAddressGen(','''module SpriteAddressGen(
output wire native_valid,
output reg [7:0] native_attribute,native_x,
'''),
  ('assign load_y =    (count == 0) && enabled;', '''assign native_valid=~dummy_sprite;
always @(posedge clk) if(ce) begin
 if(load_attr)native_attribute<=temp;
 if(load_x)native_x<=temp;
end
assign load_y =    (count == 0) && enabled;'''),
  ('module PPU(','module PPU(\n'+PORTS),
  ('SpriteAddressGen address_gen(','''SpriteAddressGen address_gen(
.native_valid(native_obj_valid),.native_attribute(native_obj_attribute),.native_x(native_obj_x),'''),
  ('assign tap_bgp=bgp_en;', '''assign native_bg_low=bgp_en && cycle[2:0]==6;
assign native_bg_high=bgp_en && cycle[2:0]==0;
assign native_obj_low=spriteset_load[3];
assign native_obj_high=spriteset_load[2];
assign native_extra_sprites=extra_sprites;
assign tap_bgp=bgp_en;''')])
 edit('rtl/nes.v',[('module NES(','module NES(\n'+PORTS),('PPU ppu(','PPU ppu(\n'+CONNECT)])
 edit('nes_probe.sv',[('module nes_probe(','module nes_probe(\n'+PORTS),('NES core(','NES core(\n'+CONNECT)])
 # Preserve the pinned scene source. A generated variant gates its start until
 # the preceding line's OBJ/BG prefetch capture has been armed. An early fault
 # is carried through the ordinary scene retirement path at row8/dot1.
 p=out/'nes_native_scene165.sv';original=p.read_text()
 pairs=[('module nes_native_scene165(','module nes_native_scene_fetch165(\n input wire capture_ready,\n'),
        ('wire qualified_ce=ppu_ce && initialized;','wire qualified_ce=ppu_ce && initialized && capture_ready;')]
 text=original
 for a,b in pairs:assert text.count(a)==1;text=text.replace(a,b,1)
 undo=text
 for a,b in reversed(pairs):undo=undo.replace(b,a,1)
 assert undo==original
 (out/'nes_native_scene_fetch165.sv').write_text(text)
 diff.extend(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='scene165/nes_native_scene165.sv',tofile='fetch165/nes_native_scene_fetch165.sv'))
 edit('nes_live_joint.sv',[
  ('module nes_live_joint(','module nes_live_joint(\n'+PORTS+OUT),
  ('nes_native_scene165 native_scene(',BINDING+'''\nnes_native_scene_fetch165 native_scene(
 .capture_ready(native_required_active || native_required_owned),'''),
  ('.ppu_valid(rom_ppu_valid),.rom_fault(rom_fault),', '.ppu_valid(rom_ppu_valid),.rom_fault(rom_fault || (native_required_owned && !native_required_valid)),'),
  ('.owned(native_scene_owned),.snapshot_valid(native_snapshot_valid),','.owned(native_scene_base_owned),.snapshot_valid(native_scene_base_valid),'),
  ('.generation(native_generation),','.generation(native_scene_generation),'),
  ('.chr_query(native_query),','.chr_query(native_query && native_snapshot_valid),'),
  ('.state_query(native_state_query),','.state_query(native_state_query && native_snapshot_valid),'),
  ('.memory_query(native_memory_query),','.memory_query(native_memory_query && native_snapshot_valid),')])
 for n in NEW:shutil.copy2(ROOT/n,out/Path(n).name)
 (out/'native-fetch-binding.diff').write_text(''.join(diff),encoding='utf8')
 return inputs
