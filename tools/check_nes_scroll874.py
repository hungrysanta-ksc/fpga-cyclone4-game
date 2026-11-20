"""Join the last map's physical retirement, returned E0 identity, scroll E1 and actual DMA."""
import argparse
import json
from pathlib import Path

from analyze_nes_map830 import load, packets, window
from analyze_nes_word873 import stages
from analyze_nes_transition850 import STRIDE
from check_nes_strip869 import digest, metrics
from check_nes_game478 import crc


def receipt(folder, g):
    w = window(folder)
    data = packets(folder)
    events = load(folder/'events.json')
    spi = [e for e in events if e.get('event')=='SPI']
    issue = [e for e in spi if e.get('opcode')=='0xe1']
    assert len(issue)==len(data)
    selected = [(i,b) for i,b in enumerate(data,1) if int.from_bytes(b[8:10],'little')==g]
    mi,mb = next((i,b) for i,b in reversed(selected) if b[1]==2)
    si,sb = next((i,b) for i,b in selected if b[1]==5 and int.from_bytes(b[10:12],'little')==0)
    assert sb[12:14]==bytes((21,0))
    returned = next(e for e in w if e['index']==mi and e['event']=='ack')
    tx,scroll=issue[mi-1],issue[si-1]
    probes = [e for e in spi if e.get('opcode')=='0xe0' and
              tx['clock']<=e['start'] and e['clock']<=scroll['start']]
    hits=[]
    for e in probes:
        r=bytes.fromhex(e['reply'])
        assert r[1]==0xf7 and r[19]==crc(r[1:19],8,7,0)
        if r[2]&2 and int.from_bytes(r[3:5],'big')==int.from_bytes(r[5:7],'big')==mi:
            assert r[7:19]==bytes((0,mb[0]))+mb[2:10]+bytes.fromhex('659a')
            hits.append(round(e['clock']))
    rows=[e for e in w if e['g']==g]
    show=next(e for e in rows if e['event']=='reveal')
    prior=next(e for e in w if e['g']==g-1 and e['event']=='reveal')
    seal=next(e for e in rows if e['event']=='load' and e['op']==3)
    dma=[(e['frame'],e['line'],e['clock']) for e in rows if e['event']=='ppu_dma' and e['value']==1088]
    ack=next(e for e in rows if e['event']=='ack' and e['op']==3)
    return dict(map_return=[returned[k] for k in ('frame','line','clock')], consecutive=si==mi+1, E0_count=len(probes),
                E0_wire_B=sum(e['bytes'] for e in probes),
                E0_SPI_clocks=round(sum(e['clock']-e['start'] for e in probes)),
                map_E1_end=round(tx['clock']), matching_credit=hits, scroll_E1_start=round(scroll['start']),
                map_return_to_scroll_clocks=round(scroll['start']-returned['clock']),
                map_DMA1088=dma, DMA=[[e['frame'],e['line'],e['value']] for e in rows if e['event']=='ppu_dma'],
                seal=[seal[k] for k in ('frame','line','clock')],
                previous=prior['frame'],show=show['frame'],line=show['line'],
                gap=show['frame']-prior['frame'], ACK=ack['clock'])


def compare(temp,work,tag):
    fw=digest(work/'link-credit/src/obj-nes-100/firmware.stm')
    client=digest(work/'client02/sink165.sfc')
    result=dict(ARM=fw,client=client,flash_B=(work/'link-credit/src/obj-nes-100/firmware.stm').stat().st_size,
                target=950,scenes={},gate={})
    for clip in ('demo','opening','transition'):
        for ph in (1,2):
            name=f'{clip}-{ph}'
            prefix=f'nes-tile821-{clip}-jointmirror-p{ph}-'
            ref,new=[temp/(prefix+t) for t in ('872-final',tag)]
            old,cur=metrics(ref),metrics(new)
            r,n=load(ref/'joint.json'),load(new/'joint.json')
            assert n['firmware_SHA256']==fw and n['client_SHA256']==r['client_SHA256']==client
            assert n['parameters']==r['parameters'] and old['pictures']==cur['pictures']
            assert old['warm_map_wire_B']==cur['warm_map_wire_B']
            for fr in r['frames']:
                g=fr['generation']
                rgb=f'frame-{g}.rgb'
                a,b=(ref/rgb).read_bytes(),(new/rgb).read_bytes()
                assert len(a)==len(b) and a[7*STRIDE:231*STRIDE]==b[7*STRIDE:231*STRIDE],(clip,ph,g)
                assert (ref/f'map-{g}.bin').read_bytes()==(new/f'map-{g}.bin').read_bytes()
            row=dict(reference=old,candidate=cur,ACK_delta=cur['last_ACK']-old['last_ACK'])
            for path,summary in ((ref,old),(new,cur)):
                e0=[e for e in load(path/'events.json') if e.get('opcode')=='0xe0']
                summary['all_E0_count']=len(e0)
                summary['all_E0_wire_B']=sum(e['bytes'] for e in e0)
                summary['all_E0_SPI_clocks']=round(sum(e['clock']-e['start'] for e in e0))
            gate=result['gate']
            if clip=='demo':
                assert load(ref/'ack861.json')['loads']==load(new/'ack861.json')['loads']
                base,target=[receipt(path,950) for path in (ref,new)]
                row.update(before950=base,after950=target)
                gate[name+'_credit']=bool(target['consecutive'] and target['matching_credit']
                                          and target['map_return_to_scroll_clocks']>0)
                gate[name+'_dma_and_show']=(target['gap']==3 and any(
                    f==target['show']-1 and target['map_return'][2]<=c<target['seal'][2]
                    for f,l,c in target['map_DMA1088']))
                gate[name+'_window']=cur['after_two_VBlanks']<old['after_two_VBlanks'] and row['ACK_delta']<0
                for path,label in ((ref,'reference'),(new,'candidate')):
                    trace=window(path)
                    pubs=[e for e in trace if e['event']=='reveal' and e['g'] in (935,936)]
                    row[label+'_936_gap']=pubs[-1]['frame']-pubs[0]['frame']
                    packet_list=packets(path)
                    ready={e['generation']:e['capture_ready'] for e in load(path/'events.json') if e['event']=='source_begin'}
                    row[label+'_later']={}
                    for g in (951,952,966):
                        marks=stages(path,g,trace,packet_list)
                        row[label+'_later'][g]=dict(capture_ready=ready[g],**marks)
                gate[name+'_936']=row['candidate_936_gap']<=2
            else:
                gate[name+'_intervals']=cur['after_two_VBlanks']<=old['after_two_VBlanks']
                if clip=='opening':
                    gate[name+'_deadlines']=(cur['opening_marks']['910']<=old['opening_marks']['910']
                                             and cur['opening_marks']['966'][0]<=old['opening_marks']['966'][0])
            result['scenes'][name]=row
    result['gate']['flash']=result['flash_B']<=212992
    for key in ('begin','input-guards','menu869','scrollguard','guards'):
        result[key]=load(work/(key+'.json'))
    assert result['menu869']['firmware']==result['input-guards']['firmware']==fw
    assert result['menu869']['rows']['normal']['released'] and result['guards']['client']==client
    result['pass']=all(result['gate'].values())
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('work',type=Path)
    p.add_argument('tag')
    p.add_argument('out',type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(compare(a.temp,a.work,a.tag),indent=2)+'\n')
