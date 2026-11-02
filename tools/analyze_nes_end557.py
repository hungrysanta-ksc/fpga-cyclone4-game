# SPDX-License-Identifier: MIT
"""Separate admission to writable host RAM from ordered execution of the final OBJ records."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path

from analyze_nes_admit556 import obj_deadline
from analyze_nes_grant555 import map_admission
from analyze_nes_map553 import map_times
from analyze_nes_phase537 import Calendar,csv_groups,ms,one,read,sha
from analyze_nes_seal538 import inspect_run
from analyze_nes_supply549 import compare
from test_nes_banks557 import handoff,host_after


def sample(start):
    return host_after(start+7.5*21_477_272/2_625_000,3)


def schedule(folder,banked,cal):
    p=read(folder/'obj-phases.json')['954']
    ev=[r for r in read(folder/'events.json') if r['generation']==954]
    spi=[r for r in ev if r['event']=='SPI']
    batches=[r for r in spi if r['opcode']=='0xe9']
    assert [r['bytes'] for r in batches]==[32,121,43]
    start=batches[-1]['start'];end=batches[-1]['clock'];assert p['end_accepted']==end
    probes=[r for r in spi if r['opcode']=='0xe8' and batches[-2]['clock']<r['start']<start]
    polls=[dict(sample=sample(r['start']) if banked else r['start'],end=r['clock'],ready=bytes.fromhex(r['reply'])[3],
                chunk=bytes.fromhex(r['reply'])[6]) for r in probes]
    assert polls[-1]['ready']==1 and polls[-1]['chunk']==0
    if banked:
        banks=p['banks557'];assert [r['count'] for r in banks]==[4,15,5]
        ready=handoff(banks,1)
        assert all(x['ready']==int(x['sample']>=ready) for x in polls)
        assert banks[-1]['sample']==sample(start)
    else:
        edge,=[r for r in p['credit_edges557'] if r['accepted']==2 and r['next_plan']==19 and r['cause']=='tile_complete']
        ready=edge['clock']
    cpu=csv_groups(folder/'window.csv')
    previous=one([r for r in cpu[953] if r['op']==3],'reveal')
    seal=[r for r in cpu[954] if r['op']==3]
    tail=obj_deadline(folder,cal,queued=banked)
    # The final E9 has 4 OBJ records plus END. Only their 18 reads belong
    # to it, even when earlier records are still running at E9 seal.
    orig=read(folder/'joint.json')
    return dict(eligibility=ready,END_call=one(ev,'end_enter')['clock'],polls=polls,last_E8=polls[-1],E9=batches[-1],
                eligible_to_deciding_sample_ms=ms(polls[-1]['sample']-ready),
                sample_to_seal_ms=ms(end-polls[-1]['sample']),seal_to_OBJ_request_ms=ms(tail['request']-end),
                OBJ_request_ms=ms(tail['request']-previous['clock']),last_OBJ_response_ms=ms(p['last_obj_rom_response']-previous['clock']),
                before_SEAL=one(seal,'load')['frame']-previous['frame'],display_VB=one(seal,'reveal')['frame']-previous['frame'],
                before_957_tile_ACK=sum(x['push_minus_last_tile_ACK_ms']<0 for x in map_times(folder)['maps']),
                wait957=sum(x['event']=='wait169' and x['clock']>=one([r for r in cpu[957] if r['op']==3],'final212')['clock']
                            for x in cpu[957] if x['op']==3),map=map_admission(folder),OBJ=tail,
                E8_total=sum(r.get('opcode')=='0xe8' for r in read(folder/'events.json')),
                spi_bytes=orig['wire_B'])


def analyze(a):
    old=read(a.previous);cal=Calendar(a.traces/'nes-service509-rom03')
    plans=read(a.plans/'frame954/plans.json')
    assert len(plans)==23 and all(bytes.fromhex(h)[6]==1 for _,h in plans[-4:])
    assert sum(bytes.fromhex(h)[7].bit_count()*2 for _,h in plans[-4:])==18
    phases=[]
    for i in (1,2):
        variants={}
        base=a.traces/f'nes-admit556-combined{i}'
        for m in ('base','probe','banks-base','banks-probe','banks-551'):
            f=a.traces/f'nes-end557-{m}{i}'; audit=a.traces/f'nes-end557-replay-{m}{i}'
            arm=a.arm if m.endswith('probe') else a.old_arm
            banked=m.startswith('banks-')
            client=a.client
            if m=='banks-551':
                arm=a.physical_arm
                client=a.physical_client
            first=None
            if banked:
                # Fill transfer 64 clocks and 11 handoff clocks, followed by
                # 14 READ/CAPTURE clocks, CHECK and READY for the 7B BG record.
                first={int(g):p['banks557'][0]['first_check']+92 for g,p in read(f/'obj-phases.json').items()}
            cost=inspect_run(f,a.plans,cal,base,sha(arm/'obj-nes-100/firmware.stm'),sha(client/'sink165.sfc'),
                             first_bg_limit=3,first_bg_requests=first)
            replay=read(audit/'audit.json');assert replay['frames']==53 and replay['trace']==cost['pins']['window.csv']
            with (audit/'bitmaps556.csv').open() as inp:spans=list(csv.DictReader(inp))
            assert len(spans)==old['phases'][i-1]['combined']['bitmap_spans'] and len({(r['bank'],r['section']) for r in spans})==6
            s=schedule(f,banked,cal)
            variants[m]=dict(cost=cost,schedule=s,replay=replay)
            if m=='base':
                assert all(cost['pins'][k]==old['phases'][i-1]['combined']['cost']['pins'][k] for k in ('events.json','packets.jsonl','window.csv','seal528.csv'))
            if m.endswith('probe'):
                ref=variants[m.replace('probe','base')]['cost']
                d=cost['dense_frames']
                later=[g for g,row in cost['BG'].items() if row['relative_window']>ref['BG'][g]['relative_window']]
                delta=compare(cost,ref)
                variants[m].update(delta=delta,later_BG=later,gate=(s['display_VB']<=5 and s['before_SEAL']<=4
                    and s['before_957_tile_ACK']>=2 and not s['wait957'] and not any(cost['waits'].values())
                    and d[953]['before_head']+d[953]['after_head']<=5 and not later and
                    delta['last_ACK_ms']<0 and delta['dense_ms']<0 and cost['dense_VB']<=27))
        candidate=variants['banks-base']
        reference=variants['banks-551']['cost']
        delta=compare(candidate['cost'],reference)
        candidate['vs_MMC551']=delta
        candidate['later_BG_vs_MMC551']=[g for g,b in candidate['cost']['BG'].items() if b['relative_window']>reference['BG'][g]['relative_window']]
        s=candidate['schedule'];d=candidate['cost']['dense_frames']
        candidate['trial_gate']=(s['display_VB']<=5 and s['before_SEAL']<=4 and s['before_957_tile_ACK']>=2
            and not s['wait957'] and not any(candidate['cost']['waits'].values()) and d[953]['before_head']+d[953]['after_head']<=5
            and not candidate['later_BG_vs_MMC551'] and all(v<0 for v in delta.values()))
        phases.append(variants)
    guards={k:read(a.checks/(k+'.json')) for k in ('credit','guards','menu','window','second')}
    fw=sha(a.arm/'obj-nes-100/firmware.stm')
    assert fw==guards['credit']['sha']==guards['guards']['sha']==guards['menu']['firmware']==guards['window']['firmware_SHA256']
    assert guards['second']['sha']==fw and len(guards['second']['rows'])==8
    return dict(phases=phases,guards=guards,directed_RTL=read(a.rtl/'result.json'),timed_RTL=read(a.timed/'result.json'),
                gate=all(ph['banks-probe']['gate'] for ph in phases),trial_gate=all(ph['banks-base']['trial_gate'] for ph in phases),
                board=old['board']['candidate'],client=sha(a.client/'sink165.sfc'),
                selected_ARM_SHA256=sha(a.old_arm/'obj-nes-100/firmware.stm'),
                scope='Actual board SPI/plan RAM/CDC tests; M4 CPI2 plus Mesen, two bank schedule with modeled tile work, shared SPI/IRQ and repeated boot ROM grants.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','previous','plans','arm','old-arm','client','physical-arm','physical-client','checks','rtl','timed','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',newline='\n')
