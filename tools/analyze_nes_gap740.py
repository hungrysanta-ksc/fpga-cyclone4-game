# SPDX-License-Identifier: MIT
"""Check the 727 fixed-map offer experiment against CPU times and the same absolute beam."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_owner739 import csv_groups, ms, packets, read, sha
from replay_nes_gap740 import schedule


def measure(base, folder, reference):
    expected = read(folder/'schedule.json')
    assert expected==schedule(base,expected['phase'],expected['policy'])
    rows=csv_groups(folder/'window.csv')
    original=csv_groups(base/'window.csv')
    assert read(folder/'audit.json')['prefix_events']==sum(len(v) for g,v in original.items() if g<957)
    actions=rows[957]
    loads=[r for r in actions if r['event']=='load']
    acks=[r for r in actions if r['event']=='ack']
    heads=packets(base)[957]
    assert len(loads)==len(acks)==len(heads)
    final=lambda g,event: next(r for r in rows[g] if r['op']==3 and r['event']==event)
    origin=final(956,'reveal')['clock']
    cutoff=reference['deadline_line247_start']
    obj=next(i for i,(h,b,t) in enumerate(heads) if t==expected['first'])
    oam=obj+1
    assert heads[oam][0][:2]==bytes((9,4))
    taps=list(csv.DictReader((folder/'owner.csv').open()))
    proven=next(int(r['clock']) for r in taps if r['event']=='proven635')
    assert loads[oam]['clock']<=proven<acks[oam]['clock']
    assert final(956,'reveal')==next(r for r in original[956] if r['event']=='reveal')
    for r in taps:
        if r['event']=='beam' and int(r['frame'])==final(956,'reveal')['frame']+2:
            assert abs(int(r['clock'])-int(r['value'])+(247-int(r['line']))*1364-cutoff)<=4
    # Check every PUSH, including payload and token, against the immutable input.
    expected_rows=[]
    for line in (base/'packets.jsonl').read_text().splitlines():
        _,clock,h,b=json.loads(line)
        shift=expected['shift'] if expected['first']<=clock<=expected['last'] else 0
        if 'scroll' in expected and clock>=expected['scroll']:
            shift=expected['tail_shift']
        expected_rows.append(f'{clock-shift}\t{h}\t{b}')
    assert (folder/'arrivals.tsv').read_text().splitlines()[:-1]==expected_rows
    times={}
    for name,t in [('query',expected['query_start']),('last_map_ACK',acks[obj-1]['clock']),
                   ('OBJ_push',heads[obj][2]-expected['shift']),('OBJ_load',loads[obj]['clock']),
                   ('OBJ_ACK',acks[obj]['clock']),('OAM_load',loads[oam]['clock']),('OAM_proven',proven),
                   ('OAM_ACK',acks[oam]['clock']),('SEAL_load',final(957,'load')['clock'])]:
        times[name]=t
    assert times['last_map_ACK']==reference['ticks']['last_map_ACK']
    prefix={}
    for g in (952,956,957):
        prefix[g]=[]
        for i,r in enumerate(rows[g]):
            if r['event']=='idle524' and r['value']>=65536:
                dma=next(s for s in rows[g][i+1:] if s['event']=='ppu_dma')
                done=next(s for s in rows[g][i+1:] if s['clock']>dma['clock'] and s['event']=='ppu_last')
                assert done['clock']<final(g,'load')['clock']
                prefix[g].append(dict(offset=r['value']-65536,size=dma['value'],start=dma['clock'],end=done['clock']))
    long={g:any(d['size']==1536 and d['offset']==2048 for d in prefix[g]) for g in (952,957)}
    dma_summary={}
    for tag,path in [('base',base),('candidate',folder)]:
        with (path/'seal528.csv').open() as f:
            dma_summary[tag]=[(int(r['src']),int(r['port']),int(r['bytes']),int(r['clock']))
                              for r in csv.DictReader(f) if r['g']=='957' and r['event']=='dma']
    if 'pulse' in expected:
        with (folder/'progress740.csv').open() as f:
            pulse_writes=[int(r['clock']) for r in csv.DictReader(f)]
        assert expected['pulse']==pulse_writes[0 if expected['policy']=='first' else 1]
    ack=final(957,'ack')['clock']
    dense=ms(final(957,'reveal')['clock']-final(951,'reveal')['clock'])/6
    waits=sum(r['op']==3 and r['event']=='wait169' and r['clock']>=final(957,'final212')['clock'] for r in actions)
    assert sha(folder/'frame-957.rgb')==sha(base/'frame-957.rgb') and read(folder/'result.json')['commits']==53
    margins={k:ms(cutoff-times[k]) for k in ('OBJ_load','OBJ_ACK','OAM_proven','OAM_ACK')}
    return dict(ticks=times,after_956_ms={k:ms(t-origin) for k,t in times.items()},phase=expected['phase'],
                policy=expected['policy'],seal_DMA=dma_summary,display_VBlanks=final(957,'reveal')['frame']-final(956,'reveal')['frame'],shift_ms=ms(expected['shift']),prefix_DMA=prefix,long_prefix=long,
                line246_margin_ms=margins,final_wait=waits,dense_ms=dense,final_ACK=ack,
                dense_delta_ms=dense-reference['dense_ms'],ACK_delta_ms=ms(ack-reference['last_ACK_clock']),
                tail_shift_ms=ms(expected.get('tail_shift',0)),pulse_clock=expected.get('pulse'),
                gate=all(long.values()) and waits==0 and min(margins.values())>=0 and dense<reference['dense_ms']
                     and ack<reference['last_ACK_clock'],pins={k:sha(folder/k) for k in ('arrivals.tsv','window.csv','owner.csv','schedule.json','result.json')})


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--temp',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--probe',type=Path,required=True)
    a=parser.parse_args()
    result={'stage':740,'basis':727,'scope':'fixed map offers, retimed measured SPI group, executed 65816','phases':{}}
    references=read(Path(__file__).resolve().parents[1]/'analysis/owner739-verification.json')['phases']
    for phase in (1,2):
        base=a.temp/f'nes-pair727-a{phase}'
        result['phases'][phase]={k:measure(base,a.temp/f'nes-gap740-{k}{phase}-trace',references[str(phase)]['ref'])
                                 for k in ('obj','pair','issued','checked','first','both')}
    for policy,mode,code in [(k,m,c) for k in ('issued','first') for m,c in [('stop',0),('stale',224)]]:
        f=a.temp/f'nes-gap740-{policy}1-{mode}'
        j=read(f/'result.json')
        assert j['passed'] and j['commits']==52 and j['last_status'] in ((code,228) if mode=='stop' else (code,))
        assert sha(f/'retained.rgb')==sha(a.temp/'nes-pair727-a1/frame-956.rgb')
        assert not (f/'map-error.txt').exists() and not (f/'callback-error.txt').exists()
        result[f'{policy}_{mode}']=dict(status=j['last_status'],commits=j['commits'],retained_RGB=sha(f/'retained.rgb'))
    for trial in ('690','704'):
        menu=read(a.probe/f'menu-{trial}.json')
        assert menu['marker_cases']==4 and menu['rows']['normal']['released']==1 and len(menu['rows'])==5
        assert all(not v['released'] for k,v in menu['rows'].items() if k!='normal')
        result[f'menu_{trial}']=dict(firmware=menu['firmware'],modes=list(menu['rows']),marker_cases=4)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
