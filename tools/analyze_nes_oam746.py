# SPDX-License-Identifier: MIT
"""Reconcile checked credit, actual OAM writes, both PPU DMA starts and final ACK."""
import argparse
import json
from pathlib import Path

from analyze_nes_beam741 import records
from analyze_nes_bg745 import timeline
from analyze_nes_owner739 import read, sha, csv_groups


def analyze(a):
    previous=read(Path('analysis/bg745-verification.json'))
    result=dict(stage=746,reference=727,ROM=previous['ROM'],ARM={},phases={},faults={})
    for key in ('long','normal','split','short'):
        src=a.probe/key/'src'
        fw=src/'obj-nes-100/firmware.stm'
        pin=sha(fw)
        guards={k:read(a.probe/f'{key}-{k}.json') for k in ('menu533','deadline719','receipt742','bg745','guard')}
        assert all(g['firmware']==pin for g in guards.values())
        assert len(guards['deadline719']['cases'])==17 and len(guards['receipt742']['rows'])==9
        menu=guards['menu533']
        assert menu['marker_cases']==4 and len(menu['rows'])==5 and all(bool(v['released'])==(k=='normal') for k,v in menu['rows'].items())
        assert len(guards['bg745']['cases'])==6 and len(guards['guard']['rows'])==7
        size=(a.probe/key/'size.log').read_text().splitlines()[-1].split()
        result['ARM'][key]=dict(size_B=fw.stat().st_size,free_B=212992-fw.stat().st_size,sha256=pin,
             text=int(size[0]),data=int(size[1]),bss=int(size[2]),guards={k:sha(a.probe/f'{key}-{k}.json') for k in guards},
             prepared_source={f.name:sha(src/f.name) for f in (a.probe/('patch-'+key)).glob('*') if f.is_file()},
             credit_cases=guards['guard']['rows'])
    for n in (1,2):
        base=a.temp/f'nes-pair727-a{n}'
        variants={}
        result['phases'][n]=variants
        for k in ('ref','long','split','matched','pieces'):
            folder=base if k=='ref' else a.temp/f'nes-oam746-{k}{n}'
            run=timeline(folder,base)
            variants[k]=run
            j=read(folder/'joint.json')
            run['stack_low']=j['observed_stack_low']
            run['workspace_end']=j['workspace_end']
            run['ACK_delta_clocks']=run['final_ACK']-variants['ref']['final_ACK']
            if k=='ref':continue
            events=read(folder/'events.json')
            if k in ('long','split'):
                observations=[x for x in events if x.get('event')=='OAM746']
                assert observations and run['firmware']==result['ARM'][k]['sha256']
                for x in observations:
                    assert sum(y['count'] for y in x['segments'])==116,x
                run['OAM_checked']=len(observations)
                run['OAM957']=[x for x in observations if x['generation']==957]
                assert len(run['OAM957'])==1
            else:
                edges=[x for x in events if x.get('event')=='credit746']
                assert run['map_issue']['changed']==0 and edges[0]['point']=='start746'
                assert edges[-1]['point']=='checked' and edges[-1]['done']==116
                assert any(x['point']=='written' and x['done']==116 for x in edges)
                assert run['firmware']==variants['ref']['firmware']
                run['OAM957']=edges
            last_map=run['order957']['long_map']
            if last_map:
                rows=csv_groups(folder/'window.csv')[957]
                run['after_map']=next(x for x in rows if x['clock']>last_map['end'] and x['event'] in ('load','ppu_dma'))
            run['E0_offset_from_map_ACK']=[x['start']-run['map_last_ACK'] for x in run['map_to_OBJ_SPI'] if x['op']=='0xe0']
            for tag in ('stop','stale'):
                d=a.temp/f'nes-oam746-{k}{n}-{tag}'
                if not d.exists():continue
                sr=read(d/'result.json')
                assert sr['passed'] and sr['commits']==52
                assert sha(d/'retained.rgb')==sha(base/'frame-956.rgb')
                result['faults'][f'{k}{n}-{tag}']=dict(commits=52,status=sr['last_status'],result=sha(d/'result.json'))
            for fault in ('pre','during','head'):
                d=a.temp/f'nes-oam746-{k}{n}-{fault}'
                if not d.exists():continue
                point=int((d/'fault745.txt').read_text())
                rows=csv_groups(d/'window.csv')[957]
                obj=[x for x in records(d/'dma745.csv') if x['g']==957 and x['src']==19104]
                outcome=read(d/'result.json')
                assert outcome['passed']
                if fault=='head':
                    first=next(x for x in rows if x['clock']>point and x['event'] in ('load','ppu_dma'))
                    assert first['event']=='load' and first['section']==5
                    assert outcome['commits']==53 and [x['n'] for x in obj]==[288]
                else:
                    assert outcome['commits']==52 and [x['n'] for x in obj]==([] if fault=='pre' else [64])
                    assert not any(x['op']==3 and x['event']=='ack' for x in rows)
                    assert sha(d/'retained.rgb')==sha(base/'frame-956.rgb')
                result['faults'][f'{k}{n}-{fault}']=dict(at=point,window=sha(d/'window.csv'),OBJ_MDMAEN=[x['n'] for x in obj],commits=outcome['commits'])
    required={f'long{n}-{fault}' for n in (1,2) for fault in ('stop','stale')}
    required.update(f'{case}-{fault}' for case in ('matched1','long2') for fault in ('pre','during','head'))
    assert required<=result['faults'].keys()
    result['probe_sha256']=sha(a.probe/'probe.elf')
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('temp','probe','out'):p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
