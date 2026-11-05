# SPDX-License-Identifier: MIT
"""Reject incomplete proofs and interrupt both early checks on the real CPU."""
import argparse
import json
from pathlib import Path
from check_nes_group628 import SAVE_MAPS, recover
from check_nes_tail631 import SAVE_REGIONS, cold_script
from replay_nes_seal632 import specialize
from nes_raw506 import once
from test_nes_seal538_stop import exercise


def run(a):
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    a.generation = 951
    prefix, rows = [], []
    for line in (a.trace/'packets.jsonl').read_text().splitlines():
        _, t, data, bulk = json.loads(line)
        h = bytes.fromhex(data)
        g = int.from_bytes(h[8:10], 'little')
        if g > 951:
            break
        if g == 951:
            rows.append((t, h, bulk))
        else:
            prefix.append(line)
    prefix.extend(json.dumps([0,t,h.hex(),bulk]) for t,h,bulk in specialize(rows,3))
    stream = a.out/'packets.jsonl'
    stream.write_text('\n'.join(prefix)+'\n')
    labels = json.loads((a.client/'labels.json').read_text())
    cases = {
        'hdma_format': ('pb(0)==2 and pb(1)==5 and pw(10)==1505',
                        'packet=packet:sub(1,17)..string.char(127)..packet:sub(19)'),
        'identity': ('pb(0)==9', 'packet=packet:sub(1,4)..string.char(pb(4)~1)..packet:sub(6)'),
        'orphan_seal': ('pb(0)==9', 'packet=string.char(2)..packet:sub(2,12)..string.pack("<I2I2",32,0)..packet:sub(17,48)'),
        'tile': ('pb(0)==9', """local found=false
 for j=0,143 do local missing=(~rd(0x1320+word(0x1254)+j))&255
  if missing~=0 then local at=48+j;packet=packet:sub(1,at)..string.char(pb(at)|missing)..packet:sub(at+2)
  found=true;break end end;assert(found)"""),
        'declaration': ('pb(0)==3', 'packet=packet:sub(1,38)..string.pack("<I2",7)'),
        'map': ('pb(0)==3', 'emu.write(0x1320+word(0x1254)+144,0,emu.memType.snesWorkRam)'),
        'cold': ('pb(0)==2 and pb(1)==2', 'packet=string.char(9)..packet:sub(2)'),
        'stop_tile': ('pb(0)==9', ''),
        'stop': ('pb(1)==5 and pw(10)==1748', ''),
    }
    records = []
    for kind, (condition, mutate) in cases.items():
        stop = kind.startswith('stop')
        status = 228 if stop else 224
        def inject(s):
            hook = labels['walk632' if kind=='stop_tile' else 'validate181']
            s = once(s,'local function loaded()',f"""local chosen=nil;local interrupted=false
emu.addMemoryCallback(function()if chosen and index==chosen then interrupted=true end end,emu.callbackType.exec,{hook})
local function loaded()""")
            s = once(s,' if pb(0)==7 then tile=file',f""" if pw(8)==FAULT and not chosen and {condition} then chosen=index;{mutate} end
 if pb(0)==7 then tile=file""")
            s = once(s,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",'')
            if stop:
                s = once(s,'if a==0x6001 then','if a==0x6001 then if interrupted then return 128 end')
            checks = f"assert(chosen and lastStatus=={status} and word(0x14d0)==0,'proof flag or fault status')"
            if kind=='stop':
                checks += SAVE_MAPS + SAVE_REGIONS
            return once(s,"assert(lastStatus==0xe4,'STOP status')",checks)
        gen = 906 if kind=='cold' else 951
        records.append(exercise(a,gen,kind,edit_packet_case=inject,reject_status=status,packet_trace=stream))
    cold = recover(a,receipt_tags=False,prepare_script=lambda out,s:cold_script(out,s,a.trace))
    (a.out/'guards.json').write_text(json.dumps(dict(cases=records,cold=cold),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','client','mesen','out'):
        p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
