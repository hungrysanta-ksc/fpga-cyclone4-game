# SPDX-License-Identifier: MIT
"""Add observational PPU ports and the NES-domain cache to a private 164 copy.

This is not a board build: the pixel buffer still exists and must be replaced.
No new host-domain input may be connected to these NES-domain control ports.
"""
from pathlib import Path
import difflib,json,shutil
from nes_game147 import ROOT,VHDL,SV,EXTRA,sha

PORTS='''input wire native_freeze,native_release_cache,native_query,
input wire [8:0] native_query_slot,
input wire [17:0] native_query_tag,
input wire [4:0] native_query_offset,
input wire native_query_obj4,
output wire native_initialized,native_owned,native_response,native_hit,
output wire [7:0] native_data,
output wire [15:0] native_valid_bytes,
'''
BINDING='''
// Same pre-edge logical/physical address and byte consumed by the real PPU.
// Do not substitute the registered debug out_ppumem_addr here.
nes_native_tap165 native_capture(
 .clk(clk),.reset(reset),.ppu_ce(tap_ce),.ppu_read(ppumem_read),
 .ppu_valid(rom_ppu_valid),.rom_fault(rom_fault),
 .ppu_logical(native_chr_logical),.ppu_physical(ppumem_addr),.ppu_data(ppumem_din),
 .freeze(native_freeze),.release_cache(native_release_cache),.query(native_query),
 .query_slot(native_query_slot),.query_tag(native_query_tag),
 .query_offset(native_query_offset),.query_obj4(native_query_obj4),
 .initialized(native_initialized),.owned(native_owned),.response(native_response),
 .hit(native_hit),.data(native_data),.valid_bytes(native_valid_bytes));
'''
NEW=['src/nes/diagnostic/nes_native_chr165.sv','src/nes/diagnostic/nes_native_tap165.sv']

def prepare(evidence,out):
    assert not out.exists() and str(out).isascii()
    manifest=evidence/'manifest.json'
    assert sha(manifest)==json.loads((ROOT/'analysis/game164-verification.json').read_bytes())['manifest_sha256']
    pins=json.loads(manifest.read_bytes())['files']
    out.mkdir(parents=True)
    inputs={}
    for n in VHDL+SV+EXTRA+['nes_live_joint.sv']:
        src=evidence/'asm'/n
        assert sha(src)==pins['asm/'+n],n
        dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
    changes=[]
    def edit(n,pairs):
        path=out/n;raw=path.read_bytes();text=raw.decode('utf8');original=text
        for old,new in pairs:
            assert text.count(old)==1,(n,old,text.count(old))
            text=text.replace(old,new,1)
        # Removing only the new observations must restore exact original bytes.
        undo=text
        for old,new in reversed(pairs):
            assert undo.count(new)==1
            undo=undo.replace(new,old,1)
        assert undo.encode('utf8')==raw,n
        path.write_bytes(text.encode('utf8'))
        changes.extend(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='164/'+n,tofile='native165/'+n))
    port='output wire [13:0] native_chr_logical,\n'
    edit('rtl/nes.v',[('module NES(','module NES(\n'+port),
         ('assign ppumem_addr  = chr_linaddr;','assign native_chr_logical = chr_addr;\nassign ppumem_addr  = chr_linaddr;')])
    edit('nes_probe.sv',[('module nes_probe(','module nes_probe(\n'+port),
         ('NES core(','NES core(\n.native_chr_logical(native_chr_logical),')])
    edit('nes_live_joint.sv',[('module nes_live_joint(','module nes_live_joint(\n'+PORTS),
         (' nes_probe dut(.*);',' wire [13:0] native_chr_logical;\n nes_probe dut(.*);'),
         ('assign out_cpumem_addr=cpumem_addr;',BINDING+'\nassign out_cpumem_addr=cpumem_addr;')])
    for n in NEW:shutil.copy2(ROOT/n,out/Path(n).name)
    (out/'native-binding.diff').write_text(''.join(changes),encoding='utf8')
    return inputs
