# SPDX-License-Identifier: MIT
"""Reproducible passive witness on pinned178 sources, using the existing ring."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha


def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)


def prepare(prior,out):
    pins=json.loads((ROOT/'analysis/clip178-pair-verification.json').read_bytes())['verification']['sources']
    assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
    for n,h in pins.items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((prior/n).read_bytes())
    changed=[]
    def edit(n,fn):
        p=out/n;p.write_text(fn(p.read_text()),encoding='utf8',newline='\n');changed.append(n)
    def frame(s):
        s=replace(s,'output reg [24:0] errors,output wire scroll_seen,',
            'output reg [24:0] errors,output wire [24:0] observe_errors180,\n output wire observe_collecting180,output wire scroll_seen,')
        return replace(s,'wire member_hit=',
            'assign observe_errors180={rom_fault,raster_errors,compact_errors,fetch_errors};\n assign observe_collecting180=joining || owned;\n wire member_hit=')
    edit('nes_native_frame165.sv',frame)
    def core(s):
        s=replace(s,'output wire [95:0] out_history157,','output wire [95:0] out_history157,output wire out_history_enable180,')
        a=s.index('//177: retain upper74');b=s.index('nes_rom_early rom_service',a)
        s=s[:a]+'''//180: passive admission transitions, same 16x96 observer RAM.
wire [24:0] native_observe_errors180;wire native_collecting180;
nes_reject_witness180 witness(
 .clk(clk),.reset(reset),.release_frame(native_release_frame),.collecting(native_collecting180),
 .owned(native_frame_owned),.valid(native_geometry_valid),.generation(native_generation),
 .live_errors(native_observe_errors180),.final_errors(native_errors),
 .scanline(scanline),.dot(cycle),.mask(native_display_mask),
 .rows(native_row_count),.groups(native_group_count),.objects(native_object_count),
 .exceptions(native_exception_count),.palettes(native_palette_count),
 .sample_enable(out_history_enable180),.sample(out_history157));
'''+s[b:]
        return replace(s,'.generation(native_generation),.errors(native_errors),',
            '.observe_errors180(native_observe_errors180),.observe_collecting180(native_collecting180),\n .generation(native_generation),.errors(native_errors),')
    edit('nes_live_joint.sv',core)
    def top(s):
        s=replace(s,'wire [95:0] history_sample157;','wire [95:0] history_sample157;wire history_enable180;')
        s=replace(s,'.out_history157(history_sample157)', '.out_history157(history_sample157),.out_history_enable180(history_enable180)')
        return replace(s,'.history_sample157(history_sample157)', '.history_sample157(history_sample157),.history_enable180(history_enable180)')
    edit('fxpak_nes_screen137_top.sv',top)
    def observer(s):
        s=replace(s,'input wire [95:0] history_sample157,','input wire [95:0] history_sample157,input wire history_enable180,')
        return replace(s,'.sample(history_sample157),','.sample_enable(history_enable180),.sample(history_sample157),')
    edit('nes_run_observer134.sv',observer)
    def ring(s):
        s=replace(s,'input wire clk,reset,active,freeze,','input wire clk,reset,active,freeze,sample_enable,')
        assert s.count('active && !stopped')==2
        s=s.replace('active && !stopped','active && sample_enable && !stopped')
        return replace(s,"8'd1,8'd96,8'd1","8'd1,8'd96,8'd2")
    edit('nes_ppu_history157.sv',ring)
    n='nes_reject_witness180.sv';(out/n).write_bytes((ROOT/'src/nes/diagnostics'/n).read_bytes())
    edit('board.qsf',lambda s:s+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_reject_witness180.sv\n')
    sources={n:sha(out/n) for n in [*pins,'nes_reject_witness180.sv']}
    assert sorted(n for n in pins if sources[n]!=pins[n])==sorted(changed)
    r=dict(baseline=pins,sources=sources,changed=changed,added=['nes_reject_witness180.sv'],
       public_sources={n:sha(ROOT/n) for n in ['tools/nes_reject180.py','src/nes/diagnostics/nes_reject_witness180.sv']},
       history_schema=2,hardware_package=False)
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');return r


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
