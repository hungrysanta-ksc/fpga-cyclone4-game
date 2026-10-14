# SPDX-License-Identifier: MIT
"""Reuse invalid first-PPU-context storage until the first ROM fault owns it.

No extra payload registers. First fault has unconditional priority and freezes
the event ring. Valid ROM context bytes and schema2 history stay unchanged;
payload of an INVALID ROM-context response is deliberately unspecified.
"""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_reject180 import replace

CHANGED=['nes_run_observer134.sv','nes_live_joint.sv','fxpak_nes_screen137_top.sv']


def transform(n,s):
    if n=='nes_live_joint.sv':
        s=replace(s,'output wire out_history_enable180,','output wire out_history_owned180,out_history_release180,out_history_collecting180,\noutput wire [24:0] out_history_live_errors180,')
        a=s.index('nes_reject_witness180 witness(');b=s.index('nes_rom_early rom_service',a)
        s=s[:a]+'''// Ownership state lives in observer context storage only while context_valid=0.
assign out_history_owned180=native_frame_owned;
assign out_history_release180=native_release_frame;
assign out_history_collecting180=native_collecting180;
assign out_history_live_errors180=native_observe_errors180;
assign out_history157={native_geometry_valid?2'd2:2'd1,native_generation[7:0],native_errors,
 scanline,cycle,native_display_mask,native_row_count,native_group_count,
 native_object_count,native_exception_count,native_palette_count[5]?5'd31:native_palette_count[4:0]};
'''+s[b:]
        return s
    if n=='fxpak_nes_screen137_top.sv':
        s=replace(s,'wire history_enable180;', 'wire history_owned180,history_release180,history_collecting180;wire [24:0] history_live_errors180;')
        s=replace(s,'.out_history_enable180(history_enable180)', '.out_history_owned180(history_owned180),.out_history_release180(history_release180),.out_history_collecting180(history_collecting180),.out_history_live_errors180(history_live_errors180)')
        return replace(s,'.history_enable180(history_enable180)', '.history_owned180(history_owned180),.history_release180(history_release180),.history_collecting180(history_collecting180),.history_live_errors180(history_live_errors180)')
    if n=='nes_run_observer134.sv':
        s=replace(s,'input wire history_enable180,','input wire history_owned180,history_release180,history_collecting180,\n input wire [24:0] history_live_errors180,')
        s=replace(s,' reg miso_hold;', ''' reg miso_hold;
 // Before a ROM fault the context-valid bit is zero: its payload is private
 // scratch. [63:60]=armed/owned-seen/first-seen/previous-bad,
 // [59:35]=previous25-bit error, [34:9]=first line/dot/mask. At first fault
 // the FULL original PPU snapshot replaces this state with higher priority.
 wire live_first180=history_collecting180 && |history_live_errors180;
 wire valid180=history_sample157[95:94]==2;
 wire new_owner180=history_owned180 && !first_ppu154[62] && !history_release180 && !core_reset && !reset && !context_valid;
 wire history_emit180=new_owner180 && first_ppu154[63] &&
  (valid180?first_ppu154[60]:(!first_ppu154[60] || history_sample157[85:61]!=first_ppu154[59:35]));
 wire [25:0] position180=first_ppu154[61]?first_ppu154[34:9]:
  live_first180?history_sample157[60:35]:{9'd511,9'd511,8'd0};
 wire [95:0] event180={history_sample157[95:61],position180,history_sample157[34:0]};''')
        s=replace(s,'.sample_enable(history_enable180),.sample(history_sample157),', '.sample_enable(history_emit180),.sample(event180),')
        anchor='if(fault_trigger && !context_valid)begin context_valid<=1;first_context<=fault_context;first_ppu154<=ppu_fault_state154;end'
        return replace(s,anchor,anchor+'''
   else if(!context_valid)begin
    if(core_reset)first_ppu154<=0;
    else begin
     if(!history_owned180)first_ppu154[62]<=0;
     if(history_release180)begin first_ppu154[61]<=0;first_ppu154[62]<=0;end
     else begin
      if(first_ppu154[63] && !first_ppu154[61] && live_first180)begin
       first_ppu154[61]<=1;first_ppu154[34:9]<=history_sample157[60:35];
      end
      if(new_owner180)begin
       first_ppu154[62]<=1;
       if(valid180)begin first_ppu154[63]<=1;first_ppu154[60]<=0;end
       else if(first_ppu154[63])begin first_ppu154[60]<=1;first_ppu154[59:35]<=history_sample157[85:61];end
      end
     end
    end
   end''')
    raise AssertionError(n)


def prepare(prior,out):
    pins=json.loads((ROOT/'analysis/reject180-verification.json').read_bytes())['verification']['sources']
    assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
    for n,h in pins.items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True)
        if n in CHANGED:p.write_text(transform(n,(prior/n).read_text()),encoding='utf8',newline='\n')
        else:p.write_bytes((prior/n).read_bytes())
    r=dict(baseline=pins,sources={n:sha(out/n) for n in pins},changed=CHANGED,
       public_sources={'tools/nes_rejectstorage180.py':sha(Path(__file__))},history_schema=2,hardware_package=False,scope=__doc__)
    assert sorted(n for n in pins if r['sources'][n]!=pins[n])==sorted(CHANGED)
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');return r


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
