"""Compare actual early-BG ARM/65816 schedules and account for late954 preparation."""
import argparse
import hashlib
import json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one,packets
from analyze_nes_frontier536 import contents
from analyze_nes_ready673 import union_length


def tile_image(folder):
    result={}
    for g,rows in packets(folder).items():
        image={}
        for h,b,_ in rows:
            if h[0]!=7:continue
            at=int.from_bytes(h[10:12],'little')
            for i,value in enumerate(b):
                key=(h[1],at+i)
                assert key not in image,(g,key)
                image[key]=value
        result[g]=dict(bytes=len(image),OBJ_B=sum(k[0]==1 for k in image),
            SHA256=hashlib.sha256(json.dumps(sorted(image.items())).encode()).hexdigest())
    return result


def preparation(folder,g):
    ev=[e for e in read(folder/'events.json') if e['generation']==g]
    calls={e['call']:e for e in ev if e['event']=='call673'}
    returns={e['call']:e for e in ev if e['event']=='return673'}
    begin=next(e['clock'] for e in ev if e['event']=='planner_enter')
    plans=[e for e in calls.values() if e['name']=='nes_plan200_emit']
    bg=[e for e in plans if bytes.fromhex(e['plan'])[6]==0]
    last=bg[-1]['clock']
    spans=[(max(begin,e['clock']),min(last,returns[k]['clock'])) for k,e in calls.items()
           if e['name']=='nes_plan200_emit' and begin<=e['clock']<last]
    maps=[(max(begin,e['clock']),min(last,returns[k]['clock'])) for k,e in calls.items()
          if e['name']=='packet_wire' and e['section']==2 and begin<=e['clock']<last]
    spi=[(max(begin,e['start']),min(last,e['clock'])) for e in ev if e['event']=='SPI' and e['start']<last and e['clock']>begin]
    p=union_length(spans);pm=union_length(spans+maps);all_busy=union_length(spans+maps+spi)
    assert 0<=p<=pm<=all_busy<=last-begin
    terms=dict(plan_emit_calls=ms(p),map_packet_calls_outside_plan=ms(pm-p),
               other_SPI=ms(all_busy-pm),planner_other_callbacks_IRQ=ms(last-begin-all_busy))
    assert abs(sum(terms.values())-ms(last-begin))<1e-6
    obj=read(folder/'obj-phases.json')[str(g)]
    banks=[]
    for i,e in enumerate(plans):
        q=bytes.fromhex(e['plan'])
        if q[6]:continue
        bank=next(b for b in obj['banks557'] if b['first']<=i<b['first']+b['count'])
        accesses=[a for a in obj['cache611'] if a[5]=='ROM' and a[1]//16==int.from_bytes(q[4:6],'little')]
        assert len(accesses)==8
        banks.append(dict(slot=int.from_bytes(q[2:4],'little'),tag=int.from_bytes(q[4:6],'little'),
            call=e['clock'],returned=returns[e['call']]['clock'],E9_accept=bank['seal'],
            first_ROM_request=accesses[0][2],last_ROM_response=accesses[-1][4]))
    e8=[]
    final=banks[-1]
    for e in ev:
        if e.get('opcode')!='0xe8' or not final['call']<=e['start']<final['returned']:continue
        reply=bytes.fromhex(e['reply'])
        e8.append(dict(start=e['start'],complete=e['clock'],flags=reply[3],has_tile=reply[6],
            kind=reply[7],bytes=int.from_bytes(reply[8:10],'little'),offset=int.from_bytes(reply[10:12],'little'),
            token=int.from_bytes(reply[14:18],'little')))
    return dict(planner_start=begin,last_BG_call=last,interval_ms=ms(last-begin),nonoverlapping_terms_ms=terms,
                BG=banks,last_BG_emit_ms=ms(final['returned']-final['call']),last_BG_E8=e8,
                immutable=next(e['clock'] for e in ev if e['event']=='immutable673'),
                E9=[e for e in ev if e.get('opcode')=='0xe9'],
                limitation='Residual includes planner/residency/other callback/IRQ work. Not pure arithmetic; SPI driver averages and CPI2 retain their model limits.')


def run(a):
    phases={}
    firmware=sha(a.arm/'obj-nes-100/firmware.stm')
    for n in a.phases:
        base=a.traces/f'nes-ready673-b{n}';new=a.traces/f'nes-bg674-{a.tag}{n}'
        reference=a.traces/f'nes-front638-both{n}h'
        b=trace(base,reference);c=trace(new,reference)
        bj,j=read(base/'joint.json'),read(new/'joint.json')
        assert bj['parameters']==j['parameters'] and bj['client_SHA256']==j['client_SHA256']
        assert j['firmware_SHA256']==firmware
        assert contents(base)[1]==contents(new)[1] and tile_image(base)==tile_image(new)
        assert {g:r['work'] for g,r in b['frames'].items()}=={g:r['work'] for g,r in c['frames'].items()}
        cpu=csv_groups(new/'window.csv');s911=[r for r in cpu[911] if r['op']==3]
        protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
                       reveal951=c['details'][951]['marks']['reveal']['line']<=246,
                       interval952=c['intervals'][952]['VBlank']==3,
                       final_wait957=c['intervals'][957]['final_waits']==0)
        dense=c['checked']['dense_mean_ms']-b['checked']['dense_mean_ms']
        ack=ms(c['checked']['last_ACK']-b['checked']['last_ACK'])
        regressions=[g for g in b['intervals'] if c['intervals'][g]['VBlank']>b['intervals'][g]['VBlank']]
        extra_waits=[g for g in b['intervals'] if c['intervals'][g]['final_waits']>b['intervals'][g]['final_waits']]
        details={}
        for g in (954,957):
            details[g]={}
            for label,folder,tr in (('base',base,b),('candidate',new,c)):
                d=tr['details'][g]
                details[g][label]=dict(preparation=preparation(folder,g),previous_reveal=d['previous_reveal'],
                    marks=d['marks'],packets=d['packets'],interval=tr['intervals'][g],early_DMA_B=tr['early_DMA_B'][g])
        phases[n]=dict(dense_delta_ms=dense,last_ACK_delta_ms=ack,
            dense={key:{'VBlank':t['checked']['dense_VB'],'mean_ms':t['checked']['dense_mean_ms'],'last_ACK':t['checked']['last_ACK']}
                   for key,t in (('base',b),('candidate',c))},
            protected=protected,deadline911={key:one(s911,key) for key in ('load','upload165_entry')},
            interval_regressions=regressions,new_final_waits=extra_waits,
            intervals={key:t['intervals'] for key,t in (('base',b),('candidate',c))},
            wire_B={key:r['wire_B'] for key,r in (('base',bj),('candidate',j))},
            details=details,same_map_OBJ_and_pixels=True,
            numerical_both_faster=dense<0 and ack<0,
            selected_gate=all(protected.values()) and dense<0 and ack<0 and not extra_waits and not regressions,
            pins={key:sha(new/key) for key in ('joint.json','events.json','window.csv','seal528.csv','obj-phases.json','packets.jsonl')})
        # Preserve the complete failing pipeline result instead of selecting
        # a locally shorter957 interval or pretending bank credit frees bulk.
        if a.tag=='pair':
            ready=details[957]['candidate']['preparation']['last_BG_E8']
            assert len(ready)>=2 and ready[0]['flags']==1 and ready[0]['has_tile']==1
            assert ready[0]['bytes']==16 and ready[0]['offset']==0
            assert ready[-1]['flags']==1 and ready[-1]['has_tile']==0
    flash=(a.arm/'obj-nes-100/firmware.stm').stat().st_size
    changed={f.name:sha(f) for f in a.arm.glob('nes_*.[ch]') if sha(f)!=sha(a.base_arm/f.name)}
    assert set(changed)=={'nes_plan_service200.c'}
    result=dict(baseline='MMC666',candidate=a.tag,phases=phases,firmware=firmware,
        Flash_B=flash,Flash_free_B=212992-flash,changed_ARM_sources=changed,
        ARM_data_B=10040,ARM_BSS_B=19544,extra_static_RAM_B=0,
        guards={f.name:dict(SHA256=sha(f),result=read(f)) for f in a.guards},
        selected='bg674' if len(phases)==2 and all(p['selected_gate'] for p in phases.values()) else 'MMC666',
        board_and_65816_unchanged=True,new_FIT_STA=False,new_delivery=False,
        board_reference='analysis/entry665-verification.json',
        prior_673_budget='analysis/ready673-budget.json',
        interpretation='Prepared BG is not send permission or bulk capacity. First checked E8 already exposes writable bank plus pending zero tile; poll retains bit1 only for END-only, so pair flush waits for zero tile removal. Repeated pairs also consume two plan banks and stall954. Do not extend the grant to BG without checking actual two-slot ownership and STOP.',
        scope='Actual linked M4 and65816; modeled CPI2/shared SPI/IRQ and measured periodic ROM calendar. Equal map/OBJ/ordinary/output pixels. Not physical FPS or closed-loop live PSRAM RTL.',
        sources={p.name:sha(p) for p in Path('tools').glob('*674.py')})
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({n:{k:p[k] for k in ('dense_delta_ms','last_ACK_delta_ms','protected','interval_regressions','new_final_waits','selected_gate')} for n,p in phases.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('traces','arm','base-arm','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--tag',default='pair');p.add_argument('--phases',type=int,nargs='+',default=[1,2])
    p.add_argument('--guards',type=Path,nargs='*',default=[])
    run(p.parse_args())
