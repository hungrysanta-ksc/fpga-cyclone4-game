"""Verify the measured limits, field packet bounds and replay controls for MMC1028."""
import json
import re
from pathlib import Path
from prepare_nes_kirby1028 import WORK, ROOT, RATE
from read_nes_tail1012 import ARM_TICK, decode

def read(version, phase, mode):
    log=(WORK/f'run-{version}-{phase}-{mode}.log').read_text(errors='replace')
    passed,=re.findall(r'^# PASS1028 (.*)$',log,re.M)
    assert 'Fatal:' not in log and 'Errors: 0' in log
    r={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',passed)}
    assert (r['version'],r['phase'],r['mode'])==(version,phase,mode)
    return r

def summarize(downloads):
    result=json.loads((WORK/'inputs.json').read_text())
    result['field_counts']=[]
    for trial in (1,2):
        path,=downloads.glob(f'nes-frame-mmc1027-{trial}*.bin')
        rows=decode(path.read_bytes(),1027)['rows']
        observed=[r['last_slot_run']['ms_from_first_E9'] for r in rows if
                  'ms_from_first_E9' in r.get('last_slot_run',{})]
        waits=[r['first_grant']-r['first_request'] for r in observed if 'first_grant' in r]
        result['field_counts'].append(dict(trial=trial,eligible=len(observed),with_foreground=len(waits),
                                           first_wait_ge_8ms=sum(w>=8 for w in waits)))
    for case in result['cases']:
        p=case['phase']
        modes=[0,1,2,4]+([8,9] if p<=2 else [])
        ref={m:read(0,p,m) for m in modes}
        cand={m:read(1,p,m) for m in modes+[5,6,7]}
        assert all(r['bytes']==case['bytes'] for rs in (ref,cand) for r in rs.values())
        assert cand[0]['done']<ref[0]['done'] and cand[0]['fg']==0 and ref[0]['early']==0
        for m in (1,2):
            assert all(ref[m][k]==cand[m][k] for k in ref[m] if k!='version')
        assert cand[4]['early']==ref[4]['early']==0
        if p<=2:
            assert cand[8]['seal']<4000 and cand[9]['seal']<4000
            assert cand[8]['hint']<4000<cand[9]['hint']
            assert cand[8]['done']<ref[8]['done'] and cand[9]['done']==ref[9]['done']
            assert cand[6]['fg']==0 and cand[7]['fg']>0
            previous_window=case['replay_first_window']
            case['latest_tested_full_prefetch_seal_after_first_E9_ms']=round(
                case['prior_window_first_after_first_E9_estimate_ms']+(cand[6]['seal']-previous_window[0])/RATE,4)
            path,=downloads.glob(f'nes-frame-mmc1027-{p}*.bin')
            trace=decode(path.read_bytes(),1027)
            sample,=[s for s in trace['samples'] if s['generation']==case['gen']]
            prior,obj,seal=sample['packets'][-3:]
            assert [q['op'] for q in (prior,obj,seal)]==[9,7,3] and prior['section']==4 and obj['offset']==384
            case['physical_ARM_ms_after_BEGIN']={name:round(q[k]*ARM_TICK,4) for name,q,k in
                [('op9_sent',prior,'sent'),('last_OBJ_issue',obj,'issue'),('SEAL_issue',seal,'issue')]}
            case['upper_bound_OBJ_issue_gain_ms_same_prior_send'] = round((obj['issue']-prior['sent']+2)*ARM_TICK,4)
        case['max_intergrant_row_control']=dict(tile_index=ref[0]['delayed_tile_row']//8,row=ref[0]['delayed_tile_row']%8,
            ms=round(ref[0]['max_intergrant']/RATE,5))
        case['advance_final_tile_ms']={m:round((ref[m]['done']-cand[m]['done'])/RATE,5) for m in modes}
        case['baseline']=ref
        case['candidate']=cand
    assert 'PASS1028_STOP' in (WORK/'run-1-1-3.log').read_text()
    result['scope']='Real compact records from source frame 3570 in slot order, private Kirby CHR, a qualified boot-ROM calendar aligned to field delays. Cache contents, final E9 arrival and mailbox ownership are controlled; field tags, per-row grants and candidate display/ACK are unmeasured.'
    result['modes']={0:'early final bank, unarmed',1:'preceding demand arms existing policy',
        2:'sealed after grant window',3:'STOP during speculative transaction',4:'unarmed but occupied conflicting indices',
        5:'32 grants remaining',6:'16 grants remaining',7:'8 grants remaining',
        8:'early host seal, preceding two-record bank releases before window',
        9:'early host seal, preceding two-record bank releases after window'}
    (ROOT/'analysis/kirby1028-prefetch.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('downloads',type=Path)
    for case in summarize(p.parse_args().downloads)['cases']:
        print(case['phase'],case['advance_final_tile_ms'])
