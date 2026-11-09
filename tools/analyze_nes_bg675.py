"""Compare one initial BG grant with MMC666, including the early zero receipt."""
import argparse
import json
from pathlib import Path
from analyze_nes_bg674 import tile_image,preparation
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_frontier536 import contents
from check_nes_fault641 import evidence
from test_nes_service509_schedule import Calendar


def detail(folder,tr,g):
    d=tr['details'][g];previous=d['previous_reveal']
    ev=[e for e in read(folder/'events.json') if e['generation']==g]
    prep=preparation(folder,g)
    return dict(previous_reveal=previous,preparation=prep,interval=tr['intervals'][g],
        zero=next(p for p in d['packets'] if p['op']==7 and p['section']==0 and p['offset']==0),
        E8=[dict(start=e['start'],complete=e['clock'],reply=e['reply']) for e in ev if e.get('opcode')=='0xe8'],
        early_DMA_B=tr['early_DMA_B'][g],marks=d['marks'],packets=d['packets'])


def stalls(folder,g):
    ev=[e for e in read(folder/'events.json') if e['generation']==g]
    returns={e['call']:e for e in ev if e['event']=='return673'}
    calls=[]
    for e in ev:
        if e['event']!='call673' or e['name']!='nes_plan200_emit':continue
        q=bytes.fromhex(e['plan']);end=returns[e['call']]['clock']
        calls.append(dict(kind=q[6],slot=int.from_bytes(q[2:4],'little'),tag=int.from_bytes(q[4:6],'little'),
            call=e['clock'],returned=end,duration_ms=ms(end-e['clock'])))
    return dict(calls=calls,batches=read(folder/'obj-phases.json')[str(g)]['banks557'])


def drain_tail(folder,tr,g):
    d=tr['details'][g];ev=[e for e in read(folder/'events.json') if e['generation']==g]
    calls={e['call']:e for e in ev if e['event']=='call673'}
    returns={e['call']:e for e in ev if e['event']=='return673'}
    lastmap=max(p['ack'] for p in d['packets'] if p['section']==2)
    ordinary=next(p for p in d['packets'] if p['section']>=3 and p['op']!=7)
    request=next(e['clock'] for e in calls.values() if e['name']=='packet_wire' and
                 e.get('section')==ordinary['section'] and e.get('offset')==ordinary['offset'])
    drained=max(returns[k]['clock'] for k,e in calls.items() if e['name']=='nes_window184_through' and lastmap<=returns[k]['clock']<=request)
    source=[e for e in ev if e.get('opcode') in ('0xd0','0xd1','0xd2') and drained<=e['start']<request]
    return dict(last_map_ACK=lastmap,drain_return=drained,first_ordinary_request=request,
        tail_ms=ms(request-drained),last_tile_ACK=d['last_tile_ACK'],
        all_tiles_done_before_drain=d['last_tile_ACK']<drained,
        source_SPI=[{k:e[k] for k in ('opcode','start','clock')} for e in source],
        interpretation='40 waits on displayed && obj_next>=16 are unchanged source. The callback count itself was not instrumented in full replay; linked guard test independently checks40/0 for16/15 threshold.')


def window_budget(folder,tr,g,calendar):
    prep=preparation(folder,g);last=prep['BG'][-1]['last_ROM_response']
    windows=[]
    for grant,response in calendar.pairs:
        if not windows or grant-windows[-1][-1][0]>10000:windows.append([])
        windows[-1].append((grant,response))
    repeat=int(last//calendar.period)
    nearby=[[(cycle*calendar.period+lo,cycle*calendar.period+hi) for lo,hi in w] for cycle in (repeat-1,repeat,repeat+1) for w in windows]
    current=next(w for w in nearby if w[0][0]<=last<=w[-1][1])
    prior=max((w for w in nearby if w[-1][1]<current[0][0]),key=lambda w:w[-1][1])
    return dict(previous_window_close=prior[-1][1],
        E9_late_ms=ms(prep['BG'][-1]['E9_accept']-prior[-1][1]),
        caller_late_ms=ms(prep['BG'][-1]['call']-prior[-1][1]))


def run(a):
    phases={};firmware=sha(a.arm/'obj-nes-100/firmware.stm')
    calendar=Calendar(a.traces/'nes-service509-rom03')
    rtl=read(a.traces/'nes-bg675-rtl01/result.json')
    pins=evidence('entry665-verification.json')['board_inputs']['inputs']
    assert all(pins[k]==v for k,v in rtl['source_SHA'].items())
    for n in a.phases:
        base=a.traces/f'nes-ready673-b{n}';new=a.traces/f'nes-bg675-grant{n}'
        ref=a.traces/f'nes-front638-both{n}h'
        b=trace(base,ref);c=trace(new,ref)
        bj,j=read(base/'joint.json'),read(new/'joint.json')
        assert bj['parameters']==j['parameters'] and bj['client_SHA256']==j['client_SHA256']
        assert j['firmware_SHA256']==firmware
        assert contents(base)[1]==contents(new)[1] and tile_image(base)==tile_image(new)
        assert {g:r['work'] for g,r in b['frames'].items()}=={g:r['work'] for g,r in c['frames'].items()}
        s911=[r for r in csv_groups(new/'window.csv')[911] if r['op']==3]
        protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
            reveal951=c['details'][951]['marks']['reveal']['line']<=246,
            interval952=c['intervals'][952]['VBlank']==3,final_wait957=c['intervals'][957]['final_waits']==0)
        dense=c['checked']['dense_mean_ms']-b['checked']['dense_mean_ms']
        ack=ms(c['checked']['last_ACK']-b['checked']['last_ACK'])
        regressions=[g for g in b['intervals'] if c['intervals'][g]['VBlank']>b['intervals'][g]['VBlank']]
        extra=[g for g in b['intervals'] if c['intervals'][g]['final_waits']>b['intervals'][g]['final_waits']]
        phases[n]=dict(dense_delta_ms=dense,last_ACK_delta_ms=ack,protected=protected,
            dense={k:{'VBlank':t['checked']['dense_VB'],'mean_ms':t['checked']['dense_mean_ms'],'last_ACK':t['checked']['last_ACK']}
                for k,t in (('base',b),('candidate',c))},
            deadline911={k:one(s911,k) for k in ('load','upload165_entry')},
            interval_regressions=regressions,new_final_waits=extra,
            intervals={k:t['intervals'] for k,t in (('base',b),('candidate',c))},
            wire_B={k:t['wire_B'] for k,t in (('base',bj),('candidate',j))},
            details={g:{k:detail(f,t,g) for k,f,t in (('base',base,b),('candidate',new,c))} for g in (954,957)},
            plan_calls={g:{k:stalls(f,g) for k,f in (('base',base),('candidate',new))} for g in (952,954,957)},
            frame952={k:t['details'][952] for k,t in (('base',b),('candidate',c))},
            drain952={k:drain_tail(f,t,952) for k,f,t in (('base',base,b),('candidate',new,c))},
            early_DMA952={k:t['early_DMA_B'][952] for k,t in (('base',b),('candidate',c))},
            ROM_windows={g:{k:window_budget(f,t,g,calendar) for k,f,t in (('base',base,b),('candidate',new,c))} for g in (954,957)},
            same_map_OBJ_and_pixels=True,numerical_both_faster=dense<0 and ack<0,
            selected_gate=all(protected.values()) and dense<0 and ack<0 and not regressions and not extra,
            pins={k:sha(new/k) for k in ('joint.json','events.json','window.csv','seal528.csv','obj-phases.json','packets.jsonl')})
    changed={f.name:sha(f) for f in a.arm.glob('nes_*.[ch]') if sha(f)!=sha(a.base_arm/f.name)}
    assert set(changed)=={'nes_plan_service200.c'}
    flash=(a.arm/'obj-nes-100/firmware.stm').stat().st_size
    r=dict(baseline='MMC666',candidate='bg675',phases=phases,firmware=firmware,
        Flash_B=flash,Flash_free_B=212992-flash,changed_ARM_sources=changed,
        ARM_data_B=10040,ARM_BSS_B=19544,extra_static_RAM_B=0,
        guards={f.name:dict(SHA256=sha(f),result=read(f)) for f in a.guards},
        RTL=rtl,RTL_matches_fitted_source_pins=True,
        function_stack_B={'emit_base':16,'emit_candidate':24,'poll_both':56,'drive_both':32,'flush_both':24,'bg675':0},
        selected='bg675' if len(phases)==2 and all(v['selected_gate'] for v in phases.values()) else 'MMC666',
        board_and_65816_unchanged=True,new_FIT_STA=False,new_delivery=False,
        board_reference='analysis/entry665-verification.json',prior_674='analysis/bg674-verification.json',
        scope='Actual linked ARM and65816; CPI2/shared SPI/IRQ model with measured periodic ROM calendar. Separate actual board RTL ownership test, not closed-loop live PSRAM or physical FPS.',
        sources={p.name:sha(p) for p in Path('tools').glob('*675.py')})
    a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    print(json.dumps({n:{k:v[k] for k in ('dense_delta_ms','last_ACK_delta_ms','protected','interval_regressions','new_final_waits','selected_gate')} for n,v in phases.items()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','arm','base-arm','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--phases',type=int,nargs='+',default=[1,2]);p.add_argument('--guards',type=Path,nargs='*',default=[])
    run(p.parse_args())
