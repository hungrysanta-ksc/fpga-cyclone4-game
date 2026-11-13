# SPDX-License-Identifier: MIT
"""Compare the producer, SPI, receiver and display clocks on one reset-booted ROM."""
import argparse
import json
from functools import lru_cache
from pathlib import Path

from analyze_nes_owner739 import csv_groups, packets, read, sha
from analyze_nes_static751 import phase

POLICIES=('priority','receipt','seal','combined','look','lookbg','bgcrc','repay','credit','mapobj')


@lru_cache(maxsize=None)
def edge(folder):
    events=read(folder/'events.json')
    windows=csv_groups(folder/'window.csv')
    heads=packets(folder)[957]
    bg,=[i for i,(h,b,_) in enumerate(heads) if h[:2]==bytes((7,0)) and len(b)==48]
    rows=windows[957]
    def points(g,kind):
        return [e for e in events if e['generation']==g and e['event']==kind]
    def seal(g,kind):
        return next(e['clock'] for e in windows[g] if e['op']==3 and e['event']==kind)
    spi=lambda g:[e for e in points(g,'SPI')]
    bg_wire=next(e for e in spi(957) if e['opcode']=='0xe1' and abs(e['clock']-heads[bg][2])<1)
    descriptor=bytes((1,0,48,0))+heads[bg][0][10:12]+heads[bg][0][8:10]+heads[bg][0][16:20]
    bg_query=next(e for e in reversed(spi(957)) if e['opcode']=='0xe8' and
                  e['clock']<=bg_wire['start'] and bytes.fromhex(e['reply'])[6:18]==descriptor)
    expected=bytes.fromhex(read(Path('analysis/obj749-verification.json'))['phases']['2']['page']['E8_reply'])
    obj_query=next(e for e in spi(957) if e['opcode']=='0xe8' and bytes.fromhex(e['reply'])[6:18]==expected[6:18])
    preceding,before=points(955,'credit673')[-2:]
    last956=points(956,'wire664')[-1]['clock']
    ack956=seal(956,'ack')
    samples=[e for e in spi(955) if e['opcode']=='0xe0' and e['clock']<=before['clock']]
    assert int.from_bytes(bytes.fromhex(samples[-1]['reply'])[5:7],'big')==before['after']
    assert int.from_bytes(bytes.fromhex(samples[-2]['reply'])[5:7],'big')!=before['after']
    bg_job=next(e for e in points(957,'wire664') if e['op']==7 and e['section']==0 and e['offset']==int.from_bytes(descriptor[4:6],'little'))
    tail=points(955,'wire664')
    return dict(
        output955=tail[0]['clock'],
        BG1968_wire955=next(e['clock'] for e in tail if (e['op'],e['section'],e['offset'])==(7,0,1968)),
        padding21_wire955=next(e['clock'] for e in tail if (e['op'],e['section'],e['offset'])==(5,5,21)),
        prior_credit955=preceding['clock'],E0_polls_until955_ACK=sum(e['start']>preceding['clock'] for e in samples),
        seal955=next(e['clock'] for e in points(955,'wire664') if e['op']==3),
        prefetch956=next(e['start'] for e in spi(955) if e['opcode']=='0xd1' and e['start']>points(955,'wire664')[-1]['clock']),
        seal955_ACK=seal(955,'ack'),E0_before955_ACK_snapshot=samples[-2]['start'],
        E0_credit955_start=samples[-1]['start'],credit955=before['clock'],
        blocks_before_ACK956=sum(e['opcode']=='0xd1' and last956<e['start'] and e['clock']<=ack956 for e in spi(956)),
        planner956=points(956,'planner_enter')[0]['clock'],source957=points(957,'source_begin')[0]['clock'],
        public956=seal(956,'reveal'),ACK956=seal(956,'ack'),
        first_after956=next(e['clock'] for e in events if e.get('clock',0)>=seal(956,'reveal') and e['event']=='input682_return'),
        planner957=points(957,'planner_enter')[0]['clock'],
        BG_verified_E8_response=bg_query['clock'],BG_wire_ready=bg_job['clock'],
        BG_E1=bg_wire['start'],BG_E1_end=bg_wire['clock'],
        BG_load=[r for r in rows if r['event']=='load'][bg]['clock'],BG_receipt=[r for r in rows if r['event']=='ack'][bg]['clock'],
        OBJ_E8=obj_query['start'],OBJ_E8_end=obj_query['clock'],OBJ_E8_reply=obj_query['reply'],
        BG_before_E1_SPI=[e['opcode'] for e in spi(957) if bg_query['clock']<e['clock']<=bg_wire['start']],
        BG_to_OBJ_SPI=[e['opcode'] for e in spi(957) if bg_wire['clock']<e['clock']<=obj_query['start']])


def measure(temp,probe,k,n):
    folder=temp/f'nes-credit752-{k}{n}'
    client=probe.parent/'nes-static751/sharedfast'
    fw=probe/f'arm-{k}/src/obj-nes-100/firmware.stm'
    timing=phase(temp,'sharedfast',n,folder=folder,client=client,firmware=sha(fw))
    marks=edge(folder)
    baseline=edge(temp/f'nes-static751-sharedfast{n}')
    ref=edge(temp/f'nes-obj749-page{n}')
    assert abs(marks['OBJ_E8']-timing['E8_start'])<1
    map957=next((r for r in timing['map_ranges'][957] if r['bytes']==1536 and r['preseal']),None)
    after_map=None
    if map957:
        rows=csv_groups(folder/'window.csv')[957]
        oam,=[offer for h,b,offer in packets(folder)[957] if h[0]==9]
        first=next(x for x in rows if x['clock']>map957['last'] and x['event'] in ('load','ppu_dma'))
        after_map=dict(OAM_offer_minus_map_last=oam-map957['last'],first=first)
    same_deadlines=(timing['margin_to_258'] is not None and timing['margin_to_258']>0 and
                    (n==2 or timing['margin_to_258']>=12) and timing['E8_end']<=timing['E8_749_end'] and
                    timing['E8_delta_clocks']<=0 and timing['order'] and all(timing['long_map'].values()) and
                    all(x<=248 for x in timing['map_latch_lines'].values()))
    bg_improved=n==1 or marks['BG_E1']<baseline['BG_E1']
    whole_gain=timing['ACK_delta']<0 and timing['dense_delta_us']<0
    return dict(firmware=sha(fw),flash=fw.stat().st_size,clocks=marks,after_map=after_map,
                deadlines=same_deadlines,whole_gain=whole_gain,BG_improved=bg_improved,
                delta_749={s:marks[s]-v for s,v in ref.items() if isinstance(v,(int,float))},
                delta_751={s:marks[s]-v for s,v in baseline.items() if isinstance(v,(int,float))},
                timing=timing,passed=bg_improved and same_deadlines and whole_gain and timing['guarded_schedule'])


def analyze(a):
    variants={k:{n:measure(a.temp,a.probe,k,n) for n in (1,2)} for k in a.policies}
    provenance={}
    for n in (1,2):
        old=edge(a.temp/f'nes-obj749-page{n}')
        new=edge(a.temp/f'nes-static751-sharedfast{n}')
        provenance[n]=dict(reference749=old,reference751=new,delta={k:new[k]-v for k,v in old.items() if isinstance(v,(int,float))})
    result=dict(stage=752,client='751 sharedfast',board='707D',reference=727,deadlines=749,
                origin=provenance,variants=variants,passed_both=[k for k,p in variants.items() if all(x['passed'] for x in p.values())])
    result['scope']='Reset boot, 53 real 65816 displays per start and linked ARM; modeled SPI/IRQ/ROM calendar.'
    result['guards']={}
    result['DMA_faults']={}
    for k in variants:
        g=read(a.probe/f'guards752-{k}.json')
        assert g['firmware']==variants[k][1]['firmware']==variants[k][2]['firmware']==g['menu']['firmware']
        assert len(g['deadline'])==17 and len(g['receipt'])==9 and len(g['menu']['rows'])==5
        assert len(g['handoff'])==(11 if k.startswith('look') else 8) and g['menu']['marker_cases']==4
        assert g['seal_receipts']['corrupt_bits']==152
        result['guards'][k]=g
        for n in (1,2):
            for fault in ('before','during','head','stale'):
                d=a.temp/f'nes-credit752-guard-{k}{n}-{fault}'
                if (d/'verified751.json').exists():
                    record=read(d/'verified751.json')
                    assert record['fault']==fault and record['client']==sha(a.probe.parent/'nes-static751/sharedfast/sink165.sfc')
                    result['DMA_faults'][f'{k}{n}-{fault}']=record
    result['rejected_overlap']={}
    for n in (1,2):
        log=a.temp/f'nes-credit752-overlap{n}.log'
        detail=log.read_text(encoding='utf8',errors='replace').splitlines()
        assert detail[-1]=='AssertionError: not an empty output queue'
        result['rejected_overlap'][n]=dict(reason=detail[-1],log=sha(log))
    base=read(a.probe.parent/'nes-static751/sharedfast/build.json')
    result['physical_ROM_B']=base['physical_ROM_B']
    result['physical_ROM_free_B']=base['physical_free_B']
    result['ROM_SHA256']=sha(a.probe.parent/'nes-static751/sharedfast/sink165.sfc')
    assert result['ROM_SHA256']==read(Path('analysis/static751-verification.json'))['variants']['sharedfast']['ROM']
    assert all(v[n]['flash']<=212992 for v in variants.values() for n in (1,2))
    if 'bgcrc' in variants:assert len(result['guards']['bgcrc']['BG_descriptor'])==7
    for policy in ('repay','mapobj'):
        if policy in variants:
            assert len(result['guards'][policy]['map_input'])==6
    for policy in result['passed_both']:
        for n in (1,2):
            for fault in ('before','during','head','stale'):
                assert f'{policy}{n}-{fault}' in result['DMA_faults'], (policy,n,fault)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','probe','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--policies',nargs='+',default=POLICIES,choices=POLICIES)
    analyze(p.parse_args())
