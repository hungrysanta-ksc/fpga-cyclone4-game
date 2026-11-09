"""Budget MMC666 readiness separately from call entry, credit, ROM and consumption."""
import argparse
import json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import csv_groups,one,ms,sha,read
from analyze_nes_frontier536 import contents
from test_nes_service509_schedule import Calendar
from nes_schedule492 import funcs


def union_length(intervals):
    end=0;total=0
    for lo,hi in sorted(intervals):
        assert lo<=hi
        total+=max(0,hi-max(lo,end));end=max(end,hi)
    return total


def run(a):
    phases={};calendar=Calendar(a.calendar)
    assert funcs(Path('../probes/nes-trial666/arm01/src/obj-nes-100/sd2snes.elf'))==funcs(Path('../probes/nes-output664/all/src/obj-nes-100/sd2snes.elf'))
    # Group the two grant bursts within each measured safe window together.
    windows=[]
    for grant,response in calendar.pairs:
        if not windows or grant-windows[-1][-1][0]>10000:windows.append([])
        windows[-1].append((grant,response))
    assert len(windows)==8
    for phase in a.phases:
        base=a.traces/f'nes-entry665-a{phase}';folder=a.traces/f'nes-ready673-b{phase}'
        b,j=read(base/'joint.json'),read(folder/'joint.json')
        assert j['frames']==b['frames'] and j['wire_B']==b['wire_B'] and j['parameters']==b['parameters']
        assert j['client_SHA256']==b['client_SHA256']
        assert j['firmware_SHA256']==read(Path('analysis/trial666-package.json'))['firmware_SHA256']
        assert contents(base)[1]==contents(folder)[1]
        checked=trace(folder,a.traces/f'nes-front638-both{phase}h')
        events=read(folder/'events.json');cpu=csv_groups(folder/'window.csv');obj=read(folder/'obj-phases.json')
        calls={e['call']:e for e in events if e['event']=='call673'}
        returns={e['call']:e for e in events if e['event']=='return673'}
        assert calls.keys()==returns.keys(),(calls.keys()-returns.keys(),returns.keys()-calls.keys())
        rows={}
        for g in (954,957):
            d=checked['details'][g];ev=[e for e in events if e['generation']==g]
            immutable,=[e for e in ev if e['event']=='immutable673'];ready=immutable['clock']
            previous=d['previous_reveal'];end=one([r for r in cpu[g] if r['op']==3],'reveal')
            prior246upper=end['clock']+(247-end['line'])*1364-357368
            packets=[]
            for packet in d['packets']:
                if packet['section']<3 and packet['op']!=3:continue
                wire,=[e for e in ev if e['event']=='wire664' and e['op']==packet['op'] and e['section']==packet['section'] and e['offset']==packet['offset']]
                match=[c for c in calls.values() if c['generation']==g and c['name']=='packet_wire' and
                    c.get('section')==packet['section'] and c.get('offset')==packet['offset'] and
                    c['clock']<=wire['clock']<=returns[c['call']]['clock'] and
                    c['op'] in ({2,24} if packet['op'] in (2,4) else {packet['op']})]
                call=max(match,key=lambda c:c['clock']);assembled=wire['clock']
                credit_changes=[e for e in ev if e['event']=='credit673' and assembled<=e['clock']<=packet['start']]
                used=(wire['sent']-wire['retired'])&65535
                assert used<=4
                credit_at=assembled
                if used==4:
                    credit_at=next(e['clock'] for e in credit_changes if ((e['sent']-e['after'])&65535)<4)
                progress=union_length((max(call['clock'],c['clock']),min(assembled,returns[k]['clock'])) for k,c in calls.items()
                    if c['name']=='nes_plan200_progress' and c['generation']==g and call['clock']<=c['clock']<assembled)
                assert ready<=call['clock']<=assembled<=packet['start']<=packet['push']<=packet['load']<=packet['ack']
                terms=dict(ready_to_request=ms(call['clock']-ready),producer_service=ms(progress),
                    packet_assembly=ms(assembled-call['clock']-progress),credit_return_wait=ms(credit_at-assembled),
                    window_encode_guard=ms(packet['start']-credit_at),
                    SPI=ms(packet['push']-packet['start']),queue=packet['queue_ms'],consumer=packet['consumer_ms'])
                # packets.jsonl floors the fractional ARM completion to the
                # SNES integer timeline. Reconcile at that same boundary.
                assert abs(terms['SPI']-packet['SPI_ms'])<ms(1)
                assert abs(sum(terms.values())-ms(packet['ack']-ready))<1e-6,(phase,g,packet,terms,sum(terms.values())-ms(packet['ack']-ready))
                packets.append(dict(op=packet['op'],section=packet['section'],offset=packet['offset'],expanded_B=packet['expanded_B'],
                    ready=ready,request=call['clock'],assembled=assembled,**{k:packet[k] for k in ('start','push','load','ack')},terms_ms=terms,
                    queue_used_on_entry=used,credit_changes=credit_changes))
            plans=[]
            for k,c in calls.items():
                if c['generation']!=g or c['name']!='nes_plan200_emit':continue
                q=bytes.fromhex(c['plan']);plans.append(dict(kind=q[6],slot=int.from_bytes(q[2:4],'little'),tag=int.from_bytes(q[4:6],'little'),
                    enter=c['clock'],return_clock=returns[k]['clock']))
            cache=obj[str(g)]['cache611'];external=[r for r in cache if r[5]=='ROM'];captures=[r for r in cache if r[5]=='OBJ_capture']
            assert external and captures and not any(r[0] for r in external)
            gap=max((r[2]-p[4],p[4],r[2]) for p,r in zip(captures,captures[1:]))
            # Final external grant's preceding calendar window is used only to
            # quantify the required earlier plan release, not as a new schedule.
            last_rom=max(r[4] for r in external)
            repeat=int(last_rom//calendar.period)
            nearby=[[(cycle*calendar.period+lo,cycle*calendar.period+hi) for lo,hi in w]
                    for cycle in (repeat-1,repeat,repeat+1) for w in windows]
            current_window=next(w for w in nearby if w[0][0]<=last_rom<=w[-1][1])
            previous_window=max((w for w in nearby if w[-1][1]<current_window[0][0]),key=lambda w:w[-1][1])
            bg=[]
            for i,p in enumerate(plans):
                if p['kind']!=0:continue
                accesses=[r for r in external if r[1]//16==p['tag']]
                assert len(accesses)==8
                bank=next(b for b in obj[str(g)]['banks557'] if b['first']<=i<b['first']+b['count'])
                bg.append(dict(**p,plan_bank_accept=bank['seal'],first_request=accesses[0][2],last_response=accesses[-1][4],
                    caller_late_to_prior_ROM_close_ms=ms(p['enter']-previous_window[-1][1]),
                    batch_accept_late_to_prior_ROM_close_ms=ms(bank['seal']-previous_window[-1][1])))
            tile=[]
            for p in d['packets']:
                if p['op']!=7:continue
                unit=32 if p['section'] else 16
                ps=[r for r in plans if (r['kind']==1)==bool(p['section']) and p['offset']<=r['slot']*unit<p['offset']+p['expanded_B']]
                tile.append(dict(kind=p['section'],offset=p['offset'],bytes=p['expanded_B'],last_plan_call=max(r['enter'] for r in ps),
                    last_plan_return=max(r['return_clock'] for r in ps),request=p['prepared'],**{k:p[k] for k in ('start','push','load','ack')}))
            check_ms=d['terms']['checks']
            last_ack=max(p['ack'] for p in tile)
            seal=next(p for p in d['packets'] if p['op']==3)
            # Optimistic budget scenarios. They do not change/readjust any real
            # timestamp, skip validation in the replay, or assert a new FPS.
            # Descriptor187B transfer + observed existing check service remain.
            seal_wire=seal['wire_B']*8/2625000*1000
            external_floor=last_rom+ (seal_wire+check_ms)*21477272/1000
            ordinary_only=last_ack+(seal_wire+check_ms)*21477272/1000
            rows[g]=dict(previous_reveal=previous,immutable=immutable,ordinary=packets,tiles=tile,plans=plans,
                output_enter=next(e['clock'] for e in ev if e['event']=='output_enter531'),
                last_external_ROM=last_rom,external_ROM_reads=len(external),last_OBJ_capture=captures[-1][4],OBJ_capture_reads=len(captures),
                largest_OBJ_capture_gap=dict(ms=ms(gap[0]),start=gap[1],end=gap[2]),
                cache_modes=sorted({r[5] for r in cache}),end_plan_accepted=obj[str(g)]['end_accepted'],
                plan_banks=obj[str(g)]['banks557'],source_close=obj[str(g)]['boundaries561'],
                prior_246_end_upper=prior246upper,
                budget=dict(ordinary_ready_to_prior246_ms=ms(prior246upper-ready),
                    unchanged_last_tile_ACK_late_ms=ms(last_ack-prior246upper),
                    last_external_ROM_late_ms=ms(last_rom-prior246upper),
                    ordinary_only_SEAL_check_late_ms=ms(ordinary_only-prior246upper),
                    ideal_credit_and_zero_ordinary_SEAL_check_late_ms=ms(external_floor-prior246upper),
                    retained_SEAL_wire_ms=seal_wire,retained_checks_ms=check_ms,
                    assumptions='Optimistic necessary budget only. No ordinary preparation/wire/consumer cost, no tile DMA/setup/driver cost in ideal-credit scenario. Existing last external ROM response and observed checks retained; not an implemented candidate or a universal WCET proof.'),
                prior_ROM_window=dict(first_grant=previous_window[0][0],last_response=previous_window[-1][1],transactions=len(previous_window)),
                BG_readiness=bg,
                ordinary_totals_ms={key:sum(p['terms_ms'][key] for p in packets if p['op']!=3)
                                    for key in ('producer_service','packet_assembly','credit_return_wait','window_encode_guard','SPI','consumer')},
                timing=dict(interval=checked['intervals'][g],early_DMA_B=checked['early_DMA_B'][g],marks=d['marks']),
                E9=[e for e in ev if e.get('opcode')=='0xe9'])
        seal911=[r for r in cpu[911] if r['op']==3]
        phases[phase]=dict(instrumentation_same_all_ACKs=True,same_work_and_pixels=True,rows=rows,
            protected=dict(deadline911=one(seal911,'load')['line']==189 and one(seal911,'upload165_entry')['line']==214,
                reveal951=checked['details'][951]['marks']['reveal']['line']<=246,interval952=checked['intervals'][952]['VBlank']==3,
                final_wait957=checked['intervals'][957]['final_waits']==0),
            dense_mean_ms=checked['checked']['dense_mean_ms'],dense_VBlank=checked['checked']['dense_VB'],last_ACK=checked['checked']['last_ACK'],
            pins={n:sha(folder/n) for n in ('joint.json','events.json','window.csv','seal528.csv','obj-phases.json','packets.jsonl')})
        assert all(phases[phase]['protected'].values())
        assert all(r['budget']['ideal_credit_and_zero_ordinary_SEAL_check_late_ms']>0 for r in rows.values())
    result=dict(baseline='MMC666',selected='MMC666',stage=673,phases=phases,
        scope='Read-only actual linked M4/65816 and independent output checks, unchanged CPI2/shared SPI/IRQ and measured repeating ROM calendar. Readiness budget sensitivity only; no changed product or improved physical/replay interval claimed.',
        new_firmware=False,new_RTL=False,new_FIT_STA=False,new_delivery=False,
        calendar=calendar.summary,
        unchanged_resources=dict(ARM_Flash_B=212496,ARM_free_B=496,ARM_data_B=10040,ARM_BSS_B=19544,
            SNES_physical_ROM_B=5120,SNES_physical_free_B=11,LE=15324,LAB=962,M9K=56,
            reference='analysis/trial666-package.json; analysis/entry665-verification.json'),
        retained_guards='No product changes. New runs check independent outputs/identity/final ACK and protected timing. STOP, cold/capture and menu/base use unchanged selected binaries and existing666 evidence; no new fault injection or physical menu test.',
        decision='Retain MMC666. Ordinary-only and ideal-credit with the current final external ROM response both miss the prior246 deadline. Next test early BG batch handoff (957) and earlier validated BG calculation (954), alongside ordinary scheduling. No new improved schedule has been implemented.',
        limitations=['Field last-write is not semantic readiness: scratch reuse and planner validation remain. Immutable means successful planner return and no later value changes in the watched region for these measured frames.',
                    'ready664 is packet_wire entry BEFORE producer service and packet assembly. wire664 is window entry after assembly.',
                    'Credit wait ends at ARM checked retired update; status/STOP/wait return and encoding remain in window_encode_guard. It is not a raw FPGA credit edge.',
                    'Only packet-local additive terms reconcile. Sums of consumer and producer-service time overlap and must not be added as a whole-frame saving.',
                    'The prior246 timestamp is a conservative upper bound from integer line observations, at most one line late; no horizontal phase precision claim.',
                    'BG caller versus prior ROM close is an optimistic necessary budget only, excluding E8/E9, descriptor decode, slot credit and eight grants per tile.'],
        source_hashes={p.name:sha(p) for p in Path('tools').glob('*673.py')})
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({n:{g:r['budget'] for g,r in p['rows'].items()} for n,p in phases.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','calendar','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--phases',type=int,nargs='+',default=[1,2]);run(p.parse_args())
