# SPDX-License-Identifier: MIT
"""Inject STOP at the moved setup and both bounded wait phases on the real CPU."""
import argparse
import json
from pathlib import Path
from test_nes_seal538_stop import exercise
from nes_raw506 import sha, once


def run(a):
    a.out=a.out.resolve()
    a.out.mkdir(parents=True,exist_ok=a.resume)
    old=(a.base/'body.bin').read_bytes()
    new=(a.client/'body.bin').read_bytes()
    labels=json.loads((a.base/'labels.json').read_text())
    changed=[i for i,(b,c) in enumerate(zip(old,new)) if b!=c]
    allowed=set(range(labels['group_ready538']-0x7e2000,labels['group_ready538']-0x7e2000+3))
    allowed.update(range(labels['cancel169']-0x7e2000-8,labels['cancel169']-0x7e2000-6))
    assert set(changed)<=allowed and len(new)==len(old)+32
    cases=[]
    def cached(g,label):
        prior=a.out/f'{g}-{label}'
        if not (a.resume and (prior/'result.json').exists()):return None
        r=json.loads((prior/'result.json').read_text())
        assert r['passed'] and r['last_status']==228 and r['commits']==g-905
        assert sha(prior/'client.sfc')==sha(a.client/'sink165.sfc')
        assert sha(prior/'retained.rgb')==sha(a.trace/f'frame-{g-1}.rgb')
        return dict(generation=g,boundary=label,status=228,commits=r['commits'])
    for g,label in ((906,'prepare665'),(907,'prepare665'),(914,'active169'),
                    (914,'blank169'),(906,'raw_row489'),(907,'row624_0'),
                    (906,'final212'),(907,'final212')):
        cases.append(cached(g,label) or exercise(a,g,label))
    new_labels=json.loads((a.client/'labels.json').read_text())
    for label in ('active169','blank169'):
        name='timeout-'+label
        def timeout(s):
            s=once(s,'local function loaded()',f"""local timed665=false
emu.addMemoryCallback(function()
 if packet and pb(0)==3 and pw(8)==FAULT then
  timed665=true;emu.write(0x103e,1,emu.memType.snesWorkRam);emu.write(0x103f,0,emu.memType.snesWorkRam)
 end
end,emu.callbackType.exec,{new_labels[label]})
local function loaded()""")
            s=once(s,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",'')
            return once(s,"assert(lastStatus==0xe4,'STOP status')","assert(timed665 and lastStatus==0xe4,'wait bound')")
        cases.append(cached(914,name) or exercise(a,914,name,edit_packet_case=timeout))
    result=dict(passed=True,client_SHA256=sha(a.client/'sink165.sfc'),
                changed_existing_offsets=changed,new_body_B=len(new)-len(old),
                unchanged_independent_check_and_final_gate=True,cases=cases)
    (a.out/'guards.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--resume',action='store_true')
    for k in ('client','base','trace','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
