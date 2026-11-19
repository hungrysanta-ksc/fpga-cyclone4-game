"""Compare observed MMC866 planner boundaries with strip acceptance deadlines."""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CLOCK=21477272


def read(path):
    return json.loads(path.read_bytes())


def unoccupied(start,duration,intervals):
    for a,b in intervals:
        if b<=start:continue
        if a>=start+duration:break
        start=max(start,b)
    return start


def fifo_finish(ready,wire,service,deadline,bus,busy,others):
    """Insert into a two-slot FIFO gap without moving any unrelated E1/load.

    Wait for all earlier entries to retire before servicing the candidate.
    Reject intervals that would require a third outstanding entry. A wire
    start reserves the slot here, conservatively preceding ingress acceptance.
    """
    earlier=[]
    for packet in others:
        start,end,load,ack=packet
        if start>=ready or end>=ready:
            issue=unoccupied(max(ready,earlier[-1][1] if earlier else ready),wire,bus)
            consume=unoccupied(max(issue+wire,earlier[-1][3] if earlier else 0),service,busy)
            finish=consume+service
            if issue+wire<=start and finish<=min(load,deadline):
                marks=[(issue,1),(finish,-1)]
                for s,_,_,a in others:
                    if s>=finish:break
                    if a>issue:marks.extend(((max(s,issue),1),(min(a,finish),-1)))
                active=0
                for _,delta in sorted(marks):
                    active+=delta
                    if active>2:break
                else:return finish
        if start>deadline:break
        earlier.append(packet)
    return None


def phase(temp,n,tag):
    folder=temp/f'nes-tile821-demo-jointmirror-p{n}-{tag}'
    baseline=temp/f'nes-tile821-demo-jointmirror-p{n}-866-on'
    measured=read(folder/'frontier869.json')
    joint=read(folder/'joint.json')
    assert joint==read(baseline/'joint.json') and joint['passed'] and joint['commits']==62
    hashes={}
    for name in ('packets.jsonl','window.csv','frontier869.json'):
        hashes[name]=hashlib.sha256((folder/name).read_bytes()).hexdigest()
        if name!='frontier869.json':
            assert hashes[name]==hashlib.sha256((baseline/name).read_bytes()).hexdigest()
    timeline=read(folder/'events.json')
    spi=[e for e in timeline if e.get('event')=='SPI' and 'start' in e]
    assert all(a['clock']<=b['start']+1 for a,b in zip(spi,spi[1:]))
    e1=[e for e in spi if e['opcode']=='0xe1']
    commands=defaultdict(list)
    with (folder/'window.csv').open() as f:
        window=list(csv.DictReader(f))
    recv=defaultdict(dict)
    dma=[]
    for r in window:
        t=int(r['clock'])
        if r['event'] in ('load','ack'):recv[int(r['index'])][r['event']]=t
        if int(r['g'])>=907 and r['event']=='ppu_dma':dma.append([t,None])
        if int(r['g'])>=907 and r['event']=='ppu_last':
            assert dma and dma[-1][1] is None
            dma[-1][1]=t
    assert all(b is not None for a,b in dma)
    for i,(line,event) in enumerate(zip((folder/'packets.jsonl').read_text().splitlines(),e1,strict=True),1):
        raw=bytes.fromhex(json.loads(line)[2])
        if raw[0] in (2,4) and raw[1]==2:
            g=int.from_bytes(raw[8:10],'little')
            offset=int.from_bytes(raw[10:12],'little')
            size=len(raw)-16 if raw[0]==2 else int.from_bytes(raw[14:16],'little')
            commands[g].append((offset,size,i,event))
    producer=read(ROOT/'analysis/map868-producer.json')
    history=read(ROOT/'analysis/history869.json')
    new_counts={(row['g'],c['page']):c['instructions'] for row in history['records'] for c in row['prepare']}
    records=read(ROOT/'analysis/map868-strip.json')['phases'][n-1]['frames']
    cal=producer['phases'][n-1]
    rows=[]
    def ms(clocks):return round(clocks*1000/CLOCK,4)
    for r,count,prior in zip(records,producer['ARM_instructions']['packed'],cal['deadlines'],strict=True):
        g,page=r['g'],r['page']
        trace=measured[str(g)]
        assert len(trace['offers'])==1 and len(trace['closed'])==len(trace['groups'])
        stoprow=min(23,len(trace['closed']))-1
        assert stoprow>=0
        close=trace['closed'][stoprow]
        offer=trace['offers'][0]
        first=page//64
        written=max(trace['writes'][first:first+23])
        changed=max(trace['changes'][first:first+23])
        target=(baseline/f'map-{g}.bin').read_bytes()[page:page+1472]
        slots={int.from_bytes(target[i:i+2],'little')&1023 for i in range(0,1472,2)}
        last_slot=max((t for k,t in trace['slots'].items() if int(k) in slots),default=0)
        assert changed<=written<=close<=offer
        group=[(i,e) for at,size,i,e in commands[g] if page<=at and at+size<=page+1472]
        assert len(group)==8
        first_issue=min(e['start'] for _,e in group)
        last_ack=max(recv[i]['ack'] for i,_ in group)
        wire=r['new_wire']*cal['E1_masterclocks_per_byte']+cal['E1_fixed_masterclocks']
        arm=new_counts[g,page]*2*CLOCK/84000000
        service=r['new_service']
        deadline=last_ack-wire-arm-service
        assert abs(ms(deadline-first_issue+arm-count*2*CLOCK/84000000)-prior['first_issue_slack_ms'])<0.001
        gate=max(close,last_slot)
        # Keep all unrelated measured transactions, packet handlers, and DMA at
        # their original clocks. No claim about future credit/CPU scheduling.
        excluded={i for i,_ in group}
        spans={id(e) for _,e in group}
        occupied=[(e['start'],e['clock']) for e in spi if id(e) not in spans]
        bus=unoccupied(gate+arm,wire,occupied)
        busy=sorted([(v['load'],v['ack']) for i,v in recv.items() if i not in excluded and 'ack' in v and 'load' in v]
                    +[(a,b) for a,b in dma])
        cpu=unoccupied(bus+wire,service,busy)
        others=[(e['start'],e['clock'],recv[i]['load'],recv[i]['ack']) for i,e in enumerate(e1,1)
                if i not in excluded and e['start']<=last_ack+1000000 and recv[i].get('ack',0)>=gate
                and 'load' in recv[i]]
        fifo=fifo_finish(gate+arm,wire,service,last_ack,occupied,busy,others)
        late=fifo_finish(max(offer,last_slot)+arm,wire,service,last_ack,occupied,busy,others)
        mask_matches=all(page<=at and at+size<=page+1472 for at,size,_,_ in commands[g])
        rows.append(dict(g=g,page=page,groups=len(trace['closed']),first_issue=round(first_issue),
            last_store=round(written),last_change=round(changed),last_used_slot=round(last_slot),
            row_close=round(close),bg_done=round(offer),credit_deadline=round(deadline),
            first_issue_to_close_ms=ms(close-first_issue),row_slack_ms=ms(deadline-gate),
            bg_end_slack_ms=ms(deadline-max(offer,last_slot)),fixed_slots_slack_ms=ms(last_ack-cpu-service),
            fifo_slack_ms=ms(last_ack-fifo) if fifo is not None else None,whole_page_only=mask_matches,
            bg_done_fifo_slack_ms=ms(last_ack-late) if late is not None else None))
    return dict(phase=n,hashes=hashes,baseline_ACK=joint['frames'][-1]['ACK_masterclock'],
                pages=rows,positive={k:sum(r[k]>0 for r in rows)
                for k in ('row_slack_ms','bg_end_slack_ms','fixed_slots_slack_ms')})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('tag')
    p.add_argument('out',type=Path)
    a=p.parse_args()
    phases=[phase(a.temp,n,a.tag) for n in (1,2)]
    a.out.write_text(json.dumps(dict(phases=phases),indent=2)+'\n')
