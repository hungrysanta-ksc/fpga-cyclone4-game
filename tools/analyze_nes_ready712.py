"""Actual unchanged producer/credit/ROM ledger and bounded replacement budget.

No earlier packet is injected. Measured waits are not additive free savings.
"""
import argparse,json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_ready673 import union_length
from analyze_nes_seal686 import receive_batch
from nes_schedule492 import funcs
from test_nes_service509_schedule import Calendar

ROOT=Path(__file__).resolve().parents[1]

def subtract(intervals,busy):
    result=[]
    for lo,hi in intervals:
        for start,end in sorted(busy):
            if end<=lo:continue
            if start>=hi:break
            if lo<start:result.append((lo,min(start,hi)))
            lo=max(lo,end)
            if lo>=hi:break
        if lo<hi:result.append((lo,hi))
    return result

def run(a):
    phases={};deadline=read(ROOT/'analysis/deadline711-budget.json')
    calendar=Calendar(a.temp/'nes-service509-rom03');windows=[]
    for grant,response in calendar.pairs:
        if not windows or grant-windows[-1][-1][0]>10000:windows.append([])
        windows[-1].append((grant,response))
    for phase in (1,2):
        base=a.temp/f'nes-bg707-step{phase}';folder=a.temp/f'nes-ready712-row{phase}'
        b,j=read(base/'joint.json'),read(folder/'joint.json')
        assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2
        for k in ('frames','parameters','wire_B','ARM_instructions','firmware_SHA256','client_SHA256','ROM_read_allocations'):
            assert j[k]==b[k],(phase,k)
        for n in ('window.csv','packets.jsonl','obj-phases.json'):
            assert sha(base/n)==sha(folder/n),(phase,n)
        assert all(sha(base/f'frame-{g}.rgb')==sha(folder/f'frame-{g}.rgb') for g in range(905,958))
        t=trace(folder,a.temp/f'nes-front638-both{phase}h')
        events=read(folder/'events.json');obj=read(folder/'obj-phases.json');cpu=csv_groups(folder/'window.csv')
        cc={e['call']:e for e in events if e['event']=='call673'};cr={e['call']:e for e in events if e['event']=='return673'}
        calls={e['call']:e for e in events if e['event']=='call712'};returns={e['call']:e for e in events if e['event']=='return712'}
        assert calls.keys()==returns.keys()
        result={}
        for g in range(951,958):
            ev=[e for e in events if e['generation']==g];d=t['details'][g]
            frozen=one(ev,'map_frozen712');planner=one(ev,'planner712')
            spi=[e for e in ev if e['event']=='SPI'];busy=[(e['start'],e['clock']) for e in spi]
            map_events=[e for e in ev if e['event']=='map_packet712']
            rows=[p for p in d['packets'] if p['section']==2]
            assert len(rows)==len(map_events)
            maps=[]
            for p,m in zip(rows,map_events,strict=True):
                assert p['offset']==m['offset'] and p['expanded_B']==m['bytes'] and p['prepared']==m['clock']
                call=next(c for c in cc.values() if c['generation']==g and c['name']=='packet_wire' and c['clock']==m['clock'])
                wire=next(e for e in ev if e['event']=='wire664' and e['section']==2 and e['offset']==m['offset'])
                service=union_length((max(call['clock'],c['clock']),min(wire['clock'],cr[k]['clock']))
                    for k,c in cc.items() if c['generation']==g and c['name']=='nes_plan200_progress' and call['clock']<=c['clock']<wire['clock'])
                used=(wire['sent']-wire['retired'])&65535;assert used<=4
                credit=wire['clock']
                if used==4:
                    credit=next(e['clock'] for e in ev if e['event']=='credit673' and wire['clock']<=e['clock']<=p['start'] and ((e['sent']-e['after'])&65535)<4)
                terms=dict(producer_service=ms(service),assembly=ms(wire['clock']-call['clock']-service),
                    checked_credit_wait=ms(credit-wire['clock']),encode_guard=ms(p['start']-credit),SPI=p['SPI_ms'],queue=p['queue_ms'],consumer=p['consumer_ms'])
                assert abs(sum(terms.values())-ms(p['ack']-call['clock']))<ms(1)
                # Last write is a lower bound, never a semantic-ready promise.
                last=max(m['last_write']);write_bound=max(last,planner['clock'])
                indices=[i%32 for i in range(m['offset']//64,(m['offset']+m['bytes'])//64)]
                semantic=max(frozen['row_complete'][i] if i<len(frozen['row_complete']) else frozen['clock'] for i in indices)
                assert semantic<=m['clock'],(phase,g,m['offset'],semantic,m['clock'])
                post_freeze=max(0,m['clock']-frozen['clock'])
                bus_free=subtract([(frozen['clock'],m['clock'])],busy) if post_freeze else []
                maps.append(dict(offset=p['offset'],bytes=m['bytes'],page=p['offset']//2048,
                    last_write=last,request=m['clock'],frozen=frozen['clock'],load=p['load'],ack=p['ack'],
                    row_complete=semantic,row_complete_to_request_ms=ms(m['clock']-semantic),
                    write_to_request_ms=ms(m['clock']-write_bound),frozen_to_request_ms=ms(post_freeze),
                    SPI_free_after_freeze_upper_ms=ms(union_length(bus_free)),
                    state={k:m[k] for k in ('map_next','pair','queued','count','sent','bulk_pending','bulk_valid','ending')},terms_ms=terms))
            gates=[]
            for k,c in calls.items():
                if c['generation']!=g or c['name']!='nes_plan527_map_credit':continue
                r=returns[k];ss=[e for e in spi if c['clock']<=e['start']<=r['clock']]
                reason='available' if r['ready'] else 'queue_reserve' if c['queued']>=3 else 'held_bulk_credit' if not ss else 'ready_or_repeated_tile'
                assert r['result']==1
                gates.append(dict(start=c['clock'],end=r['clock'],reason=reason,instructions=r['instructions'],
                    SPI_B=sum(e['bytes'] for e in ss),SPI_ms=sum(ms(e['clock']-e['start']) for e in ss),state=c))
            functions={}
            for name in ('map527','nes_sink527_early','nes_plan527_map_credit','offer527'):
                rs=[r for r in returns.values() if r['generation']==g and r['name']==name]
                functions[name]=dict(calls=len(rs),inclusive_instructions=sum(r['instructions'] for r in rs),
                    inclusive_ms=sum(ms(r['clock']-r['start']) for r in rs))
                if name=='map527':
                    own=0
                    for r in rs:
                        children=[k for k,c in cc.items() if c['name']=='packet_wire' and r['start']<=c['clock'] and cr[k]['clock']<=r['clock']]
                        own+=r['instructions']-sum(cr[k]['instructions'] for k in children)
                    functions[name]['excluding_packet_children_instructions']=own
                    functions[name]['excluding_packet_children_CPI2_ms']=own*2/84000
            plans=[]
            for k,c in cc.items():
                if c['generation']!=g or c['name']!='nes_plan200_emit':continue
                q=bytes.fromhex(c['plan']);plans.append(dict(kind=q[6],slot=int.from_bytes(q[2:4],'little'),tag=int.from_bytes(q[4:6],'little'),
                    request=c['clock'],returned=cr[k]['clock']))
            rom=obj[str(g)]['cache611'];tiles=[]
            for p in d['packets']:
                if p['op']!=7:continue
                kind=p['section'];unit=32 if kind else 16
                owned=[r for r in plans if r['kind'] in ((1,) if kind else (0,2)) and p['offset']<=r['slot']*unit<p['offset']+p['expanded_B']]
                assert owned,(phase,g,p)
                indexes=[i for i,r in enumerate(plans) if r in owned]
                banks=[v for v in obj[str(g)]['banks557'] if any(v['first']<=i<v['first']+v['count'] for i in indexes)]
                supplies=[r for r in rom if r[0]==kind and any(r[1]//16==q['tag'] for q in owned if q['kind']!=2)]
                tiles.append(dict(kind=kind,offset=p['offset'],bytes=p['expanded_B'],plan_last_call=max(q['request'] for q in owned),
                    plan_last_return=max(q['returned'] for q in owned),banks=banks,
                    last_matching_supply=max((r[4] for r in supplies),default=None),
                    packet_request=p['prepared'],SPI_start=p['start'],accepted=p['push'],load=p['load'],ack=p['ack'],
                    matching_scope='Tags can recur; last matching supply is diagnostic, not one-to-one token/slot ownership. Bank/plan bounds are exact.'))
            # A budget on already-frozen map with existing SPI activity retained.
            # These holes are NOT proven spare CPU or queue credit and overlap
            # existing producer execution. Do not sum them across map packets.
            end=one(ev,'end_enter')['clock'];post=[m for m in maps if m['request']>=frozen['clock']]
            holes=subtract([(frozen['clock'],end)],busy) if end>frozen['clock'] else []
            interval=t['intervals'][g]
            external=[r for r in rom if r[5]=='ROM'];last_rom=max((r[4] for r in external),default=None)
            rom_budget=None
            if last_rom:
                cycle=int(last_rom//calendar.period)
                nearby=[[(cy*calendar.period+lo,cy*calendar.period+hi) for lo,hi in w] for cy in (cycle-1,cycle,cycle+1) for w in windows]
                current=next(w for w in nearby if w[0][0]<=last_rom<=w[-1][1])
                previous=max((w for w in nearby if w[-1][1]<current[0][0]),key=lambda w:w[-1][1])
                last_bg=max(q['returned'] for q in plans if q['kind']==0)
                rom_budget=dict(previous_close=previous[-1][1],last_BG_return=last_bg,
                    last_BG_return_late_ms=ms(last_bg-previous[-1][1]),
                    excludes='E8/credit/E9/CRC/decode and grants; necessary earlier-production bound only')
            # Only the existing synchronous emit/flush call sites. These are
            # not all theoretical stalls obtainable by a different producer.
            emit_waits=[(c['clock'],cr[k]['clock']) for k,c in cc.items() if c['generation']==g and c['name']=='nes_plan200_emit']
            intersections=[]
            for m in maps:
                if m['page']!=1:continue
                for lo,hi in emit_waits:
                    for r in external:
                        left=max(m['row_complete'],lo,r[2]);right=min(m['request'],hi,r[3],frozen['clock'])
                        if left<right:intersections.append((left,right))
            remaining=[p for p in d['packets'] if p['start']>=max(r[4] for r in rom)]
            retained_checks=d['terms']['checks'];remaining_spi=sum(p['SPI_ms'] for p in remaining)
            previous246=deadline['phases'][str(phase)]['baseline'][str(g)]['previous_246_end']
            wire_check_deficit=ms(max(r[4] for r in rom)-previous246)+remaining_spi+retained_checks
            result[g]=dict(map_frozen=frozen['clock'],planner=planner['clock'],END=end,maps=maps,credit_gates=gates,
                function_calls=functions,plans=plans,tiles=tiles,ROM_modes={mode:sum(r[5]==mode for r in rom) for mode in {r[5] for r in rom}},
                ROM_wait_ms=sum(ms(r[3]-r[2]) for r in rom if r[5]=='ROM'),ROM_service_ms=sum(ms(r[4]-r[3]) for r in rom if r[5]=='ROM'),
                last_external_ROM=max((r[4] for r in rom if r[5]=='ROM'),default=None),last_supply=max(r[4] for r in rom),
                BG_prior_window_budget=rom_budget,
                right_map_ready_emit_ROM_wait_union_upper_ms=ms(union_length(intersections)),
                right_map_ready_emit_ROM_wait_SPI_free_upper_ms=ms(union_length(subtract(intersections,busy))),
                remaining_E1_after_supply_B=sum(p['wire_B'] for p in remaining),remaining_E1_service_ms=remaining_spi,
                remaining_E1_plus_checks_late_ms=wire_check_deficit,
                remaining_cost_scope='Actual remaining E1 and checks only; no E0/E8/input/IRQ/extra ARM/DMA service added. Necessary deficit, not a complete retimed schedule.',
                frozen_to_END_ms=ms(end-frozen['clock']),frozen_to_END_SPI_free_upper_ms=ms(union_length(holes)),
                map_after_BG_B=sum(m['bytes'] for m in post),map_after_BG_wire_ms=sum(m['terms_ms']['SPI'] for m in post),
                packet_local_totals_ms={k:sum(m['terms_ms'][k] for m in maps) for k in maps[0]['terms_ms']},
                actual_interval=interval,deadline711=deadline['phases'][str(phase)]['baseline'][str(g)],
                no_additive_savings_claim=True)
        s911=[r for r in cpu[911] if r['op']==3]
        protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
            public951=t['details'][951]['marks']['reveal']['line']<=246,interval952=t['intervals'][952]['VBlank']==3,
            final_wait957=t['intervals'][957]['final_waits']==0,seven_blocks=receive_batch(folder)['checked_blocks_before_ACK']==7)
        assert all(protected.values())
        phases[phase]=dict(rows=result,all_53_clocks_work_pixels_unchanged=True,protected=protected,
            after951_VBlank=sum(t['intervals'][g]['VBlank'] for g in range(952,958)),
            after951_mean_ms=sum(t['intervals'][g]['ms'] for g in range(952,958))/6,
            dense_mean_ms=t['checked']['dense_mean_ms'],last_ACK=t['checked']['last_ACK'],
            pins={n:sha(folder/n) for n in ('joint.json','events.json','window.csv','packets.jsonl','obj-phases.json','seal528.csv','progress680.csv')})
    functions=funcs(a.arm/'obj-nes-100/sd2snes.elf')
    names=('map527','nes_sink527_early','nes_plan527_map_credit','offer527','quiet528','drive554','nes_plan200_progress')
    sizes={n:next(k[2] for k in functions if k[0]==n) for n in names}
    assert sum(sizes.values())==1108,sizes
    report=dict(stage=712,baseline='707D + original694/704 ARM and65816',scope=__doc__,phases=phases,
        source_files={n:sha(a.arm/n) for n in ('nes_planner211.c','nes_native_runtime165.c','nes_native_sink165.c','nes_plan_service200.c','nes_plan_service200.h')},
        replacement_budget=dict(functions_B=sizes,gross_boundary_B=1108,proven_net_deletion_B=0,
            normal_growth_limit_B=8,long_growth_limit_B=52,normal_replacement_ceiling_B=1116,
            preferred_replacement_ceiling_B=1108,RAM_growth_ceiling_B=4,new_packet_buffer_B=0,
            new_RTL_LE=0,new_SNES_ROM_B=0,new_SPI_transactions_preferred=0,
            retained='poll/CRC/counter/descriptor identity, complete485 actual bulk receipt, wire packet validation, final SEAL coverage and display ACK/EA; no deletion credit for these functions'),
        proposed_boundary='Two page cursors and logical-row readiness frontier; service already-final map from existing empty-producer poll path before END, replacing early/final/quiet arbitration. No pointer to unfinal rows, no new capture read or queue.',
        decision=dict(selected_implementation=False,confirmed_replacement_boundary=True,
            existing_wait_insertion_funded=False,
            reason='Existing emit/flush ROM-wait SPI holes cannot fund one unchanged 192B map packet. A new row order must pay blocking SPI and preserve tile production/ROM deadlines; no net timing win is yet established.',
            pre_supply957_minimum=dict(method='Move unchanged 192B map E1 service only; excludes preparation, other SPI/IRQ and remaining DMA',
                packet_SPI_ms=211*8/2625+0.04978286503309517,necessary_packet_count=3,
                required_shift_ms=[phases[p]['rows'][957]['remaining_E1_plus_checks_late_ms'] for p in (1,2)]),
            earlier_BG_production_ms={g:[phases[p]['rows'][g]['BG_prior_window_budget']['last_BG_return_late_ms'] for p in (1,2)] for g in (954,955)},
            runtime_pump_savings_not_equal_ROM_wait=True),
        selected_implementation=False,physical_FPS_gain=False,new_FIT_STA=False,
        safety='New read-only actualARM/65816 checks and clock identity; STOP/cold/capture/menu use unchanged original proof. A replacement must rerun these guards and full shared SPI schedule.',
        limits=['Measured last write is not semantic readiness. Source row-complete boundary/slot ownership is mandatory.',
            'SPI-free holes are upper budgets only; active ARM compute, credit and tile arbitration still cost time.',
            'Nested function/callback/consumer intervals overlap; never sum as whole-frame savings.',
            'ROM calendar is measured boot-window repetition, not closed-loop gameplay NES/PSRAM RTL.',
            'No711 earlier arrivals are reused. No optimized candidate cadence or deletion is claimed.'])
    a.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({p:{g:dict(post_BG_map_B=r['map_after_BG_B'],map_service=r['packet_local_totals_ms']['producer_service'],map_SPI=r['packet_local_totals_ms']['SPI'],map_credit=r['packet_local_totals_ms']['checked_credit_wait'],free_upper=r['frozen_to_END_SPI_free_upper_ms'],gates=[x['reason'] for x in r['credit_gates']]) for g,r in v['rows'].items()} for p,v in phases.items()}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('temp','arm','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
