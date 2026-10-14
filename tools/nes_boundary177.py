# SPDX-License-Identifier: MIT
"""Replace ONLY low22 history bits with native ownership boundaries (tag6).

Upper74 bits, history RAM/sampling/STOP retention and all control stay174.
No loader/SPI/SDC changes. This is a cause-discrimination candidate, not a fix.
"""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha

CHANGED=['nes_native_export165.sv','nes_live_joint.sv']
FIELDS=['native_frame_owned','native_geometry_valid','native_initialized','native_active',
        'native_fill_busy','native_fill_done','native_fill_idle','native_fill_abort',
        'native_arbiter_fault','native_tx_valid','native_tx_ready','native_host_valid',
        'native_host_ready','native_release_frame']

def transform(name,s):
    def rep(a,b):
        nonlocal s
        assert s.count(a)==1,(name,a);s=s.replace(a,b)
    if name==CHANGED[0]:
        rep(' output wire busy,output reg [3:0] error',' output wire [3:0] observe_state177,\n output wire busy,output reg [3:0] error')
        rep(' assign busy=state!=IDLE;',' assign observe_state177=state;\n assign busy=state!=IDLE;')
    elif name==CHANGED[1]:
        rep('assign out_history157={scanline,cycle,history_flags157,rom_address,game148_hint_physical,ppumem_addr};',
            '//177: retain upper74 legacy bits; low22=tag6/state4/14 boundaries.\n'+
            "assign out_history157={scanline,cycle,history_flags157,rom_address,game148_hint_physical,\n 4'h6,native_export_state177,"+','.join(FIELDS)+'};')
        rep('wire native_host_valid;','wire [3:0] native_export_state177;\nwire native_host_valid;')
        rep('nes_native_export165 #(.MAX_CYCLES(33554432)) native_export(',
            'nes_native_export165 #(.MAX_CYCLES(33554432)) native_export(\n .observe_state177(native_export_state177),')
    else:raise ValueError(name)
    return s

def prepare(prior,out):
    assert not out.exists() and str(out).isascii();out.mkdir(parents=True)
    pins=json.loads((ROOT/'analysis/errorzero174-verification.json').read_bytes())['sources']
    for n,h in pins.items():
        assert sha(prior/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((prior/n).read_bytes())
    for n in CHANGED:(out/n).write_text(transform(n,(prior/n).read_text()),encoding='utf8',newline='\n')
    r=dict(sources={n:sha(out/n) for n in pins},baseline=pins,changed=CHANGED,
           public_sources={'tools/nes_boundary177.py':sha(Path(__file__))},history_low22_fields=FIELDS,
           history_upper74_unchanged=True,datapath_control_changed=False,extra_memory=False,hardware_package=False)
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.prior,a.out)
