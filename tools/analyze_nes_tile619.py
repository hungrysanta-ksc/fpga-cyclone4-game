# SPDX-License-Identifier: MIT
"""Match 618 and the tile/coverage factorial on both coupled CPU start phases."""
import argparse
import json
from pathlib import Path

from analyze_nes_map617 import csv_groups, ms, one, read, sha, timing
from analyze_nes_oam618 import work
from analyze_nes_output531 import prior_blank_windows
from test_nes_service509_schedule import Calendar


def summarize(folder, calendar):
    r=timing(folder)
    watched=r['watched']
    all_rows=csv_groups(folder/'window.csv')
    rows=all_rows[954]
    seal=[x for x in rows if x['op']==3]
    beam=csv_groups(folder/'seal528.csv')[954]
    dma=next(x for x in beam if x['event']=='dma')
    match,=[x for x in rows if x['event']=='ppu_dma' and x['clock']==dma['clock']]
    windows=sorted(prior_blank_windows(dma,match['frame'],one([x for x in rows if x['op']==1],'ack')['clock'],
                                        one(seal,'load')['clock'],252))
    cutoff=windows[-1][1]
    packets=[json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    bulk=[]
    for x in rows:
        if x['event']!='ack' or x['op']!=7:continue
        _,push,hex_header,payload=packets[x['index']-1]
        header=bytes.fromhex(hex_header);n=int.from_bytes(header[14:16],'little')
        assert len(bytes.fromhex(payload))==n
        bulk.append(dict(kind='OBJ' if header[1] else 'BG',B=n,offset=int.from_bytes(header[10:12],'little'),
                         push=push,accepted=x['clock'],line=x['line'],frame=x['frame'],
                         accepted_after_cutoff_ms=ms(x['clock']-cutoff)))
    obj=read(folder/'obj-phases.json')['954']
    boundary=next(b for b in obj['boundaries561'] if b['prior_B']==144)
    batch=obj['banks557'][1]
    word_reads=[r for r in obj['cache611'] if batch['first_check']<=r[2]<boundary['close'] and r[5]=='ROM']
    kind,address,requested,grant,response,_=word_reads[0]
    assert kind==0
    rom_reads=len(word_reads)
    j=read(folder/'joint.json')
    assert j['parameters']['ROM_phase']==0 and j['parameters']['ROM_calendar']==calendar.summary
    assert calendar.select(requested+1)==(grant,response)
    period=requested//calendar.period
    earlier=[cycle*calendar.period+tick for cycle in (period-1,period) for tick in calendar.starts
             if cycle*calendar.period+tick<requested]
    cov=one(seal,'coverage212');upload=one(seal,'upload165_entry')
    first_wait=next(x for x in seal if x['event'] in ('wait169','final212'))
    before=[x['value'] for x in seal if x['event']=='ppu_dma' and x['clock']<first_wait['clock']]
    normal_late=[x['bytes'] for x in beam if x['event']=='dma' and x['port']==24 and
                 x['clock']>first_wait['clock'] and x['dst'] in (0xc7b0,0xc7a0,0x8760)]
    g=watched[955]
    early={k for x in g['early'] for k in range(x['offset'],x['offset']+x['B'],64)}
    return dict(dense_VB=r['dense_VB'],dense_mean_ms=r['dense_ms'],last_ACK=r['last_ACK'],
                display_VB={k:v['display_VB'] for k,v in watched.items()},all_intervals=r['all_display_VB'],
                final_wait_957=watched[957]['final_waits'],
                first_map_955_B=g['first_window_DMA_B'],last_map_955_B=64*len(early.intersection(range(3200,3584,64))),
                coverage_to_upload_954_ms=ms(upload['clock']-cov['clock']),coverage_line=cov['line'],upload_line=upload['line'],
                pre_wait_954_B=before,late_tile_954_B=normal_late,SEAL_954=one(seal,'load')['clock'],
                upload_wait_954_ms=watched[954]['upload_wait_ms'],final_entry_line=one(seal,'final212')['line'],
                wait_954_lines=watched[954]['wait_lines'],cutoff_954=cutoff,bulk_954=bulk,
                BG_stall=dict(address=address,request=requested,grant=grant,ms=ms(grant-requested),
                              grant_vs_cutoff_ms=ms(grant-cutoff),BG_144_ready=boundary['ready'],
                              E9_end=batch['seal'],ROM_reads_to_144=rom_reads,
                              prior_window_last=earlier[-1],latest_first_grant=earlier[-rom_reads],
                              minimum_advance_ms=ms(requested-earlier[-rom_reads]),
                              eligible_grants_after_first_release=sum(t>=obj['banks557'][0]['release'] for t in earlier)),
                warm_DMA_checked=r['warm_DMA_checked'],
                client=j['client_SHA256'],firmware=j['firmware_SHA256'],
                pins={n:sha(folder/n) for n in ('joint.json','events.json','obj-phases.json','window.csv','seal528.csv','packets.jsonl')})


def run(a):
    base_results=read(a.reference)['phases']
    calendar=Calendar(a.calendar)
    result=[]
    modes=('tile','coverage','both')
    for phase in (1,2):
        base=a.traces/f'nes-oam618-paced{phase}'
        case_work=work(base)
        baseline=read(base/'joint.json')
        control=summarize(base,calendar)
        assert control['pins']==base_results[phase-1]['paced']['pins']
        selector=a.traces/f'nes-tile619-selector{phase}'
        audit=read(selector/'audit.json')
        assert audit['trace']==sha(selector/'window.csv')==sha(base/'window.csv')
        data=dict(control=control,selector=dict(**audit,selector=sha(selector/'selector536.csv')))
        for mode in modes:
            d=a.traces/f'nes-tile619-{mode}{phase}'
            candidate=read(d/'joint.json')
            assert all(candidate[k]==baseline[k] for k in ('firmware_SHA256','parameters','ROM_read_allocations','vram_DMA_B'))
            assert work(d)==case_work and all(sha(base/n)==sha(d/n) for g in range(905,958)
                                              for n in (f'frame-{g}.rgb',f'map-{g}.bin'))
            assert not any((d/n).exists() for n in ('fault.json','callback-error.txt','map-error.txt'))
            c=summarize(d,calendar)
            assert c['client']==sha(a.clients/mode/'sink165.sfc')
            c.update(last_ACK_delta_ms=ms(c['last_ACK']-control['last_ACK']),
                     dense_delta_ms=c['dense_mean_ms']-control['dense_mean_ms'])
            c['changed_VB']={g:n-control['all_intervals'][g] for g,n in c.pop('all_intervals').items()
                             if n!=control['all_intervals'][g]}
            c['passes']=bool(c['display_VB'][954]<control['display_VB'][954] and c['dense_VB']<control['dense_VB']
                             and c['dense_delta_ms']<0 and c['last_ACK_delta_ms']<0 and c['display_VB'][952]==4
                             and c['final_wait_957']==0 and c['last_map_955_B']==384 and c['first_map_955_B']>=192)
            data[mode]=c
        del control['all_intervals']
        result.append(data)
    edges=read(a.edges/'edges.json');priority=read(a.priority/'edges.json');stops=read(a.stops/'result.json')
    assert len(edges)==12 and len(priority)==9 and all(x['status']==0xe4 for x in stops) and len(stops)==4
    coverage_tests={tool:read(a.traces/f'nes-tile619-cov-{tool}'/filename) for tool,filename in
                    [('test_nes_tile619_edges','edges.json'),('test_nes_map616_edges','edges.json'),('test_nes_seal538_stop','result.json')]}
    assert [len(rows) for rows in coverage_tests.values()]==[8,9,4]
    out=dict(phases=result,body_B={k:read(a.clients/k/'build.json')['body_bytes'] for k in modes},
             passes={k:all(p[k]['passes'] for p in result) for k in modes},edges=edges,priority=priority,stops=stops,
             coverage_tests=coverage_tests)
    a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','calendar','reference','clients','edges','priority','stops','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
