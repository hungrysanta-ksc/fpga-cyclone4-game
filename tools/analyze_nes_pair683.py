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
        folders={k:a.traces/v for k,v in [('MMC666',f'nes-ready673-b{phase}'),('682',f'nes-receive682-read{phase}'),('683',f'nes-pair683-{a.tag}{phase}')]}
        traces={k:trace(f,a.traces/f'nes-front638-both{phase}h') for k,f in folders.items()}
        js={k:read(f/'joint.json') for k,f in folders.items()};base=traces['MMC666'];old=traces['682'];rows={}
        oldplan=read(folders['682']/'obj-phases.json')
        for k,f in folders.items():
            c=traces[k];j=js[k]
            assert j['passed'] and j['commits']==53 and j['max_bulk_banks']<=2
            assert j['parameters']==js['MMC666']['parameters']
            assert tile_image(f)==tile_image(folders['MMC666']) and contents(f)[1]==contents(folders['MMC666'])[1]
            assert {g:v['work'] for g,v in c['frames'].items()}=={g:v['work'] for g,v in base['frames'].items()}
            if k=='683':
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
        c=rows['683'];b=rows['682']
        # Use the actual eight boot-window identities, not the phase of the
        # ARM start or a condition requiring an identical response clock.
        c['BG_window_comparison']=[dict(slot=x['slot'],response=x['last_ROM_response'],base_response=y['last_ROM_response'],
            window=rom_window(x['last_ROM_response']),base_window=rom_window(y['last_ROM_response']))
            for x,y in zip(c['details'][956]['BG'],b['details'][956]['BG'],strict=True)]
        c['first_BG_window_maintained']=all(v['window']<=v['base_window'] for v in c['BG_window_comparison'])
        c['merge384']={g:any(v['offset']==1024 and v['bytes']==384 for v in c['details'][g]['grants']) for g in (956,957)}
        c['merge384_scope']='Actual EARLY DMA at map offset1024. False does not mean absence of a merged descriptor or later384B DMA; final_DMA lists the later transfers without claiming unlogged source addresses.'
        c['final_DMA384_observed']={g:any(v['value']==384 for v in c['details'][g]['final_DMA']) for g in (956,957)}
        c['request_gate']=c['timing_gate'] and c['receive956']['checked_blocks_before_ACK']==7 and c['first_BG_window_maintained'] and all(c['merge384'].values())
        c['coupled_cost_vs682']=dict(last_ACK_delta_ms=ms(c['last_ACK']-b['last_ACK']),frames={})
        for g in (956,957):
            cd,bd=c['details'][g],b['details'][g];blocked=[]
            for grant in bd['grants']:
                if grant['offset'] is None or grant['bytes']<192:continue
                t=grant['clock']
                active=[{**{k:p[k] for k in ('op','section','offset','expanded_B','load','load_line','ack')},
                         'ACK_later_than_old_grant_ms':ms(p['ack']-t)} for p in cd['packets'] if p['load']<=t<p['ack']]
                blocked.append(dict(old_grant=grant,new_active_consumption=active))
            c['coupled_cost_vs682']['frames'][g]=dict(
                previous_reveal_delta_ms=ms(cd['previous_reveal']-bd['previous_reveal']),
                own_interval_delta_ms=c['intervals'][g]['ms']-b['intervals'][g]['ms'],
                SEAL_accept_delta_ms=ms(cd['marks']['load']['clock']-bd['marks']['load']['clock']),
                early_map_delta_B=cd['early_DMA_B']['map']-bd['early_DMA_B']['map'],
                old_DMA_opportunity_comparison=blocked)
        phases[phase]=rows
    changed=[];base=a.base/'src'
    for p in (a.arm/'src').glob('*'):
        if p.suffix in ('.c','.h') and (base/p.name).exists() and p.read_bytes()!=(base/p.name).read_bytes():changed.append(p.name)
    assert sorted(changed)==(['nes_native_sink165.c','nes_native_sink165.h'] if a.tag=='handoff' else ['nes_native_sink165.c']),changed
    n=image.stat().st_size;assert n<=212992
    result=dict(stage=683,phases=phases,firmware=firmware,Flash_B=n,Flash_free_B=212992-n,
        data_B=10040,BSS_B=19544,source_changes=changed,map527_stack_B=56,base_map527_stack_B=64,
        receive_poll_stack_B=560,wait634_stack_B=40,
        source_diff=''.join(''.join(difflib.unified_diff((base/n).read_text().splitlines(True),
            (a.arm/'src'/n).read_text().splitlines(True),fromfile='682/'+n,tofile='683/'+n)) for n in sorted(changed)),
        base_firmware=sha(base/'obj-nes-100/firmware.stm'),client=js['683']['client_SHA256'],
        guards={p.name:dict(SHA256=sha(p),result=read(p)) for p in a.arm.parent.glob('*guards*.json') if read(p).get('firmware')==firmware},
        request_gate=all(p['683']['request_gate'] for p in phases.values()),new_RTL=False,new_CPU=False,new_FIT=False,new_STA=False,
        selected_physical='MMC666',unchanged_681_evidence=sha(Path('analysis/late681-verification.json')),
        source_pins={p.name:sha(p) for p in Path('tools').glob('*683.py')},
        replay_script=(a.arm.parent/('replay-'+a.tag+'.ps1' if a.tag in ('end','handoff') else 'replay.ps1')).read_text(encoding='utf-8-sig'),
        raw_build_pins={n:sha(a.arm/n) for n in ('build.log','size.log','recipe683.json')},
        initial_guard_failure='guards01 expected full ACK identity checking inside credit(); existing contract checks it in drain/through. Corrected test at actual boundary, target unchanged; raw failure preserved.',
        scope='Linked ARM and actual 65816, modeled SPI/IRQ and repeated ROM calendar; exact same bytes/pixels. Not live full-board NES/PSRAM or measured physical FPS.')
    if a.tag in ('end','handoff'):
        old=read(a.arm.parent/'arm01-verification.json')
        result['first_candidate']=dict(verification_SHA256=sha(a.arm.parent/'arm01-verification.json'),firmware=old['firmware'],
            reason='Local final-output loop cannot pair a map emitted by the earlier BG planner callback. Phase2 also regressed952; normal-output pairing removed.',
            phases={p:{k:v for k,v in r['683'].items() if k in ('protected','dense_delta_MMC666_ms','last_ACK_delta_MMC666_ms','merge384','checked_input_margin_ms','first_BG_window_maintained','request_gate')} for p,r in old['phases'].items()})
        unused=a.arm.parent/'arm02/src/obj-nes-100/firmware.stm'
        result['unrun_intermediate']=dict(firmware=sha(unused),Flash_B=unused.stat().st_size,reason='Built before the first replay phase2 result; normal-output pairing retained. Replaced by END-only arm03 before any replay; no success claim.')
    if a.tag=='handoff':
        old=read(a.arm.parent/'end-verification.json')
        result['END_only_candidate']=dict(verification_SHA256=sha(a.arm.parent/'end-verification.json'),firmware=old['firmware'],
            reason='END-only pairing did not reach the target map. Existing call trace proves first192 is in BG planner before immutable/END; second192 in final output. Preserve three-final-row offer, carry an exact one-shot boundary instead.',
            phases={p:{k:v for k,v in r['683'].items() if k in ('protected','dense_delta_MMC666_ms','last_ACK_delta_MMC666_ms','merge384','checked_input_margin_ms','first_BG_window_maintained','request_gate')} for p,r in old['phases'].items()})
        result['sink_layout']=dict(size_B=988,prior_size_B=988,one_byte_at=34,prior_padding=[34,35],ack635_offset_unchanged=36,source='Linked ELF DWARF; guards use actual offsets.')
        result['diagnosis_scope']='At identical masterclocks where682 granted early DMA, identify actual683 packet load..ACK occupancy. Empty intervals do not prove eligibility or the next selector branch. No synthetic delay/phase sweep or unseen-attempt inference.'
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({p:{k:v for k,v in r['683'].items() if k in ('protected','dense_delta_MMC666_ms','last_ACK_delta_MMC666_ms','merge384','first_BG_window_maintained','checked_input_margin_ms','request_gate','regressions','new_final_waits')} for p,r in phases.items()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('traces','arm','base','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--tag',default='arm');run(p.parse_args())
