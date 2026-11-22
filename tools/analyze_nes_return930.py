"""Attribute two adjacent OBJ descriptors using their wire tokens and staging ranges."""
import argparse
import json
from pathlib import Path

from analyze_nes_palette921 import coverage, directory, read, read_csv, sha
from analyze_nes_section929 import timeline
from analyze_nes_window924 import sample
from nes_return930 import image
from test_nes_raw506_joint import crc


def jobs(folder, tokens=(35,36,37,38)):
    events=read(folder/'events.json')
    e1=[e for e in events if e.get('opcode')=='0xe1']
    packets=[json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    heads=[r for r in read_csv(folder,'window.csv') if r['g']=='912']
    loaded=iter(r for r in heads if r['event']=='load')
    ready={p['token']:p for line in (folder/'producer.jsonl').read_text().splitlines()
           if (p:=json.loads(line))['generation']==912}
    returns=dict(read(folder/'returns904.json'))
    result={}
    for wire,event in zip(packets,e1,strict=True):
        b=bytes.fromhex(wire[2])
        if int.from_bytes(b[8:10],'little')!=912:
            continue
        head=next(loaded)
        assert (b[0],b[1])==(int(head['op']),int(head['section']))
        if b[:2]!=bytes((7,1)):
            continue
        token=int.from_bytes(b[16:20],'little')
        if token not in tokens:
            continue
        at=int.from_bytes(b[10:12],'little')
        size=int.from_bytes(b[14:16],'little')
        assert ready[token]['bytes']==size
        desc=bytes((1,1))+b[14:16]+b[10:12]+b[8:10]+b[16:20]
        e8=next(e for e in events if e.get('generation')==912 and e.get('opcode')=='0xe8'
                and bytes.fromhex(e['reply'])[6:18]==desc)
        reply=bytes.fromhex(e8['reply'])
        assert crc(reply[1:19],8,7,0)==reply[19]
        steps={r['event']:int(r['clock']) for r in heads if r['index']==head['index']}
        marks=dict(ready=ready[token]['producer'],E8=round(e8['clock']),
                   E1=round(event['clock']),load=steps['load'],first_read=steps['first_read920'],
                   last_read=steps['last_read920'],returned=steps['consume920'],head_ACK=steps['ack'])
        assert list(marks.values())==sorted(marks.values()) and marks['returned']==returns[token]
        setup={name:int(steps[name]) for name in
               ('header920','bulk194920','data_size_ok920','mark212920','append212920')}
        result[token]=dict(offset=at,bytes=size,clocks=marks,setup=setup)
    assert next(loaded,None) is None and set(result)==set(tokens)
    return result


def supply(folder,tiles):
    lanes=read(folder/'slots930.json')
    spec=[(addr,grant,reply) for g,addr,grant,reply in read(folder/'ahead911.json') if g==912]
    grants=[g for g in read(folder/'grants904.json') if g[0]==912 and g[1]==1]
    assert [g for slot,addr,t,end,row in lanes for g in row]==grants
    result={'generation_demand_grants':len(grants),'generation_spec_grants':len(spec)}
    for token in (37,38):
        job=tiles[token]
        rows=[r for r in lanes if job['offset']<=r[0]<job['offset']+job['bytes']]
        actual=[dict(address=addr,request=g[2],grant=g[3],reply=g[4])
                for slot,addr,t,end,items in rows for g in items]
        addrs={r[1] for r in rows}
        tags={a//16 for a in addrs}
        matching=[g for g in spec if g[0] in addrs]
        assert rows and max(r[3] for r in rows)<=job['clocks']['ready']
        result[token]=dict(lookups=len(rows),first_lookup=rows[0][2],last_lookup_end=rows[-1][3],
                           demand_grants=actual,same_address_spec_grants=matching,
                           other_spec_rows_in_same_tags=sorted({addr for addr,_,_ in spec
                                                                if addr//16 in tags and addr not in addrs}))
    return result


def report(temp):
    def folder(phase,cache,mode):
        return directory(temp,phase,'930'+mode,cache)
    out={'units':'NTSC master clocks, 21477272 Hz','cases':{},'builds':{}}
    modes=('handoff','short','prefix')
    for mode in modes:
        work=image(mode)
        fw=work/'link/src/obj-nes-100/firmware.stm'
        digest=sha(fw)
        base=read(work/'proof/base/result.json')
        assert base['safe_return'] and base['firmware_sha256']==digest
        assert read(work/'proof/menu.json')['rows']['normal']['released']
        rx=read(work/'proof/sram.json')['cases']
        assert len(rx['normal']['d0_sites'])==4 and not rx['bad-crc']['checked_retire']
        guards=read(work/'guards.json')
        stops=read(work/'stops.json')
        assert {k:(v['status'],v['commits']) for k,v in guards.items()}=={
            'descriptor':(224,3),'duplicate':(224,3),'seal':(224,4),
            'stop-copy':(228,3),'display_stop':(228,4)}
        assert stops=={k:{'status':228,'commits':4} for k in ('32','352')}
        out['builds'][mode]=dict(firmware=digest,flash=fw.stat().st_size,base_return=True,
                                 menu=True,SRAM_D0_sites=4,bad_crc_rejected=True,guards=guards,obj_stop=stops)
    for phase in (1,2):
        for cache in ('warm','cold'):
            key=f'{phase}-{cache}'
            case=out['cases'][key]={}
            control=directory(temp,phase,'925final',cache)
            ref,quality=sample(control,image('base'))
            for mode in ('base',*modes):
                d=folder(phase,cache,mode)
                row,actual=sample(d,image(mode))
                assert quality==actual
                joint=read(d/'joint.json')
                assert joint['passed'] and joint['client_SHA256']==read(control/'joint.json')['client_SHA256']
                assert joint['firmware_SHA256']==sha(image(mode)/'link/src/obj-nes-100/firmware.stm')
                tail=timeline(d)
                tiles=jobs(d)
                blocked=read(d/'rows911.json')['blocked'].get('36')
                if blocked:
                    assert blocked[0]==912 and blocked[1]<=tiles[36]['clocks']['returned']
                pre=coverage(row['pre912'])
                rec=dict(tiles=tiles,SEAL=tail['marks']['SEAL'][2],previous_reveal=tail['previous_reveal'],
                         two_banks_full_wait_for_token36=blocked,
                         reveal=next(int(r['clock']) for r in read_csv(d,'window.csv')
                                     if r['g']=='912' and r['event']=='reveal'),
                         gaps=row['gaps'],capture_offset=row['capture_offset'],pre912_B=len(pre),
                         same_pre912=pre.keys()==coverage(ref['pre912']).keys(),ACK=row['ack912'])
                if mode=='base':
                    assert row==ref and (d/'events.json').read_bytes()==(control/'events.json').read_bytes()
                    trace=folder(phase,cache,'supply')
                    assert (d/'window.csv').read_bytes()==(trace/'window.csv').read_bytes()
                    assert (d/'grants904.json').read_bytes()==(trace/'grants904.json').read_bytes()
                    rec['supply']=supply(trace,tiles)
                case[mode]=rec
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    a.output.write_text(json.dumps(report(a.temp),indent=2)+'\n',encoding='utf-8')
