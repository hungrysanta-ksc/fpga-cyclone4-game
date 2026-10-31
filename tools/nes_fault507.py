# SPDX-License-Identifier: MIT
"""507 same-edge SPI error-code factoring; preserve fault/STOP/response timing."""
import argparse,json,shutil
from pathlib import Path
from check_nes_game478 import sha

OLD="else if(!fault)error_code<=error_hard?4'd9:error_response?4'd7:error_overlap?4'd1:pending?decoded_error:4'd0;"
NEW="""else if(!fault)begin
   //507 Hard error9 sets bits0/3 and clears bits1/2 on THIS edge.
   // Lower-priority response7/overlap1/decoded errors remain bit-exact.
   // No diagnostic pipeline: snapshot and immediate cancellation stay atomic.
   error_code[0]<=error_hard || error_response || error_overlap || (pending && decoded_error[0]);
   error_code[1]<=!error_hard && (error_response || (!error_overlap && pending && decoded_error[1]));
   error_code[2]<=!error_hard && (error_response || (!error_overlap && pending && decoded_error[2]));
   error_code[3]<=error_hard || (!error_response && !error_overlap && pending && decoded_error[3]);
  end"""

def transform(s):
    assert s.count(OLD)==1
    return s.replace(OLD,NEW)

def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False)
    pins=json.loads((a.base/'source-pins.json').read_text())['board_inputs']
    for n,h in pins.items():
        assert sha(a.base/n)==h,n
        p=a.out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.base/n,p)
    for n in ['board.qpf','nominal204.sdc','timing506.tcl']:shutil.copy2(a.base/n,a.out/n)
    p=a.out/'nes_rom_spi.sv';p.write_text(transform(p.read_text()),encoding='utf8',newline='\n')
    new={n:sha(a.out/n)for n in pins};changed=[n for n in pins if new[n]!=pins[n]]
    assert changed==['nes_rom_spi.sv']
    r=dict(baseline=506,baseline_inputs=pins,board_inputs=new,changed=changed,extra_pipeline_clocks=0,extra_state_bits=0,scope=__doc__)
    (a.out/'source-pins.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps({'changed':changed}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['base','out']:p.add_argument('--'+n,type=Path,required=True)
    prepare(p.parse_args())
