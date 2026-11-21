"""Match actual section-5 packets, OBJ readiness, pre-SEAL DMA and visible deadlines."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from analyze_nes_tail908 import linked_run
from nes_section909 import BASE, WORK, AFTER_PALETTE, sha
from test_nes_raw506_joint import MASTER


def read_csv(directory,name):
    with (directory/name).open() as stream:
        return list(csv.DictReader(stream))


def measure(directory,work):
    firmware=work/'link/src/obj-nes-100/firmware.stm'
    result=linked_run(directory,sha(firmware))
    packets=[json.loads(s) for s in (directory/'packets.jsonl').read_text().splitlines()]
    spi=[e for e in json.loads((directory/'events.json').read_bytes()) if e.get('opcode')=='0xe1']
    returns=dict(json.loads((directory/'returns904.json').read_bytes()))
    window=read_csv(directory,'window.csv')
    loads=[r for r in window if r['event']=='load']
    assert len(packets)==len(loads)==len(spi)
    body={}
    for packet,event,load in zip(packets,spi,loads):
        _,end,hexdata,_=packet
        data=bytes.fromhex(hexdata)
        g=int.from_bytes(data[8:10],'little')
        assert g==int(load['g'])==event['generation'] and data[0]==int(load['op'])==event['packet_opcode']
        assert abs(event['clock']-end)<1
        # Sequence is assigned by emission order. Preserve the complete section
        # payload, opcode, generation, offsets and the remainder of the header.
        body.setdefault(g,[]).append(data[:2]+data[4:])
        if g not in result['frames']:continue
        if data[:2]==b'\x07\x01':
            token=int.from_bytes(data[16:20],'little')
            result['frames'][g]['last_OBJ_return']=returns[token]
        if data[0] in (2,4,5,8) and data[1] in (3,4):
            label='palette' if data[1]==3 else 'OAM'
            result['frames'][g].setdefault('last_accept',{})[label]=int(load['clock'])
        if data[:2]!=b'\x02\x05':continue
        n=int.from_bytes(data[12:14],'little')
        if n in (201,240) and int.from_bytes(data[10:12],'little')>=1121:
            result['frames'][g].setdefault('section5_pair',[]).append(
                dict(bytes=n,issue=round(event['start']),queued=end,accept=int(load['clock'])))
    result['preDMA']={}
    for g in result['frames']:
        rows=[r for r in window if int(r['g'])==g and r['op']=='-1']
        early=[r for r in rows if r['event']=='idle524']
        dma=[r for r in rows if r['event']=='ppu_dma']
        last=[r for r in rows if r['event']=='ppu_last']
        assert len(early)==len(dma)==len(last)
        tiles=iter(r for r in read_csv(directory,'tile532.csv') if int(r['g'])==g and r['event']=='tile')
        writes=[]
        for before,start,end in zip(early,dma,last):
            size=int(start['value'])
            assert int(before['clock'])<=int(start['clock'])<=int(end['clock'])
            value=int(before['value'])
            if value>=65536:
                kind,offset='map',value-65536
            else:
                tile=next(tiles)
                assert int(tile['n'])==size
                kind,offset='tile',int(tile['dst'])
            writes.append([kind,offset,size,int(end['frame'])])
        assert next(tiles,None) is None
        result['preDMA'][g]=writes
    return result,body


def coverage(writes):
    return {(k,i):v for k,off,n,v in writes for i in range(off,off+n)}


def compare(temp,tag,work):
    out={}
    for phase in (1,2):
        for state in ('warm','cold'):
            prefix=f'nes-tile821-obj-jointmirror-p{phase}-'
            paths=[temp/(prefix+f'{build}-{state}-pair') for build in ('907',tag)]
            (ref,old),(cand,new)=[measure(p,w) for p,w in zip(paths,(BASE,work))]
            assert ref['parameters']==cand['parameters'] and ref['client']==cand['client']
            for g in range(905,913):
                assert Counter(old[g])==Counter(new[g])
                assert [b for b in old[g] if b[1]==5]==[b for b in new[g] if b[1]==5]
                assert sha(paths[0]/f'frame-{g}.rgb')==sha(paths[1]/f'frame-{g}.rgb')
            diff={}
            for g in ref['frames']:
                a,b=ref['frames'][g],cand['frames'][g]
                assert a['section5_hash']==b['section5_hash']
                prior=coverage(ref['preDMA'][g]); after=coverage(cand['preDMA'][g])
                diff[g]=dict(OBJ=a['masterclocks']['last_OBJ'],OBJ_candidate=b['masterclocks']['last_OBJ'],
                    seal_delta_ms=round((b['masterclocks']['SEAL']-a['masterclocks']['SEAL'])*1000/MASTER,4),
                    display=[a['VBlank'][3],b['VBlank'][3]],preDMA_bytes=[len(prior),len(after)],
                    lost_preDMA_bytes=len(prior.keys()-after.keys()),
                    later_preDMA_bytes=sum(after[key]>prior[key] for key in prior.keys()&after.keys()),
                    last_color_OAM_accept=[a.get('last_accept'),b.get('last_accept')],
                    OBJ_return_to_SEAL_ms=[round((f['masterclocks']['SEAL']-f['last_OBJ_return'])*1000/MASTER,4) for f in (a,b)],
                    ARM_E0_delta_ms=round((b['masterclocks']['E0_response']-a['masterclocks']['E0_response'])*1000/MASTER,4),
                    section5_pair=[a.get('section5_pair',[]),b.get('section5_pair',[])])
            out[f'p{phase}-{state}']=dict(intervals=[ref['intervals'],cand['intervals']],
                last_ACK=[ref['final_ACK'],cand['final_ACK']],frames=diff,preDMA=[ref['preDMA'],cand['preDMA']],
                firmware=cand['firmware'],client=cand['client'],E1_bytes=cand['wire']['0xe1'])
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    results={}
    for tag,work in [('909',WORK),('909b',AFTER_PALETTE)]:
        result=compare(args.temp,tag,work)
        image=work/'link/src/obj-nes-100/firmware.stm'
        proof=work/'proof'
        for file,field in [('timer.json','firmware'),('menu.json','firmware'),('loader.json','firmware'),('base/result.json','firmware_sha256')]:
            assert json.loads((proof/file).read_bytes())[field]==sha(image)
        sram=json.loads((proof/'sram.json').read_bytes())['cases']
        assert len(sram['normal']['d0_sites'])==4 and sram['normal']['checked_retire'] and not sram['bad-crc']['checked_retire']
        assert json.loads((proof/'timer.json').read_bytes())['passed']
        assert json.loads((proof/'menu.json').read_bytes())['rows']['normal']['released']
        assert json.loads((proof/'base/result.json').read_bytes())['safe_return']
        results[tag]=dict(conditions=result,flash_bytes=image.stat().st_size,SRAM_guard_SHA256=sha(proof/'sram.json'))
    args.output.write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
