# SPDX-License-Identifier: MIT
"""Bind the 951 budget to measured arrivals, receiver service, final DMA and fault tests."""
import argparse
import json
from pathlib import Path
from analyze_nes_map628 import csv_groups, ms, one, packets, read, sha
from analyze_nes_tail627 import deadlines
from replay_nes_map630 import pack

def run(a):
    phases=[]
    for phase in (1,2):
        base=a.traces/f'nes-seal625-tables-bg-{phase}'
        cutoff=deadlines(base)[951]['previous_cutoff']
        w=csv_groups(base/'window.csv')
        src=packets(base)[951]
        rows=[h for h,_,_ in src if h[1]==2 and int.from_bytes(h[10:12],'little')>=2048]
        assert len(rows)==8 and all(len(h)==208 and len(pack(h))==124 for h in rows)
        base_ack=one([r for r in w[951] if r['op']==3],'ack')['clock']
        summary={}
        for m in ('fixed','wire','priority','busy','ideal','ready','readybase'):
            suffix='b' if m=='readybase' else 'a'
            folder=a.traces/f'nes-map630-{m}-{phase}{suffix}'
            r=read(folder/'audit.json');result=read(folder/'result.json')
            assert result['passed'] and result['last_status']==1 and r['frames']==result['commits']==47
            observed=csv_groups(folder/'window.csv')
            show=lambda events:one([e for e in events[950] if e['op']==3],'reveal')['frame']
            assert show(observed)==show(w) and r['cutoff']==cutoff
            assert all(sha(folder/f'frame-{g}.rgb')==sha(base/f'frame-{g}.rgb') for g in range(905,952))
            tail=observed[951]
            r['ACK_delta_ms']=ms(one([e for e in tail if e['op']==3],'ack')['clock']-base_ack)
            if m=='readybase':
                indices=sorted({e['index'] for e in tail if e['section']==2})[2:]
                indices+=sorted({e['index'] for e in tail if e['section'] in (3,4,5)})
                assert len(indices)==24
                durations={};detail=[]
                for index in indices:
                    q=[e for e in tail if e['index']==index]
                    times=[one(q,k)['clock'] for k in ('load','data630','accepted630','ack')]
                    assert times==sorted(times)
                    parts=[ms(y-x) for x,y in zip(times,times[1:])]
                    detail.append({'index':index,'section':q[0]['section'],'op':q[0]['op'],'ms':parts})
                    for k,value in zip(('head_to_data','data_to_accepted','accepted_to_ACK'),parts):
                        durations[k]=durations.get(k,0)+value
                r['tail24']=durations;r['tail_packets']=detail
                seal=[e for e in tail if e['op']==3]
                r['head_to_upload_ms']=ms(one(seal,'upload165_entry')['clock']-one(seal,'load')['clock'])
                r['final_DMAs']=[(e['line'],e['value']) for e in seal if e['event']=='ppu_dma']
            summary[m]=r
        phases.append(summary)
    guards=read(a.traces/'nes-map630-guards03/guards.json')
    assert {r['boundary']:r['status'] for r in guards['cases']}=={**dict.fromkeys(('length','span','address','zero','cold'),224),'stop':228}
    assert guards['restart']==dict(commits=2,status=1,restored_map_bytes=16384)
    a.out.write_text(json.dumps(dict(phases=phases,guards=guards),indent=2)+'\n',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
