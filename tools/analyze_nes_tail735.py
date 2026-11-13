"""Measure both lanes on the same clock. Intersect nested spans before summing."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_accept726 import audit, map_image, report, tile_image
from analyze_nes_fence714 import Calendar
from analyze_nes_output615 import csv_groups, ms, one, packets, read, sha
from analyze_nes_rows713 import resources


def tail(folder):
    rows = csv_groups(folder/'window.csv')[957]
    ev = [e for e in read(folder/'events.json') if e['generation']==957]
    obj = [r for r in rows if r['event']=='ack' and (r['op'],r['section'])==(7,1)][-1]
    seal = [r for r in rows if r['op']==3]
    lo, hi = obj['clock'], one(seal,'load')['clock']
    seal_push = packets(folder)[957][-1][2]
    bands = []

    def add(label, start, end, priority):
        left, right = max(lo,start), min(hi,end)
        if left<right:
            bands.append((left,right,priority,label))

    add('queue_after_SEAL_push',seal_push,hi,0)
    for e in ev:
        if e['event']=='SPI':
            add('SPI_'+e['opcode'],e['start'],e['clock'],1)
        elif e['event']=='input682_return':
            add('input_callback_off_bus',e['begin']['clock'],e['clock'],2)
        elif e['event']=='return673':
            name = e['name']
            if name in ('nes_window184_through','nes_plan200_progress','nes_window184_enqueue',
                        'nes_window184_barrier','packet_wire'):
                priority = {'nes_window184_through':3,'nes_window184_enqueue':4,'nes_window184_barrier':4,
                            'nes_plan200_progress':5,'packet_wire':6}[name]
                add(name+'_off_bus',e['start'],e['clock'],priority)
    ticks = Counter()
    host_intervals = []
    edges = sorted({lo,hi}|{v for l,r,_,_ in bands for v in (l,r)})
    for a,b in zip(edges,edges[1:]):
        _, label = min(((p,n) for l,r,p,n in bands if l<=a and b<=r),
                       default=(9,'caller_preparation_off_bus'))
        ticks[label] += b-a
        host_intervals.append((a,b,label))
    assert abs(sum(ticks.values())-(hi-lo))<1e-4
    ordinary = []
    queue_empty = Counter()
    dispatch = 0
    prior = lo
    loads = [r for r in rows if r['event']=='load']
    for header,_,push in packets(folder)[957]:
        i = int.from_bytes(header[2:4],'little')
        # Receiver index is global. Packet sequence starts at zero for every generation.
        idx = loads[i]['index']
        cpu = [r for r in rows if r['index']==idx]
        load,ack = one(cpu,'load'),one(cpu,'ack')
        if load['clock']<=lo:
            continue
        assert prior<=load['clock']<=hi and push<=load['clock']
        # The receiver has finished the previous head. Only the positive
        # overlap before this push exposes host latency on its serial lane.
        for left,right,label in host_intervals:
            queue_empty[label]+=max(0,min(push,right)-max(prior,left))
        dispatch+=load['clock']-max(prior,push)
        prior=ack['clock']
        if load['clock']==hi:
            break
        row = dict(op=header[0],section=header[1],offset=int.from_bytes(header[10:12],'little'),
                   load=load['clock'],ack=ack['clock'],service_ms=ms(ack['clock']-load['clock']))
        chunks = [r['clock'] for r in cpu if r['event']=='zero_chunk516']
        if chunks:
            row.update(header_and_setup_ms=ms(chunks[0]-load['clock']),
                       fill_loop_ms=ms(chunks[-1]-chunks[0]),receipt_and_exit_ms=ms(ack['clock']-chunks[-1]),
                       DMA_chunks=sum(r['event']=='zero_dma' for r in cpu))
        ordinary.append(row)
    checks = {}
    names = ('load','seal','validate181','coverage212','upload165_entry')
    for a,b in zip(names,names[1:]):
        checks[a+'_to_'+b] = ms(one(seal,b)['clock']-one(seal,a)['clock'])
    immutable = one(ev,'immutable673')
    cursor = immutable['clock']
    gaps = []
    for e in sorted((e for e in ev if e['event']=='SPI' and e['start']<lo and e['clock']>cursor),
                    key=lambda e:e['start']):
        if e['start']>cursor:
            gaps.append(e['start']-cursor)
        cursor=max(cursor,min(lo,e['clock']))
    if cursor<lo:
        gaps.append(lo-cursor)
    opportunity=dict(immutable_to_OBJ_ACK_ms=ms(lo-immutable['clock']),unused_SPI_ms=ms(sum(gaps)),
                     largest_idle_SPI_ms=ms(max(gaps,default=0)),idle_intervals=len(gaps),
                     field_last_writes_ms_before_OBJ={k:ms(lo-v['last_write']) for k,v in immutable['fields'].items()})
    post = ms(hi-lo)
    empty_ms={k:ms(v) for k,v in queue_empty.items() if v}
    ordinary_ms=sum(r['service_ms'] for r in ordinary)
    assert abs(post-(sum(empty_ms.values())+ms(dispatch)+ordinary_ms))<1e-7
    return dict(empty_queue_exposed_host_ms=empty_ms,ready_head_dispatch_ms=ms(dispatch),
                before_OBJ=opportunity,post_OBJ_ms=post,elapsed_ms={k:ms(v) for k,v in ticks.items()},last_OBJ_ACK=obj,
                SEAL_load=one(seal,'load'),SEAL_push=seal_push,ordinary=ordinary,
                parallel_ordinary_service_ms=sum(r['service_ms'] for r in ordinary),
                SEAL_checks_after_load_ms=checks,credit_updates=[{k:e[k] for k in ('clock','before','after','sent')}
                    for e in ev if e['event']=='credit673' and lo<=e['clock']<=hi],
                # Bracket horizontal position using the observed OBJ ACK scanline.
                # This boundary is necessary, even allowing zero remaining DMA and checks.
                OBJ_after_end_of_line246_ms=[ms((obj['line']-k)*1364) for k in (247,246)],
                SEAL_after_end_of_line246_ms=[post+ms((obj['line']-k)*1364) for k in (247,246)])


def section5(folder):
    frames = {}
    for g, commands in packets(folder).items():
        body = bytearray()
        for h,_,_ in commands:
            if h[1]!=5:
                continue
            assert int.from_bytes(h[10:12],'little')==len(body)
            length=int.from_bytes(h[14:16],'little')
            assert h[0] in (2,4,5)
            body.extend(h[16:]*(length//2) if length else h[16:])
        frames[g]=bytes(body)
    return frames


def run(temp, probe, after_obj=False):
    stem="nes-tail735-b" if after_obj else "nes-tail735-a"
    suffix="02" if after_obj else "01"
    builds={}
    for label, parent in [('727',probe.parent/'nes-pair727'),('735',probe)]:
        for name in ('normal01','arm01'):
            builds[label+name]=resources(parent/(name[:-2]+suffix if label=='735' else name)/'src')
    cal=Calendar(temp/'nes-service509-rom03')
    history=read(Path(__file__).resolve().parents[1]/'analysis/idle734-verification.json')
    phases={}
    for phase in (1,2):
        ref=temp/f'nes-front638-both{phase}h'
        old,new=[temp/(stem+str(phase)) for stem in ('nes-pair727-a',stem)]
        base,cand=[report(p,ref,cal) for p in (old,new)]
        assert base['pins']==history['phases'][str(phase)]['rows']['base']['pins']
        control_folder=temp/f'nes-idle734-b{phase}'
        control_pins=history['phases'][str(phase)]['rows']['candidate']['pins']
        assert all(sha(control_folder/k)==v for k,v in control_pins.items())
        bj,cj=[read(p/'joint.json') for p in (old,new)]
        assert cj['firmware_SHA256']==builds['735arm01']['firmware']
        assert bj['firmware_SHA256']==builds['727arm01']['firmware']
        assert cj['parameters']==bj['parameters'] and cj['client_SHA256']==bj['client_SHA256']
        assert section5(old)==section5(new) and map_image(old)==map_image(new) and tile_image(old)==tile_image(new)
        def plans(p):
            return [(e['generation'],e['plan']) for e in read(p/'events.json')
                    if e['event']=='call673' and e['name']=='nes_plan200_emit']
        assert plans(old)==plans(new)
        pixels={p.name:sha(p) for p in new.glob('frame-*.rgb')}
        assert len(pixels)==53 and all(sha(old/n)==v for n,v in pixels.items())
        before,after=[csv_groups(p/'window.csv') for p in (old,new)]
        def reveal(cpu,g):
            return one([r for r in cpu[g] if r['op']==3],'reveal')['frame']
        protect=cand['protected'].copy()
        protect['prior_intervals']=all(reveal(after,g)-reveal(after,g-1)<=reveal(before,g)-reveal(before,g-1)
                                       for g in (908,911,934,940,943,951))
        a=audit(new)['frames']
        protect['1536B']=all(any(d['offset']==2048 and d['bytes']==1536 for d in a[g]['prefix_map_DMA']) for g in (952,957))
        early=cand['details'][956]['early_DMA']
        protect['956_early_vs727']=all(early[k]>=base['details'][956]['early_DMA'][k] for k in ('map','tile'))
        protect['956_tile128_vs734B']=early['tile']>=128
        last_map=next(p for p in cand['details'][956]['packets'] if p['offset']==3264 and p['section']==2)
        next_obj=min(p['load'] for p in cand['details'][956]['packets'] if p['section']==1 and p['load']>last_map['ack'])
        dma=[d for d in a[956]['prefix_map_DMA'] if d['bytes']==384 and d['offset']==3072]
        protect['956_last384_before_OBJ']=any(
            last_map['ack']<d['clock']<next(r['clock'] for r in after[956] if r['event']=='ppu_last' and r['clock']>d['clock'])<next_obj
            for d in dma)
        bg={g:[row['details'][g]['current_ROM_window_close'] for row in (base,cand)] for g in range(952,958)}
        protect['BG_windows']=all((b is None and c is None) or (b is not None and c is not None and c<=b)
                                  for b,c in bg.values())
        delta=dict(mean952_957_ms=cand['after951_mean_ms']-base['after951_mean_ms'],
                   dense951_955_ms=cand['dense_ms']-base['dense_ms'],last_ACK_ms=ms(cand['last_ACK']-base['last_ACK']),
                   VBlank=cand['after951_VBlank']-base['after951_VBlank'])
        phases[phase]=dict(base=tail(old),control734B=tail(control_folder),candidate=tail(new),
                           delta=delta,protected=protect,BG_windows=bg,map_prefix={g:a[g]['prefix_map_DMA'] for g in (952,956,957)},
                           early956=early,intervals=cand['intervals'],base_intervals=base['intervals'],
                           wire_B=[base['wire_B'],cand['wire_B']],instructions=[base['ARM_instructions'],cand['ARM_instructions']],
                           ACK=[base['last_ACK'],cand['last_ACK']],pins=cand['pins'],baseline_pins=base['pins'],pixels=pixels,
                           passed=all(protect.values()) and delta['VBlank']<=0 and all(delta[k]<0 for k in ('dense951_955_ms','mean952_957_ms','last_ACK_ms')))
    guards={}
    for name in ('ranges','short-padding','credit03-b','deadline02-b','gate03-b','menu03-b','normal-menu03-b',
                 'normal-admission02-b','normal-runtime02-b','ownership03-b','runtime03-b','stop06/result'):
        rootname=name.replace('-b','-obj') if after_obj else name
        if after_obj and name in ('ranges','short-padding','stop06/result'):
            rootname={'ranges':'ranges-obj-final','short-padding':'short-padding-obj','stop06/result':'stop-obj/result'}[name]
        file=probe/(rootname+'.json')
        g=read(file)
        if isinstance(g,dict):
            assert g.get('passed',True)
        guards[name]=dict(SHA256=sha(file),result=g if name=='stop06/result' else None)
    storage=history['resources']['builds']
    flash={}
    for kind,edition in (('normal01','normal'),('arm01','long')):
        b,c=builds['727'+kind],builds['735'+kind]
        assert c['Flash_B']<=212992 and c['sections']==b['sections'] and c['structs']==b['structs']
        previous=storage['733_'+edition]['Flash_B']
        flash[edition]=dict(vs727_B=c['Flash_B']-b['Flash_B'],vs733_B=c['Flash_B']-previous,
                            free_B=212992-c['Flash_B'],at_or_below_733=c['Flash_B']<=previous)
    return dict(Flash=flash,stage=735,after_obj=after_obj,phases=phases,builds=builds,guards=guards,timing_pass=all(p['passed'] for p in phases.values()),
                frames=106,new_RTL=False,new_65816=False,new_FIT_STA=False,physical_FPS=False,
                scope='Linked M4/65816, independent receiver and pixel oracle; CPI2, SPI/IRQ and periodic ROM contention modeled.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('temp','probe','out'):
        p.add_argument(n,type=Path)
    p.add_argument('--after-obj',action='store_true')
    p.add_argument('--control',type=Path,help='completed unrestricted 735 replay')
    a=p.parse_args()
    result=run(a.temp,a.probe,a.after_obj)
    if a.control:
        control=read(a.control)
        assert a.after_obj and control['stage']==735 and not control['after_obj']
        result=dict(stage=735,variants={'A':control,'B':result},new_CPU_frames=212,
                    timing_pass=control['timing_pass'] or result['timing_pass'])
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
