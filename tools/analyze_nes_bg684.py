"""Same-work two-phase map pair, input credit, BG window and final ACK gates."""
import argparse,difflib,json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import read,sha,ms,csv_groups,one
from analyze_nes_receive682 import receive_batch,blocks956
from analyze_nes_bg674 import preparation,tile_image
from analyze_nes_frontier536 import contents
from analyze_nes_progress680 import grants

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
        folders={k:a.traces/v for k,v in [('MMC666',f'nes-ready673-b{phase}'),('682',f'nes-receive682-read{phase}'),('683',f'nes-pair683-handoff{phase}'),('684',f'nes-bg684-arm{phase}')]}
        traces={k:trace(f,a.traces/f'nes-front638-both{phase}h') for k,f in folders.items()}
        js={k:read(f/'joint.json') for k,f in folders.items()};base=traces['MMC666'];old=traces['682'];rows={}
        oldplan=read(folders['682']/'obj-phases.json')
        for k,f in folders.items():
            c=traces[k];j=js[k]
            assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2
            assert j['parameters']==js['MMC666']['parameters']
            assert tile_image(f)==tile_image(folders['MMC666']) and contents(f)[1]==contents(folders['MMC666'])[1]
            assert {g:v['work'] for g,v in c['frames'].items()}=={g:v['work'] for g,v in base['frames'].items()}
            if k=='684':
                assert j['firmware_SHA256']==firmware and j['client_SHA256']==js['682']['client_SHA256']
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
        c=rows['684'];b=rows['683'];f=folders['684'];ev=read(f/'events.json')
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
        c['delta683']=dict(last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),dense_ms=c['dense_mean_ms']-b['dense_mean_ms'],frames={})
        c['final957_vs_MMC666']={}
        waits={}
        for tag in ('MMC666','684'):
            seals=[r for r in csv_groups(folders[tag]/'window.csv')[957] if r['op']==3]
            wait,=[r for r in seals if r['event'].startswith('wait_return_')]
            waits[tag]=wait['clock']
            dma=rows[tag]['details'][957]['final_DMA']
            c['final957_vs_MMC666'][tag]=dict(wait_return=wait,final_DMA_B=sum(d['value'] for d in dma),
                final_DMA_count=len(dma),final_DMA_sizes=[d['value'] for d in dma],
                post_wait_to_ACK_clocks=rows[tag]['last_ACK']-wait['clock'])
        delta_wait=waits['684']-waits['MMC666']
        delta_after=(c['last_ACK']-waits['684'])-(rows['MMC666']['last_ACK']-waits['MMC666'])
        assert delta_wait+delta_after==c['last_ACK']-rows['MMC666']['last_ACK']
        c['final957_vs_MMC666']['partition']=dict(wait_return_delta_clocks=delta_wait,
            post_wait_delta_clocks=delta_after,last_ACK_delta_clocks=delta_wait+delta_after,
            explanation='Measured return from the existing VBlank wait, followed by complete DMA/display/ACK. No invented delay or unobserved polling-branch attribution.')
        for g in (956,957):
            cd,bd=c['details'][g],b['details'][g]
            c['delta683']['frames'][g]=dict(previous_reveal_ms=ms(cd['previous_reveal']-bd['previous_reveal']),
                own_interval_ms=c['intervals'][g]['ms']-b['intervals'][g]['ms'],
                SEAL_accept_ms=ms(cd['marks']['load']['clock']-bd['marks']['load']['clock']),
                early_map_B=cd['early_DMA_B']['map']-bd['early_DMA_B']['map'])
        phases[phase]=rows
    base=a.base/'src';changed=[]
    for p in (a.arm/'src').glob('*'):
        if p.suffix in ('.c','.h') and (base/p.name).exists() and p.read_bytes()!=(base/p.name).read_bytes():changed.append(p.name)
    assert sorted(changed)==['nes_native_runtime165.c','nes_native_sink165.c','nes_native_sink165.h','nes_planner211.c','nes_resident211.h']
    n=image.stat().st_size;assert n<=212992
    result=dict(stage=684,phases=phases,firmware=firmware,Flash_B=n,Flash_free_B=212992-n,data_B=10040,BSS_B=19544,
        source_changes=changed,base_firmware=sha(base/'obj-nes-100/firmware.stm'),client=js['684']['client_SHA256'],
        source_diff=''.join(''.join(difflib.unified_diff((base/n).read_text().splitlines(True),(a.arm/'src'/n).read_text().splitlines(True),fromfile='683/'+n,tofile='684/'+n)) for n in sorted(changed)),
        guards={p.name:dict(SHA256=sha(p),result=read(p)) for p in a.arm.parent.glob('*guards*.json')},
        request_gate=all(p['684']['request_gate'] for p in phases.values()),new_RTL=False,new_CPU=False,new_FIT=False,new_STA=False,
        selected_physical='MMC666',unchanged_681_evidence=sha(Path('analysis/late681-verification.json')),
        source_pins={p.name:sha(p) for p in Path('tools').glob('*684.py')},
        replay_script=(a.arm.parent/'replay.ps1').read_text(encoding='utf-8-sig'),
        raw_build_pins={n:sha(a.arm/n) for n in ('build.log','size.log','recipe684.json')},
        over_budget_first_build=dict(Flash_B=(a.arm.parent/'arm01/src/obj-nes-100/firmware.stm').stat().st_size,reason='Duplicate range calculation in runtime; shared existing sink helper in arm02. No arm01 replay.'),
        scope='Linked ARM and actual 65816, modeled SPI/IRQ and repeated ROM calendar; exact same bytes/pixels. Not live full-board NES/PSRAM or measured physical FPS.')
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    keys=('protected','dense_delta_MMC666_ms','last_ACK_delta_MMC666_ms','first_BG_window_maintained','checked_input_margin_ms','continuous_map','moved_before_OBJ','request_gate','regressions','new_final_waits')
    print(json.dumps({p:{k:v for k,v in r['684'].items() if k in keys} for p,r in phases.items()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','arm','base','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
