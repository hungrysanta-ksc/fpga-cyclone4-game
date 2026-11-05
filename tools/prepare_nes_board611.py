"""Bind capture611 and the BG-preserving cache to the frozen physical board."""
import argparse,json,shutil
from pathlib import Path
from check_nes_wire600 import ROOT,pin,read,sha
from nes_raw506 import once

def prepare(base,out):
    manifest=read(ROOT/'analysis/whole580-manifest.json')['FPGA_inputs']
    for n,r in manifest.items():pin(base/n,r['sha256'])
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('db','incremental_db','output_files','simulation'))
    ports=''' input wire cap_start,cap_seal,cap_sample,
 input wire [15:0] cap_generation,
 input wire [16:0] cap_address,input wire [7:0] cap_data,
'''
    p=out/'nes_source_tile192.sv';s=p.read_text()
    s=once(s,' input wire clk,reset,stop,frame_owned,geometry_valid,',ports+''' input wire cap_release,input wire [15:0] cap_release_generation,
 output wire cap_ready,cap_sample_ready,
 input wire clk,reset,stop,frame_owned,geometry_valid,''')
    s=once(s,'nes_chr_cache192 cache(.clk(clk),.reset(reset),.flush(tile_cancel||denied||!immutable),.content_epoch(live_epoch),',
        '''// source_epoch207 asserts unavailable before every content epoch change.
  // Capture is allowed before the first display lease exists; queries still
  // require the original lease/epoch check in tile205.
  nes_chr_cache611 cache(.clk(clk),.reset(reset),.stop(tile_cancel||denied),
   .immutable(source_ready&&source_is_rom&&!source_writing),
   .start(cap_start),.seal(cap_seal),.release_bank(cap_release),
   .capture_gen(cap_generation),.release_gen(cap_release_generation),
   .sample(cap_sample),.sample_address(cap_address),.sample_data(cap_data),
   .start_ready(cap_ready),.sample_ready(cap_sample_ready),.request_obj(out_kind==1),''')
    p.write_text(s,newline='\n')
    p=out/'nes_direct206.sv';s=p.read_text()
    s=once(s,' input wire nes_clk,host_clk,reset,transport_fault,',ports+' input wire nes_clk,host_clk,reset,transport_fault,')
    s=once(s,'source(.clk(nes_clk),.reset(nr),.stop(nc),',
        '''source(.cap_start(cap_start),.cap_seal(cap_seal),.cap_sample(cap_sample),
  .cap_generation(cap_generation),.cap_address(cap_address),.cap_data(cap_data),
  .cap_release(retire_commit&&retire_permitted),.cap_release_generation(retire_generation),
  .cap_ready(),.cap_sample_ready(),.clk(nes_clk),.reset(nr),.stop(nc),''')
    p.write_text(s,newline='\n')
    p=out/'nes_live_joint.sv';s=p.read_text()
    s=once(s,'wire [2:0] native_patch_count181;','wire capture_begin611;\nwire [2:0] native_patch_count181;')
    s=once(s,'.capture_begin(),.source_ready(source_ready204)', '.capture_begin(capture_begin611),.source_ready(source_ready204)')
    s=once(s,'nes_direct206 direct_path(.nes_clk(clk)', '''nes_direct206 direct_path(
 .cap_start(capture_begin611),.cap_generation(native_generation+16'd1),
 .cap_seal(native_frame_owned&&native_geometry_valid),
 .cap_sample(native_active&&tap_ce&&native_obj_valid&&(native_obj_low||native_obj_high)&&
             ppumem_read&&rom_ppu_valid&&ppumem_addr[21:17]==5'h10),
 .cap_address(ppumem_addr[16:0]),.cap_data(ppumem_din),.nes_clk(clk)''')
    p.write_text(s,newline='\n')
    for n in ('nes_obj_capture611.sv','nes_chr_cache611.sv'):shutil.copy(ROOT/'rtl'/n,out/n)
    p=out/'board.qsf';s=p.read_text()
    s=once(s,'set_global_assignment -name SYSTEMVERILOG_FILE nes_chr_cache192.sv',
        'set_global_assignment -name SYSTEMVERILOG_FILE nes_chr_cache611.sv\nset_global_assignment -name SYSTEMVERILOG_FILE nes_obj_capture611.sv')
    p.write_text(s,newline='\n')
    (out/'inputs611.json').write_text(json.dumps({n:sha(out/n) for n in list(manifest)+['nes_obj_capture611.sv','nes_chr_cache611.sv']},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
