# SPDX-License-Identifier: MIT
"""Check matched issue clocks, classify individual 4B checks, and bind fault results."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
from analyze_nes_map628 import ms, read, sha

def retained(folder):
    cost=Counter()
    count=Counter()
    previous=None
    changed=False
    for idx,label,t in csv.reader((folder/'profile.csv').open()):
        if label=='group628':
            changed=False
        elif label=='copy628':
            changed=True
        elif label=='rowcontrol':
            assert previous[:2]==(idx,'verify628')
            key='changed' if changed else 'retained'
            cost[key]+=int(t)-previous[2]
            count[key]+=1
        previous=idx,label,int(t)
    assert count=={'retained':356,'changed':28}
    return {k:ms(v) for k,v in cost.items()}

def analyze(a):
    phases=[]
    for i in (1,2):
        rows={}
        for paced,modes in [(False,['base','literal','group','split']),(True,['group','split'])]:
            reference=None
            for mode in modes:
                d=a.root/f"nes-map629-{mode}-{i}{'paced' if paced else 'a'}"
                r=read(d/'audit.json')
                arrivals=(d/'arrivals.tsv').read_text().splitlines()[:-1]
                targets=[int(line.split('\t')[0]) for line in arrivals]
                # Compare every published clock, even when credit forces the consumer to defer.
                if reference is None:reference=targets
                assert targets==reference
                admitted=list(csv.DictReader((d/'admit.csv').open()))
                assert list(map(int,(r['target'] for r in admitted)))==targets
                deferred=[int(v['observed'])-int(v['target']) for v in admitted if int(v['blocked'])]
                r['max_credit_delay_ms']=ms(max(deferred,default=0))
                if mode=='group':r['checksum_only_ms']=retained(d)
                rows[('paced_' if paced else '')+mode]=r
        assert rows['group']['offers_sha']==rows['split']['offers_sha']
        assert rows['paced_group']['offers_sha']==rows['paced_split']['offers_sha']
        phases.append(rows)
    guards=read(a.root/'nes-map629-guards/result.json')
    assert len(guards['guards'])==7 and guards['restart']['commits']==2
    assert all(r['status']==(228 if r['boundary']=='stop' else 224) for r in guards['guards'])
    client=phases[0]['split']['client_sha']
    for r in guards['guards']:
        assert sha(a.root/'nes-map629-guards'/f"{r['generation']}-{r['boundary']}"/'client.sfc')==client
    target=(a.root/'nes-map628-checked-1/map-951.bin').read_bytes()
    rows=[target[i:i+64] for i in range(2048,3584,64)]
    assert all(r[32:34]!=bytes(2) and r[34:]==bytes(30) for r in rows)
    a.out.write_text(json.dumps(dict(phases=phases,guards=guards,right_rows=len(rows),zero_suffix_bytes=30),indent=2)+'\n',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','out'):p.add_argument('--'+name,type=Path,required=True)
    analyze(p.parse_args())
