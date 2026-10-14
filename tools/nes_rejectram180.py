# SPDX-License-Identifier: MIT
"""Use the existing history RAM read register for previous-error comparison.

Same96-bit schema2 and MCU180. RUN reads last written entry; STOP reads SPI
index. An unavailable feedback value conservatively emits, never suppresses.
"""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_reject180 import replace


def transform(n,s):
    if n=='nes_reject_witness180.sv':
        s=replace(s,'input wire clk,reset,release_frame,collecting,owned,valid,',
            'input wire clk,reset,release_frame,collecting,owned,valid,\n input wire feedback_ready180,input wire [24:0] feedback_errors180,')
        s=replace(s,' reg [24:0] previous_signature;\n','')
        s=replace(s,'final_errors!=previous_signature','!feedback_ready180 || final_errors!=feedback_errors180')
        return replace(s,'else if(armed)begin previous_bad<=1;previous_signature<=final_errors;end','else if(armed)previous_bad<=1;')
    if n=='nes_ppu_history157.sv':
        s=replace(s,'// Passive last16 NES-clock samples, including the first fault edge.',
          '// Event ring. During RUN reuse RAM output to compare the last error; STOP selects SPI index.')
        s=replace(s,'output reg [55:0] page','output reg [55:0] page,output wire feedback_ready180,output wire [24:0] feedback_errors180')
        s=replace(s,'reg stopped,fault_seen;', '''reg stopped,fault_seen;
 reg feedback_pending180;
 wire run_read180=active && !stopped;
 wire write180=!reset && active && sample_enable && !stopped;
 wire [3:0] last_slot180=next_slot-4'd1;
 // After a write edge, the read still holds the old last slot. One more
 // edge loads the new slot. Invalid feedback must never suppress an event.
 assign feedback_ready180=run_read180 && count!=0 && !feedback_pending180 && !reset;
 assign feedback_errors180=read_data[85:61];''')
        s=replace(s,'read_data<=entries[command[4:1]];',
            'read_data<=entries[run_read180?last_slot180:command[4:1]];')
        s=replace(s,'if(!reset && active && sample_enable && !stopped)entries[next_slot]<=sample;',
            'if(write180)entries[next_slot]<=sample;')
        s=replace(s,'next_slot<=0;count<=0;stopped<=0;fault_seen<=0;',
            'next_slot<=0;count<=0;stopped<=0;fault_seen<=0;feedback_pending180<=0;')
        return replace(s,'  else begin\n   if(active', '  else begin\n   feedback_pending180<=write180;\n   if(active')
    if n=='nes_run_observer134.sv':
        s=replace(s,'output wire selected,output wire miso','output wire selected,output wire miso,\n output wire feedback_ready180,output wire [24:0] feedback_errors180')
        return replace(s,'.page(history_page157));','.page(history_page157),.feedback_ready180(feedback_ready180),.feedback_errors180(feedback_errors180));')
    if n=='nes_live_joint.sv':
        s=replace(s,'output wire [95:0] out_history157,output wire out_history_enable180,',
            'output wire [95:0] out_history157,output wire out_history_enable180,\ninput wire feedback_ready180,input wire [24:0] feedback_errors180,')
        return replace(s,'nes_reject_witness180 witness(',
            'nes_reject_witness180 witness(\n .feedback_ready180(feedback_ready180),.feedback_errors180(feedback_errors180),')
    if n=='fxpak_nes_screen137_top.sv':
        s=replace(s,'wire history_enable180;', 'wire history_enable180;wire feedback_ready180;wire [24:0] feedback_errors180;')
        for a in ['.out_history157(history_sample157)', '.history_sample157(history_sample157)']:
            s=replace(s,a,a+',.feedback_ready180(feedback_ready180),.feedback_errors180(feedback_errors180)')
        return s
    raise AssertionError(n)


CHANGED=['nes_reject_witness180.sv','nes_ppu_history157.sv','nes_run_observer134.sv','nes_live_joint.sv','fxpak_nes_screen137_top.sv']


def prepare(prior,out):
    pins=json.loads((ROOT/'analysis/reject180-verification.json').read_bytes())['verification']['sources']
    assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
    for n,h in pins.items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True)
        if n in CHANGED:p.write_text(transform(n,(prior/n).read_text()),encoding='utf8',newline='\n')
        else:p.write_bytes((prior/n).read_bytes())
    r=dict(baseline=pins,sources={n:sha(out/n) for n in pins},changed=CHANGED,
      public_sources={'tools/nes_rejectram180.py':sha(Path(__file__))},history_schema=2,hardware_package=False,
      scope=__doc__)
    assert sorted(n for n in pins if r['sources'][n]!=pins[n])==sorted(CHANGED)
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');return r


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
