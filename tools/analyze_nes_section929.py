"""Match the producer, published packets, independent 65816 loads and displayed frames."""
import argparse
import hashlib
import json
from pathlib import Path

from analyze_nes_palette921 import coverage, directory, read, read_csv, sha
from analyze_nes_window924 import sample
from nes_section929 import LAST, ORIGINAL, WORK

LINKS = {'925final': ORIGINAL, '929prefix': WORK, '929last': LAST}


def timeline(folder):
    packets = [json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    events=read(folder/'events.json')
    spi = [e for e in events if e.get('opcode')=='0xe1']
    last = {}
    order = []
    joined = bytearray()
    window=read_csv(folder,'window.csv')
    heads = [r for r in window if r['g']=='912' and r['event']=='load']
    for (_, end, wire, _), event in zip(packets, spi, strict=True):
        p = bytes.fromhex(wire)
        if p[8:10] != (912).to_bytes(2,'little'):
            continue
        head = heads.pop(0)
        op, section, length = p[0], p[1], int.from_bytes(p[12:14],'little')
        assert [op,section] == [int(head['op']),int(head['section'])]
        assert abs(event['clock']-end)<1
        if op==7 and section==1:
            key='OBJ'
        elif op==2 and section==5 and length in (201,240):
            key=str(length)
            joined.extend(p[16:])
        elif op==3:
            key='SEAL'
        else:
            continue
        order.append(key)
        last[key]=[round(event['start']),round(event['clock']),int(head['clock'])]
    assert not heads and len(joined)==441
    jobs = [j for line in (folder/'producer.jsonl').read_text().splitlines()
            if (j:=json.loads(line))['generation']==912 and j['kind']==1]
    prior,producer=jobs[-2:]
    token=producer['token']
    returns=dict(read(folder/'returns904.json'))
    assert prior['token']+1==token
    response=next(round(e['clock']) for e in events if e.get('generation')==912 and
                  e.get('opcode')=='0xe8' and (rx:=bytes.fromhex(e['reply']))[6:8]==bytes((1,1))
                  and int.from_bytes(rx[14:18],'little')==token)
    assert producer['producer']<=response<=last['OBJ'][0]
    tail=[k for i,k in enumerate(order) if k!='OBJ' or 'OBJ' not in order[i+1:]]
    assert sorted(tail)==['201','240','OBJ','SEAL']
    shown=next(int(r['frame']) for r in window if r['g']=='912' and r['event']=='reveal')
    # All lines in this NTSC VBlank last 1364 master clocks. Bracket the
    # start of line 247 without assuming that a line-only sample is at h=0.
    estimates=[int(r['clock'])+(247-int(r['line']))*1364 for r in window
               if int(r['frame'])==shown-1 and 225<=int(r['line'])<=261]
    end246=[max(estimates)-1363,min(estimates)]
    assert end246[0]<=end246[1]
    previous=next(int(r['clock']) for r in window if r['g']=='911' and r['event']=='reveal')
    return dict(tail_order=tail, marks=last, producer_ready=producer['producer'], token=token,
                OBJ_first_E8=response, previous_reveal=previous,
                previous_OBJ_bytes=prior['bytes'], previous_OBJ_return=returns[prior['token']],
                final_OBJ_bytes=producer['bytes'],
                prior_end_line246=end246,
                joined_sha256=hashlib.sha256(joined).hexdigest())


def report(temp):
    evidence = {'units':'master clocks at 21477272 Hz; marks = SPI start, SPI end, 65816 load',
                'links':{},'cases':{}}
    for tag, work in LINKS.items():
        fw=work/'link/src/obj-nes-100/firmware.stm'
        evidence['links'][tag]=dict(firmware=sha(fw), flash_B=fw.stat().st_size)
        if tag!='925final':
            proof=work/'proof'
            digest=evidence['links'][tag]['firmware']
            base=read(proof/'base/result.json')
            assert base['safe_return'] and base['firmware_sha256']==digest
            for name in ('loader','menu','timer'):
                assert read(proof/f'{name}.json')['firmware']==digest
            assert read(proof/'menu.json')['rows']['normal']['released'] and read(proof/'timer.json')['passed']
            rx=read(proof/'sram.json')['cases']
            assert len(rx['normal']['d0_sites'])==4 and not rx['bad-crc']['checked_retire']
            guards=read(work/'guards.json')
            obj_stop=read(work/'obj-stop.json')
            assert {k:(v['status'],v['commits']) for k,v in guards.items()}=={
                'stop-copy':(228,3),'descriptor':(224,3),'duplicate':(224,3),
                'seal':(224,4),'display_stop':(228,4)}
            assert {k:(v['status'],v['commits']) for k,v in obj_stop.items()}=={'32':(228,4),'352':(228,4)}
            evidence['links'][tag].update(guards=guards,obj_stop=obj_stop,base_return=True,menu=True,
                                          sram_D0_sites=4,bad_crc_rejected=True)
    for phase in (1,2):
        for cache in ('warm','cold'):
            rows={}
            for tag, work in LINKS.items():
                folder=directory(temp,phase,tag,cache)
                row,quality=sample(folder,work)
                joint=read(folder/'joint.json')
                assert joint['passed'] and joint['firmware_SHA256']==evidence['links'][tag]['firmware']
                if tag=='925final':
                    control_quality=quality
                    control=folder
                    pre=coverage(row['pre912'])
                else:
                    assert quality==control_quality and joint['client_SHA256']==read(control/'joint.json')['client_SHA256']
                result=timeline(folder)
                result.update(gaps=row['gaps'],intervals=row['intervals'],ACK=row['ack912'],
                              pre912_B=len(coverage(row['pre912'])),
                              pre912_same=coverage(row['pre912']).keys()==pre.keys(),
                              capture_offset=row['capture_offset'])
                if tag=='925final':
                    joined=result['joined_sha256']
                assert result['joined_sha256']==joined
                if cache=='warm' and tag in ('925final','929prefix'):
                    observed=directory(temp,phase,'929mark'+('base' if tag=='925final' else 'prefix'),cache)
                    assert (observed/'window.csv').read_bytes()==(folder/'window.csv').read_bytes()
                    mark=read(observed/'prefix929.json')
                    assert mark['joined_sha256']==joined and mark['clock']<=result['marks']['201'][0]
                    result['ARM_joined_at_call']=mark
                rows[tag]=result
            evidence['cases'][f'{phase}-{cache}']=rows
    return evidence


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(report(args.temp),indent=2)+'\n',encoding='utf-8')
