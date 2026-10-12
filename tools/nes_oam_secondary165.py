# SPDX-License-Identifier: MIT
"""Factor secondary OAM writers with explicit per-byte priority, no added cycle."""
from pathlib import Path
import argparse,difflib,json,re
from nes_game147 import sha
from nes_oam_port165 import prepare as prepare_range

def transform(text,variant='valid-mask'):
    start=text.index('module OAMEval(');end=text.index('endmodule',start)
    old=text[start:end];s=old
    writes=["oam_temp <= '{64{8'hFF}};",
        'oam_temp[oam_row_cur] <= oam_temp[oam_row_last];',
        "oam_temp[oam_secondary_addr] <= 8'hFF;",
        "oam_temp[{1'b1, oam_secondary_addr}] <= 8'hFF;",
        'oam_temp[oam_secondary_addr] <= oam_dbus;']
    writes += ["oam_temp[{1'b1, oam_secondary_row_ex[2:0], 2'b"+f'{i:02b}'+"}] <= oam_read({oam_addr_ex, 2'b"+f'{i:02b}'+"});" for i in range(4)]
    for w in writes:
        assert s.count(w)==1,w
        # Preserve single-statement conditional grammar after removing its write.
        s=s.replace(w,'begin /* secondary writer factored below */ end')
    assert not re.search(r'oam_temp[^;\n]*<=',s)
    common='''
// Per-byte priority matches the original source order: reset > clear/eval > copy.
wire temp_clear = ce && rendering && cycle < 64 && secondary_write && oam_wr_enabled;
wire temp_eval = ce && rendering && cycle >= 64 && cycle < 256 &&
 (evaluating || (visible && PAL));
wire temp_load = temp_eval && secondary_write && oam_wr_enabled && ~n_ovr;
wire temp_extra = temp_eval && (&spr_counter) && ~ex_ovr && oam_secondary_row_ex < 8 &&
 scanline[7:0] >= oam_read({oam_addr_ex, 2'b00}) &&
 scanline[7:0] < oam_read({oam_addr_ex, 2'b00}) + (obj_size ? 16 : 8);
wire [7:0] temp_copy_data = oam_temp[oam_row_last];
'''
    writers='''
genvar temp_index;
generate for(temp_index=0;temp_index<32;temp_index=temp_index+1)begin:secondary_byte
 always @(posedge clk)begin
  if(reset || (temp_clear && oam_secondary_addr==temp_index))oam_temp[temp_index]<=8'hff;
  else if(temp_load && oam_secondary_addr==temp_index)oam_temp[temp_index]<=oam_dbus;
  else if(oam_copy_write && oam_row_cur==temp_index)oam_temp[temp_index]<=temp_copy_data;
 end
 always @(posedge clk)begin
  if(reset || (temp_clear && oam_secondary_addr==temp_index))oam_temp[32+temp_index]<=8'hff;
  else if(temp_extra && oam_secondary_row_ex[2:0]==temp_index/4)
   oam_temp[32+temp_index]<=oam_read({oam_addr_ex,2'b00}+temp_index%4);
 end
end endgenerate
'''
    if variant=='valid-mask':
        declaration='''reg [7:0] temp_storage[0:63];
reg [63:0] temp_valid;
wire [7:0] oam_temp[0:63];
genvar observed_temp;
generate for(observed_temp=0;observed_temp<64;observed_temp=observed_temp+1)begin:secondary_observation
 assign oam_temp[observed_temp]=temp_valid[observed_temp] ? temp_storage[observed_temp] : 8'hff;
end endgenerate'''
        assert s.count('reg [7:0] oam_temp[64];')==1
        s=s.replace('reg [7:0] oam_temp[64];',declaration)
        # Keep the observation array for the unchanged differential bench. Main
        # consumers mask after address selection, not separately in all 64 words.
        for expr in ['oam_secondary_addr',"6'd32","6'd33","6'd34"]+[
                "{1'b1, oam_secondary_addr[4:2], 2'b"+f'{i:02b}'+'}' for i in range(4)]:
            s=s.replace('oam_temp['+expr+']','secondary_read('+expr+')')
        common=common.replace('oam_temp[oam_row_last]','secondary_read(oam_row_last)')
        writers='''
genvar temp_index;
generate for(temp_index=0;temp_index<32;temp_index=temp_index+1)begin:secondary_byte
 wire clear_byte=temp_clear && oam_secondary_addr==temp_index;
 wire load_byte=temp_load && oam_secondary_addr==temp_index;
 wire copy_byte=oam_copy_write && oam_row_cur==temp_index;
 wire extra_byte=temp_extra && oam_secondary_row_ex[2:0]==temp_index/4;
 // Only validity needs reset/clear. Hidden storage may update while invalid;
 // every transition back to valid writes fresh data on that same edge.
 always @(posedge clk)begin
  if(reset || clear_byte)temp_valid[temp_index]<=0;
  else if(load_byte || copy_byte)temp_valid[temp_index]<=1;
  if(load_byte)temp_storage[temp_index]<=oam_dbus;
  else if(copy_byte)temp_storage[temp_index]<=temp_copy_data;
 end
 always @(posedge clk)begin
  if(reset || clear_byte)temp_valid[32+temp_index]<=0;
  else if(extra_byte)temp_valid[32+temp_index]<=1;
  if(extra_byte)temp_storage[32+temp_index]<=oam_read({oam_addr_ex,2'b00}+temp_index%4);
 end
end endgenerate
'''
    else:assert variant=='factored'
    s+=common+writers
    if variant=='valid-mask':
        # Explicit memory/valid operands also track changes when the address is
        # constant; avoid simulator sensitivity to globals hidden in a function.
        s=re.sub(r'secondary_read\(([^()]*)\)',lambda m:"(temp_valid["+m[1]+"] ? temp_storage["+m[1]+"] : 8'hff)",s)
    return text[:start]+s+text[end:]

def prepare(baseline,out,variant='valid-mask'):
    prepare_range(baseline,out)
    p=out/'rtl/ppu.sv';before_hash=sha(p);before=p.read_text();after=transform(before,variant)
    p.write_text(after,encoding='utf8')
    (out/'secondary.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='range165/rtl/ppu.sv',tofile='secondary165/rtl/ppu.sv')),encoding='utf8')
    m=json.loads((out/'preparation.json').read_bytes());m['variant']='secondary-'+variant+'-area'
    m['range_source_sha256']=before_hash
    m['sources']['rtl/ppu.sv']=sha(p);m['public_sources']['tools/nes_oam_secondary165.py']=sha(Path(__file__))
    (out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--variant',choices=['factored','valid-mask'],default='valid-mask')
    a=p.parse_args();prepare(a.baseline,a.out,a.variant)
