# SPDX-License-Identifier: MIT
"""Delay only the final 955 SEAL, preserving every preceding PUSH and CPU event."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from analyze_nes_bank621 import csv_groups, one
from analyze_nes_output615 import packets
from nes_raw506 import once


def seal_offset(folder):
    origin=one([e for e in csv_groups(folder/'window.csv')[954] if e['op']==3],'reveal')['clock']
    hdr,_,push=packets(folder)[955][-1]
    assert hdr[0]==3
    return push-origin


def run(a):
    a.frames=51
    delay=seal_offset(a.later)-seal_offset(a.trace) if a.later else 0
    assert delay>=0
    def probe(_,args,unused):
        # Reuse the bound consumer's observers, including true 624 raw DMA.
        s=(args.trace/'capture.lua').read_text(encoding='utf8')
        s=once(s,'local ROOT='+json.dumps(args.trace.resolve().as_posix()),'local ROOT='+json.dumps(args.out.as_posix()))
        s=once(s,"MODE=='normal'and 53 or","MODE=='normal'and 51 or")
        s=once(s,'checkedMem527(function()rpc()end','emu.addMemoryCallback(function()rpc()end')
        return once(s,'checkedEvent527(function()\n if sequence==1','emu.addEventCallback(function()\n if sequence==1')
    def edit(script):
        path=a.out/'arrivals.tsv'
        rows=path.read_text().splitlines()
        clock,head,bulk=rows[-2].split('\t')
        h=bytes.fromhex(head)
        assert h[0]==3 and int.from_bytes(h[8:10],'little')==955
        end=int(clock)+delay
        rows[-2:]=[f'{end}\t{head}\t{bulk}',f'{end+1}\tFINISH\t']
        path.write_text('\n'.join(rows)+'\n',newline='\n')
        return script
    def compare(before,after):
        cutoff=packets(a.trace)[955][-1][2]
        prefix=lambda rows:[r for r in rows if int(r['clock'])<cutoff]
        assert prefix(before)==prefix(after)
        if not delay:
            assert before==after
        tail=lambda rows:[r for r in rows if r['g']=='955' and r['op']=='3']
        return dict(delay=delay,prefix=len(prefix(after)),before=tail(before),after=tail(after))
    with patch.object(replay,'observe',probe):
        replay.run(a,edit_script=edit,compare_trace=compare)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','client','mesen','out','later'):
        p.add_argument('--'+key,type=Path,required=key!='later')
    run(p.parse_args())
