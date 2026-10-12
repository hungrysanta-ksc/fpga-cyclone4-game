# SPDX-License-Identifier: MIT
"""Materialize bounded fill on the existing reader; no SD image or host CDC."""
from pathlib import Path
import difflib,shutil
from nes_game147 import ROOT
from nes_native_frame165 import prepare as frame_prepare,BINDING as FRAME_BINDING,FILES as FRAME_FILES

FILES=FRAME_FILES+['nes_native_fill165.sv','nes_native_arbiter165.sv']
PORTS='''input wire native_fill_start,native_byte_ready,
output wire native_fill_busy,native_fill_done,native_fill_success,native_byte_valid,
output wire [3:0] native_fill_error,output wire [7:0] native_byte_data,
output wire [12:0] native_byte_tile,output wire [3:0] native_byte_lane,
output wire [1:0] native_byte_kind,output wire [15:0] native_byte_generation,
'''
WIRES='''
wire native_fill_slot,native_core_safe,native_arbiter_fault;
wire native_mem_ready,native_mem_request,native_mem_response,native_mem_error;
wire [21:0] native_mem_address,native_mem_response_address;wire [7:0] native_mem_data;
wire native_fill_request,native_fill_ready,native_fill_idle,native_fill_abort,native_fill_response,native_fill_mem_error;
wire [21:0] native_fill_address,native_fill_reply_address;wire [15:0] native_fill_generation,native_fill_reply_generation;
wire [7:0] native_fill_data;
wire native_fill_query,native_frame_response,native_frame_hit;wire [2:0] native_fill_query_kind;
wire [12:0] native_fill_query_index;wire [15:0] native_fill_query_generation;wire [63:0] native_frame_data;
wire native_frame_query=native_fill_busy?native_fill_query:(native_query&&!native_fill_start);
wire [2:0] native_frame_query_kind=native_fill_busy?native_fill_query_kind:native_query_kind;
wire [12:0] native_frame_query_index=native_fill_busy?native_fill_query_index:native_query_index;
wire [15:0] native_frame_query_generation=native_fill_busy?native_fill_query_generation:native_query_generation;
assign native_response=native_frame_response&&!native_fill_busy&&!native_fill_start;
assign native_hit=native_frame_hit&&!native_fill_busy&&!native_fill_start;
assign native_data=native_hit?native_frame_data:64'd0;
'''
BINDING=FRAME_BINDING
for old,new in [('native_query','native_frame_query'),('native_query_kind','native_frame_query_kind'),
 ('native_query_index','native_frame_query_index'),('native_query_generation','native_frame_query_generation'),
 ('native_response','native_frame_response'),('native_hit','native_frame_hit'),('native_data','native_frame_data')]:
 BINDING=BINDING.replace('('+old+')','('+new+')')
BINDING+='''
nes_native_fill165 #(.WAIT_CYCLES(65536)) native_fill(
 .clk(clk),.reset(reset),.start(native_fill_start),.clear(native_release_frame),
 .frame_owned(native_frame_owned),.geometry_valid(native_geometry_valid&&!rom_fault&&!native_arbiter_fault),.frame_generation(native_generation),
 .query(native_fill_query),.query_kind(native_fill_query_kind),.query_index(native_fill_query_index),.query_generation(native_fill_query_generation),
 .response(native_frame_response),.hit(native_frame_hit),.data(native_frame_data),
 .mem_idle(native_fill_idle),.mem_ready(native_fill_ready),.mem_response(native_fill_response),.mem_error(native_fill_mem_error),
 .mem_response_address(native_fill_reply_address),.mem_response_generation(native_fill_reply_generation),.mem_data(native_fill_data),
 .mem_request(native_fill_request),.mem_abort(native_fill_abort),.mem_address(native_fill_address),.mem_generation(native_fill_generation),
 .byte_valid(native_byte_valid),.byte_ready(native_byte_ready),.byte_data(native_byte_data),.byte_tile(native_byte_tile),.byte_lane(native_byte_lane),
 .byte_kind(native_byte_kind),.byte_generation(native_byte_generation),.busy(native_fill_busy),.done(native_fill_done),
 .success(native_fill_success),.error(native_fill_error),.quarantine(),.tile_count(),.byte_count(),.cycles());
nes_native_arbiter165 native_arbiter(
 .clk(clk),.reset(reset),.slot(native_fill_slot),.core_safe(native_core_safe),
 .core_request(rom_request),.core_address(rom_address),.core_ready(rom_ready),.core_response(rom_response),.core_error(rom_error),
 .core_response_address(rom_response_address),.core_data(rom_data),
 .fill_request(native_fill_request),.fill_abort(native_fill_abort),.fill_address(native_fill_address),.fill_generation(native_fill_generation),
 .fill_ready(native_fill_ready),.fill_idle(native_fill_idle),.fill_response(native_fill_response),.fill_error(native_fill_mem_error),
 .fill_response_address(native_fill_reply_address),.fill_response_generation(native_fill_reply_generation),.fill_data(native_fill_data),
 .mem_ready(native_mem_ready),.mem_request(native_mem_request),.mem_address(native_mem_address),.mem_response(native_mem_response),
 .mem_error(native_mem_error),.mem_response_address(native_mem_response_address),.mem_data(native_mem_data),.fault(native_arbiter_fault));
'''

def backend_binding(s):
 for n in ['ready','request','address','response','error','response_address','data']:
  s=s.replace('(rom_'+n+')','(native_mem_'+n+')')
 return s

def prepare(evidence,out):
 inputs=frame_prepare(evidence,out);diff=[]
 def edit(name,pairs):
  p=out/name;old=p.read_text();s=old
  for a,b in pairs:assert s.count(a)==1,(name,a,s.count(a));s=s.replace(a,b,1)
  undo=s
  for a,b in reversed(pairs):assert undo.count(b)==1;undo=undo.replace(b,a,1)
  assert undo==old
  p.write_text(s);diff.extend(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='frame165/'+name,tofile='memory165/'+name))
 slot='''// Qualified only for this fixed NTSC/MMC3 wrapper. No CPU/PPU CE is changed.
assign native_fill_slot=div_cpu==3 && scanline_ppu>=242 && scanline_ppu<260 &&
 !reset_noSS && !freeze_clocks && !corepause_active && !pause_cpu && !dma_aout_enable && !apu_dma_request &&
 cpu_rnw && cpu_addr[15];
'''
 edit('rtl/nes.v',[('module NES(','module NES(\noutput wire native_fill_slot,'),
  ('assign rom_cpu_address_valid=mr_int && prg_addr[15] && prg_allow;',slot+'assign rom_cpu_address_valid=mr_int && prg_addr[15] && prg_allow;')])
 edit('nes_probe.sv',[('module nes_probe(','module nes_probe(\noutput wire native_fill_slot,'),
  ('NES core(','NES core(.native_fill_slot(native_fill_slot),')])
 edit('nes_rom_service.sv',[('module nes_rom_early(','module nes_rom_early(\noutput wire native_core_safe,'),
  ('// Never steal or abort a read already accepted by the backend.',
   'assign native_core_safe=!reset&&!fault&&!busy&&!cpu_need&&!ppu_need&&!prefetch_need&&cpu_valid&&cpu_address_valid;\n// Never steal or abort a read already accepted by the backend.')])
 p=out/'nes_live_joint.sv';s=p.read_text();a=s.index('nes_spi_boot loader_boot(');b=s.index('wire rom_cpu_address_valid',a)
 loader=s[a:b]
 edit('nes_live_joint.sv',[('module nes_live_joint(','module nes_live_joint(\n'+PORTS),
  ('wire guard_allow,',WIRES+'\nwire guard_allow,'),(loader,backend_binding(loader)),
  ('nes_rom_early rom_service(','nes_rom_early rom_service(.native_core_safe(native_core_safe),'),
  (FRAME_BINDING,BINDING)])
 for n in FILES:shutil.copy2(ROOT/'src/nes/diagnostic'/n,out/n)
 (out/'native-memory-binding.diff').write_text(''.join(diff))
 return inputs
