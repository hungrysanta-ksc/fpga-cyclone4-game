"""Receiver-only deadline sensitivity and unpaid producer/ROM costs.

Arrival advances are diagnostic, NOT executable ARM schedules or measured FPS.
The two controls must reproduce all 53 original CPU traces clock for clock.
"""
import argparse,csv,json
from pathlib import Path
from analyze_nes_output615 import read,sha,csv_groups,one,ms
from analyze_nes_output531 import prior_blank_windows
from analyze_nes_output664 import trace

ROOT=Path(__file__).resolve().parents[1]

def analyze(a):
    old=read(ROOT/'analysis/credit710-verification.json')
    phases={}
    tags=['control','seal16667','tail16667']+[f'all{n}' for n in (8000,10000,12000,14000,15000,15500,15750,16000)]
    for phase in (1,2):
        folder=a.temp/f'nes-bg707-step{phase}'
        base=old['phases'][str(phase)]['base']
        assert all(sha(folder/n)==v for n,v in base['pins'].items())
        details=trace(folder,a.temp/f'nes-front638-both{phase}h')['details']
        before=csv_groups(folder/'window.csv');beam=csv_groups(folder/'seal528.csv')
        events=read(folder/'events.json');obj=read(folder/'obj-phases.json')
        ps=[json.loads(s) for s in (folder/'packets.jsonl').read_text().splitlines()]
        spi=[e for e in events if e.get('opcode')=='0xe1']
        assert len(spi)==len(ps)==1277
        baseline={}
        for g in range(951,958):
            d=details[g];rows=d['packets'];seal=[r for r in before[g] if r['op']==3]
            previous=one([r for r in before[g-1] if r['op']==3],'reveal')
            anchor=next(r for r in reversed(beam[g]) if r['event']=='dma' and r['port']==4)
            final=one(seal,'reveal')
            cutoff=sorted(prior_blank_windows(anchor,final['frame'],previous['clock'],anchor['clock'],246))[-2][1]
            last_tile=max(i for i,r in enumerate(rows) if r['op']==7)
            after=rows[last_tile+1:]
            baseline[g]=dict(previous_246_end=cutoff,SEAL_load_late_ms=ms(d['marks']['load']['clock']-cutoff),
                checks_ms=d['terms']['checks'],necessary_load_advance_with_checks_ms=ms(d['marks']['load']['clock']-cutoff)+d['terms']['checks'],
                note='Necessary only: excludes remaining DMA and post-check CPU work; not a sufficient deadline.',
                terms=d['terms'],last_tile_ACK_to_SEAL_ms=d['last_tile_to_SEAL_load_ms'],
                tail_packets=len(after),tail_wire_B=sum(r['wire_B'] for r in after),
                tail_SPI_ms=sum(r['SPI_ms'] for r in after),
                queue_max_ms=max(r['queue_ms'] for r in rows),
                ready_to_SPI_max_ms=max(r['ready_to_SPI_ms'] or 0 for r in rows),
                map_expanded_B=sum(r['expanded_B'] for r in rows if r['section']==2),
                tile_B=sum(r['expanded_B'] for r in rows if r['op']==7))
        runs={}
        for tag in tags:
            name=f'nes-deadline711-{tag}-{phase}' if tag!='control' else f'nes-deadline711-control0{phase+2}'
            path=a.temp/name;r=read(path/'audit711.json')
            assert r['passed'] and r['same_pixels'] and r['prefix_exact'] and r['full_CRC_coverage_ACK']
            assert all(sha(path/n)==v for n,v in r['pins'].items())
            assert sha(path/'client.sfc')==sha(folder/'client.sfc')==r['client_SHA256']
            cpu=csv_groups(path/'window.csv')
            assert all(cpu[g]==before[g] for g in before if tag=='control' or g<951)
            assert all(sha(path/f'frame-{g}.rgb')==sha(folder/f'frame-{g}.rgb') for g in range(905,958))
            arrivals=(path/'arrivals.tsv').read_text().splitlines()
            assert len(arrivals)==len(ps)+1
            assert all(line.split('\t')[1:]==[p[2],p[3]] for line,p in zip(arrivals[:-1],ps,strict=True))
            admission=list(csv.DictReader((path/'admission711.csv').open()))
            assert len(admission)==len(ps) and max(int(x['depth']) for x in admission)<=4 and max(int(x['bulk']) for x in admission)<=2
            metrics=r['metrics']
            # Early audits counted entry to wait_final516, not an actual wait.
            # Derive waits from raw CPU trace for every run, retaining old audits.
            for g in range(951,958):
                s=[x for x in cpu[g] if x['op']==3]
                metrics[str(g)]['final_waits']=sum(x['event']=='wait169' and x['clock']>=one(s,'final212')['clock'] for x in s)
            protected=metrics['951']['show']['line']<=246 and metrics['952']['interval_VBlank']==3 and metrics['957']['final_waits']==0
            runs[tag]=dict(folder=name,dense_mean_ms=r['dense_mean_ms'],dense_delta_ms=r['dense_mean_ms']-base['dense_mean_ms'],
                last_ACK=r['last_ACK'],ACK_delta_ms=ms(r['last_ACK']-base['last_ACK']),metrics=metrics,
                all_951_957_one_VBlank_earlier=all(v['show_frame_delta']==-1 for v in metrics.values()),
                protected=protected,simultaneous_gate=protected and r['dense_mean_ms']<base['dense_mean_ms'] and r['last_ACK']<base['last_ACK'],
                same_packets_pixels=True,original_905_950_exact=True,queue_credits=4,bulk_slots=2,pins=r['pins'],
                new_ARM=False,new_ROM_service=False,new_FPGA=False)
            runs[tag]['credit_scope']='Receiver admission is bounded to4heads/2bulk; offers are precomputed. Delayed admission does not rerun ARM credit queries or charge a fresh SPI transaction after credit returns. This is an optimistic availability bound, not a legal full bus schedule.'
            runs[tag]['after_first_interval_mean_ms']=sum(metrics[str(g)]['interval_ms'] for g in range(952,958))/6
            runs[tag]['after_first_interval_VBlank']=[metrics[str(g)]['interval_VBlank'] for g in range(952,958)]
            if tag=='control':assert r['last_ACK']==base['last_ACK'] and abs(r['dense_mean_ms']-base['dense_mean_ms'])<1e-10
        # Charge all15750 hypothetical packets against the actual producer.
        # A ready664 timestamp is measured preparation, not earliest semantic
        # readiness. Only negative ROM/capture precedence proves incompatibility
        # with the unchanged source schedule. It does not rule out rescheduling.
        target=a.temp/f'nes-deadline711-all15750-{phase}'
        offers={int(x['index']):x for x in read(target/'audit711.json')['offers']}
        admission={int(x['index']):int(x['admit']) for x in csv.DictReader((target/'admission711.csv').open())}
        target_cpu=csv_groups(target/'window.csv');debt={};global_indices={}
        for i,p in enumerate(ps,1):
            h=bytes.fromhex(p[2]);g=int.from_bytes(h[8:10],'little');global_indices.setdefault(g,[]).append(i)
        for g in range(951,958):
            d=details[g];rows=d['packets'];ix=global_indices[g]
            ev=[e for e in events if e['generation']==g]
            marks={n:next(e['clock'] for e in ev if e['event']==n) for n in ('source_begin','bg_map_frozen','prepare_enter')}
            loads=[e for e in target_cpu[g] if e['event']=='load'];assert len(loads)==len(rows)
            prep=[]
            for index,row in zip(ix,rows,strict=True):
                offer=offers[index]['offer'];duration=spi[index-1]['clock']-spi[index-1]['start']
                if row['prepared'] is not None:prep.append(ms(max(0,row['prepared']-(offer-duration))))
            rom={}
            for kind in (0,1):
                last=max((i for i,row in enumerate(rows) if row['op']==7 and row['section']==kind),default=None)
                cr=[r for r in obj[str(g)]['cache611'] if r[0]==kind]
                if last is not None and cr:
                    response=max(r[4] for r in cr)
                    rom[kind]=dict(last_supply_response=response,last_packet_load=loads[last]['clock'],
                        source_must_advance_at_least_ms=ms(max(0,response-loads[last]['clock'])),
                        includes_cache_and_ROM=True,physical_ROM_reads=sum(r[5]=='ROM' for r in cr))
            debt[g]=dict(producer_marks=marks,first_admit=admission[ix[0]],
                first_offer_before_source_begin_ms=ms(max(0,marks['source_begin']-offers[ix[0]]['offer'])),
                first_admit_before_source_begin_ms=ms(max(0,marks['source_begin']-admission[ix[0]])),
                prepared_earlier_count=sum(x>0 for x in prep),max_measured_preparation_advance_ms=max(prep,default=0),
                source_supply=rom,SEAL_measured_ready=rows[-1]['prepared'],SEAL_offer=offers[ix[-1]]['offer'],
                unmodeled='ARM instruction execution, D1/D2/E0/E9/EA/IRQ, credit-stalled SPI rescheduling and ROM retiming; original E1 durations are retained in offer times only.')
        phases[phase]=dict(baseline=baseline,runs=runs,all15750_unpaid_producer_cost=debt,
            baseline_pins=base['pins'],actual_full_path_baseline_only=True)
    both={tag:all(p['runs'][tag]['simultaneous_gate'] and p['runs'][tag]['all_951_957_one_VBlank_earlier'] for p in phases.values()) for tag in tags}
    assert both['all15750'] and both['all16000'] and not both['all15500']
    report=dict(stage=711,scope=__doc__,phases=phases,both_conditional_gates=both,
        target_selected='707D + original ARM694/704 + original65816; unchanged',
        receiver_runs=2*len(tags),CPU_frames=106*len(tags),new_target_implementation=False,
        no_global_minimum_claim=True,nonmonotone=True,new_physical_test=False,
        throughput_warning='Uniform earlier arrivals shift the sequence, not its cadence: all15750 keeps952..957 at3VBlank. The951..955 mean includes the one-time951 3->2VBlank gain. No sustained throughput or60fps improvement is established.',
        resources=dict(ARM_long_B=212940,ARM_60s_B=212984,ARM_limit_B=212992,ARM_free_long_B=52,ARM_free_60s_B=8,
            LE=15322,LE_free=86,LAB=962,LAB_free=1,M9K=56,M9K_free=0,RAM_bits=305264,
            CPU_body_free_B=380,CPU_physical_ROM_free_B=26,delta_Flash_B=0,delta_RAM_B=0,delta_LE=0,
            whole_FIT_STA='Inherited exact707D; no changed RTL and no new synthesis',STA_ns=dict(setup=.362,hold=.145,recovery=1.594,removal=.483)),
        safety=dict(independent_CPU_checks='Executed in each completed replay; identical work and all 53 pixel images',
            STOP_menu='Inherited unchanged707D/694/704 proof; no new STOP fault-injection or physical menu run',
            seven_block_overlap='Original full-path baseline only; hypothetical early-output cases require new ARM/input proof',
            firstfault_capture_recovery='Unchanged target; no newly implemented recovery'),
        next_budget=dict(boundary='Immutable map-range producer/issuer ownership together with tile/source readiness; existing E1 ABI first',
            existing_ARM_functions_B=dict(map527=364,nes_sink527_early=104,nes_plan527_map_credit=70),
            proven_deletion_B=0,ARM_net_growth_limit_normal_B=8,ARM_net_growth_limit_long_B=52,
            new_packet_buffers_B=0,ready_bitmap_candidate_max_B=8,ready_bitmap_implemented=False,
            planned_RTL_delta=0,planned_CPU_delta=0,
            cadence_gate='Both phases: sum952..957 intervals<18VBlank, plus original951/952/957 protection, dense951..955 andlastACK improve; actualARM/input/ROM required.'),
        analysis_correction='final wait counts recomputed from wait169 after final212, not entry to wait_final516',
        evidence_refs={n:sha(ROOT/'analysis'/n) for n in ('credit710-verification.json','bg707-verification.json','longrun694-verification.json')})
    a.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(runs=report['receiver_runs'],frames=report['CPU_frames'],both=both)))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--temp',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    analyze(p.parse_args())
