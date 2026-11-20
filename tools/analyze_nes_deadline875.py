"""Reconcile the capture edge, checked SEAL and actual DMA with complete scene replays."""
import argparse
import json
from pathlib import Path

from analyze_nes_map830 import load, packets, window
from analyze_nes_transition850 import STRIDE
from check_nes_scroll874 import receipt
from check_nes_strip869 import digest, metrics
from check_nes_game478 import crc

PERIOD=262*341*4


def points(folder):
    spi=load(folder/'events.json')
    trace=window(folder)
    source=next(e for e in spi if e['event']=='source_begin' and e['generation']==952)
    preceding_source=next(e for e in spi if e['event']=='source_begin' and e['generation']==951)
    pop=next(e for e in reversed(spi) if e.get('opcode')=='0xd2' and e['input_generation']==951)
    ready=source['capture_ready']
    lost_edge=ready-240*341*4-PERIOD
    assert 0<=pop['clock']-lost_edge<PERIOD
    prior=next(e['clock'] for e in trace if e['g']==951 and e['event']=='ack' and e['op']==3)
    seal_index=next(e['index'] for e in trace if e['g']==951 and e['event']=='load' and e['op']==3)
    seal_tx=round([e for e in spi if e.get('opcode')=='0xe1'][seal_index-1]['clock'])
    rows=[e for e in trace if e['g']==952]
    def first(kind):
        return next(e for e in rows if e['event']==kind and (kind!='load' or e['op']==3))
    return dict(capture_ready=ready,capture_begin=round(source['clock']),
                previous_display_ACK=prior,previous_SEAL_SPI_end=seal_tx,
                input951_ready_to_begin=round(preceding_source['clock']-preceding_source['capture_ready']),
                potential_overlap_with_one_earlier_capture=max(0,prior-max(ready-PERIOD,seal_tx)),
                planner=round(next(e['clock'] for e in spi if e['event']=='planner_enter' and e['generation']==952)),
                input951_commit_pop=round(pop['clock']),previous_capture_edge=lost_edge,
                clocks_past_edge=round(pop['clock']-lost_edge),
                SEAL=first('load'),upload=first('upload165_entry'),show=first('reveal'),
                gap=first('reveal')['frame']-next(e['frame'] for e in trace if e['g']==951 and e['event']=='reveal'),
                DMA=[[e['frame'],e['line'],e['value']] for e in rows if e['event']=='ppu_dma'])


def arm_ack(folder,published):
    packet_list=packets(folder)
    head=packet_list[-1]
    assert head[0]==3
    expected=bytes((1,3))+head[2:10]+bytes.fromhex('659a')
    for e in load(folder/'events.json'):
        if e.get('opcode')!='0xe0' or e['clock']<published:
            continue
        b=bytes.fromhex(e['reply'])
        if b[2]&2 and b[7:19]==expected:
            assert b[1]==0xf7 and b[19]==crc(b[1:19],8,7,0)
            assert int.from_bytes(b[3:5],'big')==int.from_bytes(b[5:7],'big')==len(packet_list)
            return round(e['clock'])
    raise ValueError(f'no matching ARM receipt in {folder}')


def consumer(temp):
    rows={}
    for f in sorted(temp.glob('nes-deadline875-consumer-*/summary.json')):
        d=load(f)
        key=f.parent.name.removeprefix('nes-deadline875-consumer-')
        rows[key]=dict(advance=d['advance_clocks'],seal_advance=d.get('seal_advance_clocks',d['advance_clocks']),
                       SEAL=d['seal'],show=d['show'],ACK=d['ack'],DMA=d['dma'],
                       marks=[m for m in d['marks'] if m[0] in
                              ('seal','validate181','covered619','upload165_entry','wait169','final_credit')])
    for ph in (1,2):
        a,b=rows[f'p{ph}-lines0'],rows[f'p{ph}-lines48']
        assert a['show']['frame']-b['show']['frame']==1 and b['show']['line']<=246
    return rows


def analyze(temp,root,work,tag):
    fw=work/'link-credit/src/obj-nes-100/firmware.stm'
    arm,client=digest(fw),digest(work/'client02/sink165.sfc')
    info=dict(ARM=arm,client=client,flash_B=fw.stat().st_size,scenes={},gates={})
    gates=info['gates']
    gates['flash']=info['flash_B']<=212992
    for clip in ('opening','transition','demo'):
        for ph in (1,2):
            key=f'{clip}-{ph}'
            prefix=f'nes-tile821-{clip}-jointmirror-p{ph}-'
            ref,parent,new=[temp/(prefix+t) for t in ('872-final','874-drain',tag)]
            old,actual=load(ref/'joint.json'),load(new/'joint.json')
            assert old['passed'] and actual['passed'] and old['frames'] and actual['commits']==old['commits']
            assert old['parameters']==actual['parameters'] and actual['client_SHA256']==old['client_SHA256']==client
            assert actual['firmware_SHA256']==arm
            for fr in old['frames']:
                g=fr['generation']
                a,b=[(path/f'frame-{g}.rgb').read_bytes() for path in (ref,new)]
                assert len(a)==len(b) and a[7*STRIDE:231*STRIDE]==b[7*STRIDE:231*STRIDE]
                assert (ref/f'map-{g}.bin').read_bytes()==(new/f'map-{g}.bin').read_bytes()
            metrics3=[metrics(path) for path in (ref,parent,new)]
            assert len({m['warm_map_wire_B'] for m in metrics3})==1
            row={k:[m[k] for m in metrics3] for k in ('pictures','after_two_VBlanks','last_ACK','warm_map_wire_B','opening_marks','held_blank_VBlanks')}
            info['scenes'][key]=row
            gaps=row['after_two_VBlanks']
            if clip=='demo':
                assert load(ref/'ack861.json')['loads']==load(new/'ack861.json')['loads']
                row['target952']=[points(path) for path in (ref,parent,new)]
                row['ARM_final_E0']=[arm_ack(path,clk) for path,clk in zip((ref,parent,new),row['last_ACK'])]
                target=receipt(new,950)
                row['target950']=target
                gates[key+'_950']=bool(target['consecutive'] and target['matching_credit'] and target['gap']==3 and any(
                    frame==target['show']-1 and target['map_return'][2]<=clock<target['seal'][2]
                    for frame,line,clock in target['map_DMA1088']))
                a,b,c=row['target952']
                gates[key+'_952']=c['show']['frame']<b['show']['frame'] and c['show']['line']<=246 and c['gap']<=2
                gates[key+'_window']=(gaps[2]<gaps[0] and row['last_ACK'][2]<row['last_ACK'][0]
                                      and row['ARM_final_E0'][2]<row['ARM_final_E0'][0])
            else:
                gates[key+'_intervals']=gaps[2]<=gaps[0]
                if clip=='transition' and row['held_blank_VBlanks'][0] is not None:
                    gates[key+'_blank']=row['held_blank_VBlanks'][2]==row['held_blank_VBlanks'][0]
                if clip=='opening':
                    a,_,c=row['opening_marks']
                    gates[key+'_deadlines']=c['910']<=a['910'] and c['966'][0]<=a['966'][0]
    for name in ('begin','input-guards','scrollguard','menu869'):
        info[name]=load(work/(name+'.json'))
    assert info['input-guards']['firmware']==info['menu869']['firmware']==arm
    assert info['menu869']['rows']['normal']['released']
    info['guards']=load(work/'guards.json') if (work/'guards.json').exists() else load(root/'probes/nes-scroll874/guards.json')
    assert info['guards']['client']==client
    if (work/'raster-guards.json').exists():
        info['raster']=load(work/'raster-guards.json')
        assert info['raster']['ARM'][1]==arm
    info['passed']=all(gates.values())
    return info


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('variants',nargs='+',help='work directory suffix:replay tag')
    a=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    report=dict(order=['MMC872','874-both-pages','candidate'],consumer=consumer(a.temp),variants={})
    for pair in a.variants:
        name,tag=pair.split(':')
        report['variants'][name]=analyze(a.temp,root,root/f'probes/nes-deadline875-{name}',tag)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
