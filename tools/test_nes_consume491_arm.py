# SPDX-License-Identifier: MIT
"""Linked M4 bounded plan append: retained ownership guards and burst boundaries.

Endpoint instruction-clock delays are fixtures, not physical ARM/SPI/ROM time.
"""
import argparse,inspect,json
from pathlib import Path
import check_nes_supply485_arm as base

def burst(src,n):
    m=base.ARM(src,'normal');m.setup()
    assert m.emit(2,0,0)
    for i in range(1,n):assert m.emit(0,i,i)
    assert m.call('nes_plan200_finish',[m.p])==1
    e=m.endpoint;assert e.sent==e.retired==n and len(e.plans)==n and not e.jobs
    # No final display grant exists; EA must remain blocked after DMA completion.
    before=e.rearmed;assert not before and m.call('nes_plan200_retire',[m.p])==0 and not e.rearmed
    return {'plans':e.plans,'E0':sum(bytes.fromhex(q)[0]==0xe0 for q in e.calls),
            'E8':sum(bytes.fromhex(q)[0]==0xe8 for q in e.calls),
            'wire_B':sum(len(bytes.fromhex(q))for q in e.calls),'instructions':m.instructions,
            'E9_bytes':[q for q in e.calls if bytes.fromhex(q)[0]==0xe9]}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(exist_ok=False)
    s=inspect.getsource(base.run)
    old="and any(q['bulk'] for q in prefix[2:])"
    assert s.count(old)==1
    s=s.replace(old,"and all(q['accepted_E9']==1 and q['bulk']==0 for q in prefix[2:])")
    namespace=dict(base.__dict__);exec(compile(s,'491 bounded-append ownership','exec'),namespace)
    modes=['normal','normal_final_grant','normal_two_frames','bad_E8_CRC','wrong_generation','same_token_mutation','old_token','bad_ACK','bad_accepted','STOP_after_E9','STOP_after_bulk','ambiguous_E1']
    rows=[namespace['run'](a.arm,mode)for mode in modes]
    bursts=[]
    for n in [2,5,14,15,16,29,30,61]:
        old,new=burst(a.baseline,n),burst(a.arm,n)
        assert old['plans']==new['plans'] and old['E9_bytes']==new['E9_bytes']
        bursts.append({'n':n,'baseline':old,'candidate':new})
    result={'passed':True,'scope':__doc__,'firmware_SHA256':base.sha(a.arm/'obj-nes-100/firmware.stm'),
            'baseline_SHA256':base.sha(a.baseline/'obj-nes-100/firmware.stm'),
            'ownership_cases':rows,'bursts':bursts,'wire_ABI_changed':False,'physical_time':False}
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'ownership':len(rows),'bursts':len(bursts),
                      'fixture_E8':[(q['n'],q['baseline']['E8'],q['candidate']['E8'])for q in bursts]}))
