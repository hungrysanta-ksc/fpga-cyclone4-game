"""Align idle DMA bytes, progress stores, SPI status snapshots and scroll acceptance."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from analyze_nes_deadline875 import analyze,points
from analyze_nes_map830 import load,packets,window
from check_nes_game478 import crc
from check_nes_raster879 import matched_output,summary
from check_nes_retire878 import trace,verify_retire_order
from check_nes_scroll874 import receipt
from check_nes_strip869 import digest


def observation(folder):
    gen=950
    rec=receipt(folder,gen)
    log=window(folder)
    tx=[e for e in load(folder/'events.json') if e['event']=='SPI']
    returns=[e for e in log if e['g']==gen and e['section']==2 and e['event']=='ack']
    head=returns[-1]['index']
    last=packets(folder)[head-1]
    expected=bytes([0,last[0]])+last[2:10]+bytes.fromhex('659a')
    scroll=next(e for e in log if e['index']==head+1 and e['event']=='load')
    assert scroll['g']==gen and scroll['section']==5
    with (folder/'progress680.csv').open() as f:
        notices=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(f)]
    polls=[e for e in tx if e.get('opcode')=='0xe0' and
           rec['map_E1_end']<=e['start']<rec['scroll_E1_start']]
    hits=[]
    for e in polls:
        b=bytes.fromhex(e['reply'])
        assert b[1]==0xf7 and crc(b[1:19],8,7,0)==b[19]
        if b[2]&8:
            assert b[2]==10 and int.from_bytes(b[3:5],'big')==int.from_bytes(b[5:7],'big')==head and b[7:19]==expected
            stores=[n for n in notices if n['retired']==n['sent']==head and n['clock']+3<=e['clock']]
            assert stores, (folder,e)
            hits.append(dict(start=round(e['start']),end=round(e['clock']),store=stores[-1]['clock']))
    dma=[]
    for i,e in enumerate(log):
        if e['g']!=gen or e['event']!='ppu_dma' or e['op']!=-1:continue
        end=next(m for m in log[i+1:] if m['event'] in ('ppu_last','ppu_dma'))
        assert end['event']=='ppu_last' and end['g']==gen
        notice=next((n for n in notices if end['clock']<=n['clock']<end['clock']+1600),None)
        dma.append(dict(bytes=e['value'],begin=e['clock'],last_byte=end['clock'],frame=e['frame'],
                        lines=[e['line'],end['line']],progress_store=notice))
    bus=[e for e in tx if e.get('opcode') and rec['map_E1_end']<=e['start']<rec['scroll_E1_start']]
    first_credit=rec['matching_credit'][0]
    scroll_tx=next(e for e in tx if e.get('opcode')=='0xe1' and round(e['start'])==rec['scroll_E1_start'])
    return dict(map=rec,map_packet=head,scroll_load=scroll,scroll_SPI_end=round(scroll_tx['clock']),
                map_first_return=returns[0],map_last_return=returns[-1],idle_DMA=dma,
                first_progress=hits[0] if hits else None,
                E0_after_map_return=sum(round(e['start'])>=rec['map_return'][2] for e in polls),
                E0_after_credit=sum(round(e['start'])>=first_credit for e in polls),
                post_credit_SPI_B=sum(e['bytes'] for e in bus if round(e['start'])>=first_credit),
                post_credit_SPI_clocks=round(sum(e['clock']-e['start'] for e in bus if round(e['start'])>=first_credit)),
                credit_to_scroll=rec['scroll_E1_start']-first_credit)


def report(temp):
    root=Path(__file__).resolve().parents[2]
    work=root/'probes/nes-mapwait880-shared'
    result=analyze(temp,root,work,'880-progress')
    end_work=root/'probes/nes-mapwait880-end'
    combined=analyze(temp,root,end_work,'880-end')
    for run, directory, tag in ((result,work,'880-progress'),(combined,end_work,'880-end')):
        assert run['guards']['source_tag']==tag
        run['blocks951']=load(directory/'blocks951.json')
        run['retire_guards']=load(directory/'retire-guards.json')
        assert run['retire_guards']['ARM']==run['ARM']
        for clip in ('opening','transition','demo'):
            for ph in (1,2):
                folder=temp/f'nes-tile821-{clip}-jointmirror-p{ph}-{tag}'
                run['scenes'][f'{clip}-{ph}']['released']=verify_retire_order(folder)
    result['RTL']=load(temp/'nes-mapwait880-rtl/result.json')
    assert result['RTL']['passed']
    for name,sha in result['RTL']['pins'].items():
        if name.endswith('_tb.sv'):continue
        assert digest(temp/'nes-trial816-board872'/name)==sha
    result['phases']={}
    for ph in (1,2):
        def folder(tag):
            return temp/f'nes-tile821-demo-jointmirror-p{ph}-{tag}'
        edge=points(folder('874-drain'))['previous_capture_edge']
        row={}
        for tag in ('878-once','879-static','880-credit','880-progress','880-end'):
            d=folder(tag)
            timeline=trace(d,edge)
            row[tag]=dict(timeline=summary(timeline),observation=observation(d),
                          capture951_ready=timeline['capture951_ready'],first951_D1_end=timeline['first_D1_end'])
            if tag.startswith('880'):
                joint=load(d/'joint.json')
                assert joint['firmware_SHA256']==(combined if tag=='880-end' else result)['ARM']
                row[tag]['releases']=matched_output(folder('879-static'),d)
        row['consumer']={k:load(temp/f'nes-mapwait880-consumer-{ph}-{v}/summary.json')
                         for k,v in [('control',0),('held',1)]}
        def wire(tag):
            return [e for e in load(folder(tag)/'events.json') if e['event']=='SPI']
        base,bounded=[wire(tag) for tag in ('880-credit','880-progress')]
        first=next((i for i,(a,b) in enumerate(zip(base,bounded)) if a!=b),None)
        row['paired_comparison']={
            'first_different_transaction':first,
            'at_first_difference':None if first is None else [base[first],bounded[first]],
            'E0_count':[sum(e['opcode']=='0xe0' for e in data) for data in (base,bounded)],
            'SPI_bytes':[sum(e['bytes'] for e in data) for data in (base,bounded)]}
        visible=[{e['g']:e['frame'] for e in window(folder(tag)) if e['event']=='reveal'}
                 for tag in ('880-credit','880-progress')]
        previous=None
        transitions={}
        for g,frame in visible[1].items():
            offset=frame-visible[0][g]
            if previous!=offset:transitions[g]=offset
            previous=offset
        row['paired_comparison']['display_lead_changes']=transitions
        result['phases'][ph]=row
        for run,tag in ((result,'880-progress'),(combined,'880-end')):
            run['gates'][f'demo-{ph}_950_clock']=(row[tag]['timeline']['show950']['clock']
                <=row['878-once']['timeline']['show950']['clock'])
            run['gates'][f'demo-{ph}_capture']=row[tag]['timeline']['commit_minus_874_edge']<0
            def audit(which):
                parent=temp/f'nes-mapwait880-consumer-{ph}-{which}'
                assert load(parent/'summary.json')['final_ACK']['clock']==row[which]['observation']['map']['ACK']
                with (parent/'idle-vram.csv').open() as f:
                    return [tuple(map(int,r)) for r in csv.reader(f)]
            origin=audit('878-once')
            current=audit(tag)
            assert len(origin)==1472 and all(b[0]==origin[0][0]+i and
                b[1]==origin[0][1]+i and b[2]==0x2118+(i%2) for i,b in enumerate(origin))
            # Include source address, configured VRAM destination, actual PPU port and byte.
            # Retain the historical exact-length gate separately from equivalent coverage.
            covered=current[:len(origin)]==origin
            observation_row=row[tag]['observation']
            row[tag]['WRAM_to_VRAM']=dict(prefix_matches=covered,source=origin[0][0],destination=origin[0][1],
                reference_bytes=len(origin),actual_idle_bytes=len(current),
                data_sha256=hashlib.sha256(bytes(r[3] for r in origin)).hexdigest())
            run['gates'][f'demo-{ph}_same_map_range']=covered and any(d['bytes'] in (1088,1472)
                and d['frame']==observation_row['map']['show']-1 for d in observation_row['idle_DMA'])
        for clip in ('opening','transition'):
            def path(tag):
                return temp/f'nes-tile821-{clip}-jointmirror-p{ph}-{tag}'
            control, bounded=path('880-credit'),path('880-progress')
            base=[e for e in load(control/'events.json') if e['event']=='SPI']
            new=[e for e in load(bounded/'events.json') if e['event']=='SPI']
            first=next(((i,a['generation'],b['generation']) for i,(a,b) in enumerate(zip(base,new)) if a!=b),None)
            reveals=lambda f:[(e['g'],e['frame'],e['line']) for e in window(f) if e['event']=='reveal']
            pair=[reveals(control),reveals(bounded)]
            assert len(pair[0])==len(pair[1]) and load(control/'joint.json')['passed']
            row.setdefault('paired_scenes',{})[clip]=dict(first_SPI_difference=first,
                 SPI_count=[len(base),len(new)],same_reveals=pair[0]==pair[1],
                 intervals=[r[-1][1]-r[1][1] for r in pair])
            diagnostic=(906 if ph==1 else 909) if clip=='opening' else 941
            row['paired_scenes'][clip]['generation']=diagnostic
            for tag in ('872-final','880-credit','880-progress','880-end'):
                row['paired_scenes'][clip][tag]=[
                    [e['event'],e['clock'],e['frame'],e['line']] for e in window(path(tag))
                    if e['g']==diagnostic and e['op']==3 and e['event'] in ('load','upload165_entry','reveal')]
        for clip,g in (('transition',941),('demo',950)):
            d=temp/f'nes-tile821-{clip}-jointmirror-p{ph}-880-progress'
            rec=receipt(d,g)
            first_credit=rec['matching_credit'][0]
            status=[e for e in load(d/'events.json') if e.get('opcode')=='0xe0' and e['generation']==g]
            inside=[e for e in status if first_credit<=round(e['start'])<rec['scroll_E1_start']]
            events=window(d)
            row.setdefault('wait_inputs',{})[g]=dict(
                map_wire=[[b[0],int.from_bytes(b[10:12],'little'),int.from_bytes(b[12:14],'little')]
                    for b in packets(d) if b[1]==2 and int.from_bytes(b[8:10],'little')==g],
                completed_before_credit=[e['value'] for i,e in enumerate(events)
                    if e['g']==g and e['event']=='ppu_dma' and e['op']==-1 and
                    next(x for x in events[i+1:] if x['event']=='ppu_last')['clock']<first_credit],
                progress_seen_before_credit=sum(e['clock']<first_credit and bool(bytes.fromhex(e['reply'])[2]&8)
                                                for e in status),
                E0_after_credit=len(inside),last_flags=bytes.fromhex(inside[-1]['reply'])[2] if inside else None,
                credit_to_scroll=rec['scroll_E1_start']-first_credit)
    for run,tag in ((result,'880-progress'),(combined,'880-end')):
        run['passed']=all(run['gates'].values())
        equivalent=dict(run['gates'])
        for ph,data in result['phases'].items():
            obs=data[tag]['observation']
            equivalent[f'demo-{ph}_950']=(equivalent[f'demo-{ph}_same_map_range'] and
                obs['map']['consecutive'] and bool(obs['map']['matching_credit']) and obs['map']['gap']==3 and
                obs['first_progress'] is not None)
        run['failed_with_equivalent_coverage']=[k for k,ok in equivalent.items() if not ok]
    result['post_END_96us']=combined
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(report(a.temp),indent=2)+'\n')
