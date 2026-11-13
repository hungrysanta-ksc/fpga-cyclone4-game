"""Compare relative packet clocks and absolute last ACK on the same two calendars."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_tail735 import Calendar, audit, csv_groups, map_image, ms, one, packets, read, report, resources, section5, sha, tile_image


def timeline(folder, row):
    d=row['details'][957]
    origin=d['previous_reveal']
    ev=[e for e in read(folder/'events.json') if e['generation']==957]
    heads=d['packets']
    obj=next(p for p in reversed(heads) if (p['op'],p['section'])==(7,1))
    table=next(p for p in heads if p['section']==5 and p['offset']==1505)
    pad=next(p for p in heads if p['section']==5 and p['offset']==21)
    scroll=next(p for p in heads if p['section']==5 and p['offset']==0)
    first_map=next(p for p in heads if p['section']==2 and p['offset']==2048)
    oam=next(p for p in heads if p['section']==4)
    immutable=one(ev,'immutable673')['clock']
    last_response=read(folder/'obj-phases.json')['957']['last_obj_rom_response']
    queries=[]
    for e in ev:
        if e.get('opcode')!='0xe8':
            continue
        reply=bytes.fromhex(e['reply'])
        if reply[6:8]==bytes([1,1]) and int.from_bytes(reply[8:10],'little')==obj['expanded_B'] and int.from_bytes(reply[10:12],'little')==obj['offset']:
            queries.append(e['clock'])
    assert last_response<=min(queries)<=obj['start']
    transaction,=[e for e in ev if e.get('opcode')=='0xe1' and abs(e['clock']-table['push'])<=1]
    assert transaction['bytes']==259 and transaction['start']==table['start']
    competing=[e for e in ev if e['event']=='SPI' and e['start']<transaction['clock'] and e['clock']>transaction['start']]
    assert len(competing)==1
    stamps=dict(immutable=immutable,OBJ_last_source_response=last_response,OBJ_descriptor_seen=min(queries),
                OBJ_start=obj['start'],OBJ_load=obj['load'],OBJ_ACK=obj['ack'],
                scroll_start=scroll['start'],scroll_ACK=scroll['ack'],pad_start=pad['start'],pad_ACK=pad['ack'],
                table_start=table['start'],table_push=table['push'],table_ACK=table['ack'],first_long_map=first_map['start'],
                OAM_start=oam['start'],SEAL_load=d['marks']['load']['clock'],reveal=d['marks']['reveal']['clock'])
    cpu=csv_groups(folder/'window.csv')[957]
    obj_row=next(r for r in cpu if r['event']=='ack' and r['clock']==obj['ack'])
    seal_row=one([r for r in cpu if r['op']==3],'load')
    seal_events=[r for r in cpu if r['op']==3]
    upload=one(seal_events,'upload165_entry')
    target_frame=one(seal_events,'reveal')['frame']-1
    anchor=min((r for r in cpu if r['frame']==target_frame), key=lambda r:abs(r['line']-247))
    # Horizontal position is not logged. Bound line 247 using this frame,
    # allowing one short scanline in addition to a full scanline of uncertainty.
    projected=anchor['clock'] + (247-anchor['line'])*1364
    budget=[ms(upload['clock']-t) for t in (projected+4,projected-1364-4)]
    return dict(checked_upload_after_previous_line246_ms=budget,
                OBJ_frame_line=[obj_row['frame'],obj_row['line']],SEAL_frame_line=[seal_row['frame'],seal_row['line']],clocks=stamps,origin=origin,relative_ms={k:ms(t-origin) for k,t in stamps.items()},
                table_continuous_ms=ms(transaction['clock']-transaction['start']),table_wire_B=transaction['bytes'],
                OBJ_ready_to_ACK_ms=ms(obj['ack']-last_response),post_OBJ_ms=ms(stamps['SEAL_load']-obj['ack']))


def compare(temp,probe,tag,phase):
    return compare_paths(temp, probe, tag, phase, temp/f'nes-prefix736-{tag}{phase}',
                         probe/('arm05' if tag=='a' else 'arm06')/'src')


def compare_paths(temp,probe,tag,phase,candidate_path,firmware):
    base_path=temp/f'nes-pair727-a{phase}'
    ref=temp/f'nes-front638-both{phase}h'
    calendar=Calendar(temp/'nes-service509-rom03')
    base,new=[report(f,ref,calendar) for f in (base_path,candidate_path)]
    baseline=read(Path(__file__).resolve().parents[1]/'analysis/idle734-verification.json')['phases'][str(phase)]['rows']['base']
    assert base['pins']==baseline['pins']
    paths=(base_path,candidate_path)
    b,c=[read(p/'joint.json') for p in paths]
    assert c['parameters']==b['parameters'] and c['client_SHA256']==b['client_SHA256']
    for f,j in [(probe.parent/'nes-pair727/arm01/src',b),(firmware,c)]:
        assert j['firmware_SHA256']==sha(f/'obj-nes-100/firmware.stm') and j['passed'] and j['commits']==53
    def work(p):
        plans=[(e['generation'],e['plan']) for e in read(p/'events.json') if e.get('name')=='nes_plan200_emit' and e['event']=='call673']
        colors=[(g,h[:2],h[10:]) for g,heads in packets(p).items() for h,_,_ in heads if h[1] in (3,4)]
        return map_image(p),tile_image(p),section5(p),plans,colors
    assert work(base_path)==work(candidate_path), (tag,phase,'expanded payload, plans or palette/OAM differ')
    pixels={f.name:sha(f) for f in candidate_path.glob('frame-*.rgb')}
    assert len(pixels)==53 and all(sha(base_path/n)==v for n,v in pixels.items())
    base_t,new_t=[timeline(p,r) for p,r in zip(paths,(base,new))]
    relative={k:t-base_t['relative_ms'][k] for k,t in new_t['relative_ms'].items()}
    # Identify bus users that occupied the candidate table slot in the
    # reference, aligned to the preceding display in each run.
    tb=new_t['clocks']
    align=base_t['origin']-new_t['origin']
    lo,hi=tb['table_start']+align,tb['table_push']+align
    occupied=Counter()
    for e in read(base_path/'events.json'):
        if e['event']=='SPI':
            overlap=max(0,min(hi,e['clock'])-max(lo,e['start']))
            if overlap:
                occupied[e['opcode']]+=ms(overlap)
    cpu0,cpu1=[csv_groups(p/'window.csv') for p in paths]
    def interval(cpu,g):
        def frame(g):
            return one([r for r in cpu[g] if r['op']==3],'reveal')['frame']
        return frame(g)-frame(g-1)
    checks=new['protected'].copy()
    checks['previous_gains']=all(interval(cpu1,g)<=interval(cpu0,g) for g in (908,911,934,940,943,951))
    audit_rows=audit(candidate_path)['frames']
    runs={g:audit_rows[g]['prefix_map_DMA'] for g in (952,956,957)}
    checks['long_map_DMA']=all(any(d['offset']==2048 and d['bytes']==1536 for d in runs[g]) for g in (952,957))
    base_audit=audit(base_path)['frames']
    map_deadlines={}
    for g in (952,957):
        reference=next(d['clock'] for d in base_audit[g]['prefix_map_DMA'] if d['offset']==2048 and d['bytes']==1536)
        def last_row(row):
            return next(p['ack'] for p in row['details'][g]['packets'] if p['section']==2 and p['offset']==3392)
        opportunity=reference+new['details'][g]['previous_reveal']-base['details'][g]['previous_reveal']
        map_deadlines[g]=dict(reference_last_ACK_margin_ms=ms(reference-last_row(base)),
                              candidate_last_ACK_margin_ms=ms(opportunity-last_row(new)))
    early=new['details'][956]['early_DMA']
    checks['early956']=all(early[k]>=base['details'][956]['early_DMA'][k] for k in ('map','tile'))
    d956=new['details'][956]['packets']
    ack=next(p['ack'] for p in d956 if p['section']==2 and p['offset']==3264)
    obj=next((p['load'] for p in d956 if p['section']==1 and p['load']>ack),None)
    checks['last384_before_OBJ']=obj is not None and any(d['offset']==3072 and d['bytes']==384 and ack<d['clock'] and
        next(r['clock'] for r in cpu1[956] if r['event']=='ppu_last' and r['clock']>d['clock'])<obj for d in runs[956])
    bg={g:[r['details'][g]['current_ROM_window_close'] for r in (base,new)] for g in range(952,958)}
    checks['BG_windows']=all((b is None and c is None) or (b is not None and c is not None and c<=b) for b,c in bg.values())
    delta=dict(mean952_957_ms=new['after951_mean_ms']-base['after951_mean_ms'],dense951_955_ms=new['dense_ms']-base['dense_ms'],
               last_ACK_ms=ms(new['last_ACK']-base['last_ACK']),VBlank=new['after951_VBlank']-base['after951_VBlank'])
    activated=[]
    for g,heads in packets(candidate_path).items():
        sections=[h[1] for h,_,_ in heads]
        if 2 in sections and 5 in sections and sections.index(5)<max(i for i,s in enumerate(sections) if s==2):
            activated.append(g)
    candidate_offset = ms(new_t['origin'] - base_t['origin'])
    commit_delta = ms(new['last_ACK'] - base['last_ACK'])
    delta['prior_display_shift_ms'] = candidate_offset
    delta['from_previous_display_to_ACK_ms'] = commit_delta - candidate_offset
    earlier=all(relative[k]<0 for k in ('OBJ_ACK','scroll_ACK','pad_ACK','table_start'))
    return dict(changed_intervals={g:[interval(cpu0,g),interval(cpu1,g)] for g in range(906,958) if interval(cpu0,g)!=interval(cpu1,g)},
                prefix_before_last_map_generations=activated,base=base_t,candidate=new_t,relative_delta_ms=relative,baseline_SPI_during_table_slot_ms=occupied,
                delta=delta,protected=checks,earlier_957=earlier,prefix_DMA=runs,early956=early,map_deadlines=map_deadlines,BG_windows=bg,
                absolute_ACK=[base['last_ACK'],new['last_ACK']],baseline_pins=base['pins'],
                wire_B=[base['wire_B'],new['wire_B']],instructions=[base['ARM_instructions'],new['ARM_instructions']],intervals=new['intervals'],pins=new['pins'],pixels=pixels,
                passed=all(checks.values()) and earlier and delta['VBlank']<=0 and all(delta[k]<0 for k in ('mean952_957_ms','dense951_955_ms','last_ACK_ms')))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for n in ('temp','probe','out'):
        parser.add_argument(n,type=Path)
    args=parser.parse_args()
    builds={p.name:resources(p/'src') for p in args.probe.iterdir() if (p/'size.log').is_file()}
    trials={}
    for tag,n in [('a','05'),('b','06')]:
        assert builds['normal'+n]['Flash_B']<=212992 and builds['arm'+n]['Flash_B']<=212992
        trials[tag]={ph:compare(args.temp,args.probe,tag,ph) for ph in (1,2)}
    guards={}
    history=read(Path(__file__).resolve().parents[1]/'analysis/idle734-verification.json')['resources']['builds']
    for tag,n in [('a','05'),('b','06')]:
        for kind,edition in [('normal','normal'),('arm','long')]:
            current=builds[kind+n]
            assert all(current[k]==history['727_'+edition][k] for k in ('sections','structs'))
        for name in ('order','deadline02','credit03','gate03','menu03','normal-menu03','normal-admission02',
                     'normal-runtime02','ownership03','runtime03','padding','cursor','span-oam'):
            f=args.probe/(name+'-'+tag+'.json')
            guard=read(f)
            assert guard.get('passed',True)
            guards[f.stem]=sha(f)
        for prefix,gen in [('stop',907),('warm-stop',948)]:
            f=args.temp/f'nes-prefix736-{prefix}-{tag}/result.json'
            cases=read(f)
            assert len(cases)==2 and all(r['status']==228 and r['generation']==gen and r['commits']==gen-905 for r in cases)
            if gen==948:
                assert gen in trials[tag][1]['prefix_before_last_map_generations']
            guards[prefix+'-'+tag]=cases
    result=dict(guards=guards,stage=736,builds=builds,trials=trials,new_CPU_frames=212,physical_FPS=False,new_RTL=False,new_65816=False,
                selected=[tag for tag,phases in trials.items() if all(r['passed'] for r in phases.values())])
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
