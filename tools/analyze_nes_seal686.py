"""Same-work two-phase map pair, input credit, BG window and final ACK gates."""
import argparse,csv,difflib,inspect,json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_receive682 import receive_batch as prior_receive_batch,blocks956
from analyze_nes_bg674 import preparation,tile_image
from analyze_nes_frontier536 import contents
from analyze_nes_progress680 import grants
from nes_raw506 import once

# Reason3 is the existing SEAL ownership entry that converts to reason2.
# Keep the same checked token/CRC/POP/7-block oracle, including one block for
# all unsealed callbacks. Only its recorded reason classification changes.
_receive_scope=dict(read=read,ms=ms)
exec(once(inspect.getsource(prior_receive_batch),'if b[\'reason\']!=2:assert n<=1',"if b['reason'] not in (2,3):assert n<=1"),_receive_scope)
receive_batch=_receive_scope['receive_batch']

def run(a):
    phases={};image=a.arm/'src/obj-nes-100/firmware.stm';firmware=sha(image)
    calendar=a.traces/'nes-service509-rom03/fill1'
    anchors={int(x):int(y) for x,y in (line.split() for line in (calendar/'anchors.tsv').read_text().splitlines())}
    origin=anchors[12]-8;period=anchors[20]-anchors[12]
    windows={int(t)-origin:int(f)-12 for kind,t,f,*rest in (line.split() for line in (calendar/'rom.tsv').read_text().splitlines()) if kind=='R'}
    def rom_window(t):
        cycle,offset=divmod(t,period)
        return cycle*8+windows[offset]
    for phase in (1,2):
        folders={k:a.traces/v for k,v in [('MMC666',f'nes-ready673-b{phase}'),('685',f'nes-complete685-sealed{phase}'),('686',f'nes-seal686-arm{phase}')]}
        traces={k:trace(f,a.traces/f'nes-front638-both{phase}h') for k,f in folders.items()}
        js={k:read(f/'joint.json') for k,f in folders.items()};base=traces['MMC666'];old=traces['685'];rows={}
        oldplan=read(folders['685']/'obj-phases.json')
        for k,f in folders.items():
            c=traces[k];j=js[k]
            assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2
            assert j['parameters']==js['MMC666']['parameters']
            assert tile_image(f)==tile_image(folders['MMC666']) and contents(f)[1]==contents(folders['MMC666'])[1]
            assert {g:v['work'] for g,v in c['frames'].items()}=={g:v['work'] for g,v in base['frames'].items()}
            if k=='686':
                assert j['firmware_SHA256']==firmware and j['client_SHA256']==sha(a.client/'sink165.sfc')
                pin,=[e for e in read(f/'events.json') if e['event']=='image682_start'];assert pin['firmware']==firmware
                plan=read(f/'obj-phases.json')
                for g,p in oldplan.items():assert [(v['count'],v['first'],v['decoded']) for v in p['banks557']]==[(v['count'],v['first'],v['decoded']) for v in plan[g]['banks557']]
            cpu=csv_groups(f/'window.csv');s911=[r for r in cpu[911] if r['op']==3]
            protected=dict(deadline911=one(s911,'load')['line']<=189 and one(s911,'upload165_entry')['line']<=214,
                reveal951=c['details'][951]['marks']['reveal']['line']<=246,
                interval952=c['intervals'][952]['VBlank']==3,final_wait957=c['intervals'][957]['final_waits']==0)
            details={}
            for g in (955,956,957):
                d=c['details'][g]
                details[g]=dict(previous_reveal=d['previous_reveal'],marks=d['marks'],packets=d['packets'],
                    early_DMA_B=c['early_DMA_B'][g],grants=grants(f,g,d['packets']),BG=preparation(f,g)['BG'],
                    final_DMA=[{q:r[q] for q in ('clock','line','value')} for r in cpu[g] if r['event']=='ppu_dma' and r['op']==3])
            delta=c['checked']['dense_mean_ms']-base['checked']['dense_mean_ms'];ack=ms(c['checked']['last_ACK']-base['checked']['last_ACK'])
            regress=[g for g in base['intervals'] if c['intervals'][g]['VBlank']>base['intervals'][g]['VBlank']]
            waits=[g for g in base['intervals'] if c['intervals'][g]['final_waits']>base['intervals'][g]['final_waits']]
            rows[k]=dict(protected=protected,dense_mean_ms=c['checked']['dense_mean_ms'],dense_delta_MMC666_ms=delta,
                dense_VBlank=c['checked']['dense_VB'],last_ACK=c['checked']['last_ACK'],last_ACK_delta_MMC666_ms=ack,
                timing_gate=all(protected.values()) and delta<0 and ack<0 and not regress and not waits,
                regressions=regress,new_final_waits=waits,intervals=c['intervals'],details=details,wire_B=j['wire_B'],
                ARM_workspace_end=j['workspace_end'],ARM_observed_stack_low=j['observed_stack_low'],
                pins={p:sha(f/p) for p in ('joint.json','packets.jsonl','window.csv','events.json','obj-phases.json')})
            if k!='MMC666':
                r=receive_batch(f);rows[k]['receive956']=r;rows[k]['blocks956']=blocks956(f)
                rows[k]['checked_input_margin_ms']=ms(r['previous_ACK']-r['rows'][6]['returned'])
                ev=read(f/'events.json')
                rows[k]['map_handoff']={g:dict(
                    calls=[{q:e[q] for q in ('clock','name','op','offset','bytes')} for e in ev if e['generation']==g and e['event']=='call673' and e['name']=='packet_wire' and e['section']==2 and e['offset'] in (1024,1216)],
                    immutable=next(e['clock'] for e in ev if e['generation']==g and e['event']=='immutable673'),
                    END_call=next(e['clock'] for e in ev if e['generation']==g and e['event']=='call673' and e['name']=='nes_plan200_end')) for g in (956,957)}
        c=rows['686'];b=rows['685'];f=folders['686'];ev=read(f/'events.json')
        c['BG_window_comparison']=[dict(slot=x['slot'],response=x['last_ROM_response'],base_response=y['last_ROM_response'],
            window=rom_window(x['last_ROM_response']),base_window=rom_window(y['last_ROM_response']))
            for x,y in zip(c['details'][956]['BG'],b['details'][956]['BG'],strict=True)]
        c['first_BG_window_maintained']=all(v['window']<=v['base_window'] for v in c['BG_window_comparison'])
        c['BG_complete']={}
        for g in (951,952,954,955,956,957):
            e=[v for v in ev if v['generation']==g]
            complete=[v for v in e if v['event']=='bg684_return' and v['begin']['final']]
            assert len(complete)<=1,(phase,g,complete)
            obj=[v for v in e if v['event']=='call673' and v['name']=='nes_plan200_emit' and bytes.fromhex(v['plan'])[6]==1]
            for v in complete:
                assert v['passed'] and v['map_sha']==v['begin']['map_sha'] and v['last_map_write']<=v['begin']['clock']
                assert not obj or v['clock']<=obj[0]['clock']
                calls=[q for q in e if q['event']=='call673' and q['name']=='packet_wire' and v['begin']['clock']<=q['clock']<=v['clock']]
                assert all(q['section']==2 for q in calls)
                c['BG_complete'][g]=dict(callback=v,packets=calls,first_OBJ=obj[0]['clock'] if obj else None,
                    advance_before_planner_end_ms=ms(next(q['clock'] for q in e if q['event']=='immutable673')-v['clock']))
        c['map_order']={}
        for g in (956,957):
            packets=c['details'][g]['packets']
            i=next(i for i,p in enumerate(packets) if p['section']==2 and p['offset']==1024)
            seq=[{k:p[k] for k in ('op','section','offset','expanded_B','load','ack')} for p in packets[i:i+3]]
            c['map_order'][g]=seq
        c['continuous_map']=all(v[0]['section']==v[1]['section']==2 and v[0]['offset']==1024 and v[1]['offset']==1216 for v in c['map_order'].values())
        c['moved_before_OBJ']=all(g in c['BG_complete'] and any(p['offset']==1216 for p in c['BG_complete'][g]['packets']) for g in (956,957))
        c['request_gate']=c['timing_gate'] and c['receive956']['checked_blocks_before_ACK']==7 and c['first_BG_window_maintained'] and c['continuous_map'] and c['moved_before_OBJ']
        c['delta685']=dict(last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),dense_ms=c['dense_mean_ms']-b['dense_mean_ms'],frames={})
        c['final957_vs_MMC666']={}
        waits={}
        for tag in ('MMC666','686'):
            seals=[r for r in csv_groups(folders[tag]/'window.csv')[957] if r['op']==3]
            wait,=[r for r in seals if r['event'].startswith('wait_return_')]
            waits[tag]=wait['clock']
            dma=rows[tag]['details'][957]['final_DMA']
            c['final957_vs_MMC666'][tag]=dict(wait_return=wait,final_DMA_B=sum(d['value'] for d in dma),
                final_DMA_count=len(dma),final_DMA_sizes=[d['value'] for d in dma],
                post_wait_to_ACK_clocks=rows[tag]['last_ACK']-wait['clock'])
        delta_wait=waits['686']-waits['MMC666']
        delta_after=(c['last_ACK']-waits['686'])-(rows['MMC666']['last_ACK']-waits['MMC666'])
        assert delta_wait+delta_after==c['last_ACK']-rows['MMC666']['last_ACK']
        c['final957_vs_MMC666']['partition']=dict(wait_return_delta_clocks=delta_wait,
            post_wait_delta_clocks=delta_after,last_ACK_delta_clocks=delta_wait+delta_after,
            explanation='Measured return from the existing VBlank wait, followed by complete DMA/display/ACK. No invented delay or unobserved polling-branch attribution.')
        for g in (956,957):
            cd,bd=c['details'][g],b['details'][g]
            c['delta685']['frames'][g]=dict(previous_reveal_ms=ms(cd['previous_reveal']-bd['previous_reveal']),
                own_interval_ms=c['intervals'][g]['ms']-b['intervals'][g]['ms'],
                SEAL_accept_ms=ms(cd['marks']['load']['clock']-bd['marks']['load']['clock']),
                early_map_B=cd['early_DMA_B']['map']-bd['early_DMA_B']['map'])
        phases[phase]=rows
        budget=[{k:int(v) for k,v in r.items()} for r in csv.DictReader((f/'budget685.csv').open())]
        assert budget
        for r in budget:
            allowed=r['range'] if r['line']<=248 and r['range']<=1536 else min(r['range'],1152)
            assert r['bytes']==allowed and 225<=r['line']<=252 and 0<r['clock']-r['latch_clock']<3*1364
        c['actual_beam_budget']=budget
        dma_edges=[]
        for g,records in csv_groups(f/'window.csv').items():
            if g<905:continue  # boot upload under forced blank is not idle map DMA
            starts=[r for r in records if r['event']=='ppu_dma' and r['op']==-1]
            ends=[r for r in records if r['event']=='ppu_last' and r['op']==-1]
            for start,end in zip(starts,ends,strict=True):
                assert start['clock']<end['clock'] and start['frame']==end['frame'] and 225<=start['line']<=end['line']<262
                dma_edges.append(dict(generation=g,start=start,end=end))
        c['actual_DMA_edges']=dma_edges
        c['completed957_1536']=any(r['generation']==957 and r['bytes']==r['range']==1536 for r in budget)
        c['request_gate']=c['request_gate'] and c['completed957_1536']
        r=c['receive956'];rows955=[v for v in ev if v['generation']==955]
        seal=next(v for v in rows955 if v['event']=='SPI' and v.get('packet_opcode')==3)
        queries=[v for v in rows955 if v['event']=='SPI' and v.get('opcode')=='0xe0' and seal['clock']<=v['start']<r['rows'][0]['begin']]
        c['receive955_boundary']=dict(SEAL_SPI_start=seal['start'],SEAL_SPI_end=seal['clock'],
            first_poll=r['rows'][0]['begin'],checked7_return=r['rows'][6]['returned'],previous_ACK=r['previous_ACK'],
            post_SEAL_to_first_poll_ms=ms(r['rows'][0]['begin']-seal['clock']),
            checked7_duration_ms=ms(r['rows'][6]['returned']-r['rows'][0]['begin']),
            required_advance_ms=max(0,ms(r['rows'][6]['returned']-r['previous_ACK'])),
            E0_queries=[{k:v[k] for k in ('start','clock','bytes','reply')} for v in queries],
            ownership='Successful SEAL send invokes reason3 before first E0. Actual CRC/POP then unchanged E0 full identity, no premature COMMIT/EA.')
        c['sealed_input_boundaries']=[]
        for g in range(905,958):
            events=[v for v in ev if v['generation']==g]
            seal,=[v for v in events if v['event']=='SPI' and v.get('packet_opcode')==3]
            query=next(v for v in events if v['event']=='SPI' and v.get('opcode')=='0xe0' and v['start']>=seal['clock'])
            owner,=[v for v in events if v['event']=='input682_enter' and v['reason']==3 and seal['clock']<=v['clock']<query['start']]
            pending=[v for v in events if v['event']=='SPI' and seal['clock']<=v['start']<query['start']]
            assert all(v['opcode'] not in ('0xd3','0xea','0xe1') for v in pending)
            reads=[v for v in pending if v['opcode']=='0xd1'];assert len(reads)<=7
            c['sealed_input_boundaries'].append(dict(generation=g,SEAL_end=seal['clock'],owner=owner['clock'],
                first_E0=query['start'],read_count=len(reads),output_status_deferral_ms=ms(query['start']-seal['clock'])))
        c['max_observed_output_status_deferral_ms']=max(v['output_status_deferral_ms'] for v in c['sealed_input_boundaries'])
        c['map955_boundary']={}
        for tag in ('685','686'):
            d=rows[tag]['details'][955]
            packet,=[v for v in d['packets'] if v['section']==2 and v['offset']==3392]
            ack,=[v for v in csv_groups(folders[tag]/'window.csv')[955] if v['event']=='ack' and v['clock']==packet['ack']]
            beams=[{k:int(v) for k,v in row.items()} for row in csv.DictReader((folders[tag]/'budget685.csv').open()) if row['generation']=='955']
            c['map955_boundary'][tag]=dict(last_map=packet,acceptance_ACK=ack,beam_grants=beams,
                early_map_B=d['early_DMA_B']['map'],final_DMA_B=sum(v['value'] for v in d['final_DMA']),
                reveal=d['marks']['reveal'],display_ACK=d['marks']['ack'])
        b955,n955=c['map955_boundary']['685'],c['map955_boundary']['686']
        c['map955_boundary']['delta']=dict(last_map_ACK_ms=ms(n955['last_map']['ack']-b955['last_map']['ack']),
            final_DMA_B=n955['final_DMA_B']-b955['final_DMA_B'],
            reveal_ms=ms(n955['reveal']['clock']-b955['reveal']['clock']),
            interpretation='Observed missed safe beam grant; do not extend252 DMA admission or246 display validation. Restore previous actual acceptance deadline before claiming a later grant.')
    base=Path('../probes/nes-complete685/arm01/src');old=read(Path('analysis/complete685-sealed-verification.json'))
    assert sha(base/'obj-nes-100/firmware.stm')==old['firmware']
    assert sha(a.client/'sink165.sfc')==old['client']
    changed=sorted(p.name for p in (a.arm/'src').glob('*') if p.suffix in ('.c','.h') and (base/p.name).exists() and p.read_bytes()!=(base/p.name).read_bytes())
    assert changed==['nes_native_runtime165.c','nes_sink_window184.c']
    guards={p.name:dict(SHA256=sha(p),result=read(p)) for p in a.arm.parent.glob('*guards*.json')}
    for v in guards.values():assert v['result']['firmware']==firmware
    assert image.stat().st_size<=212992
    report=dict(stage=686,phases=phases,firmware=firmware,Flash_B=image.stat().st_size,Flash_free_B=212992-image.stat().st_size,
        data_B=10040,BSS_B=19544,client=sha(a.client/'sink165.sfc'),client_budget=read(a.client/'build.json'),
        base_evidence_SHA256=sha(Path('analysis/complete685-sealed-verification.json')),guards=guards,
        inherited_CPU_guards=old['CPU_guards'],request_gate=all(r['686']['request_gate'] for r in phases.values()),
        new_RTL=False,new_CPU=False,new_FIT=False,new_STA=False,selected_physical='MMC666',new_static_RAM_B=0,
        source_changes=changed,source_diff=''.join(''.join(difflib.unified_diff((base/n).read_text().splitlines(True),(a.arm/'src'/n).read_text().splitlines(True),fromfile='685/'+n,tofile='686/'+n)) for n in changed),
        source_pins={p.name:sha(p) for p in Path('tools').glob('*686*.py')},
        replay_script=(a.arm.parent/'replay.ps1').read_text(encoding='utf-8-sig'),
        preserved_failures=['analysis01 used old reason2-only batch classification and rejected the new reason3 owner. Corrected classification only; raw runs/CPU/clock/bytes unchanged.'],
        scope='Actual linked686 M4 and unchanged685 65816, same workload/pixels. Modeled SPI/IRQ/repeated ROM calendar, no physical FPS/full NES PSRAM cosimulation.')
    a.out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    keys=('protected','dense_delta_MMC666_ms','last_ACK_delta_MMC666_ms','first_BG_window_maintained','checked_input_margin_ms','continuous_map','completed957_1536','request_gate','regressions','new_final_waits','receive955_boundary')
    print(json.dumps({p:{k:v for k,v in r['686'].items() if k in keys} for p,r in phases.items()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','arm','client','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
