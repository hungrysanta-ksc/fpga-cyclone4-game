# SPDX-License-Identifier: MIT
"""Compare the tail byte ledger, consumer cost, and target blank at two phases."""
import argparse
import json
from pathlib import Path
from analyze_nes_map628 import csv_groups, ms, one, read, sha, packets
from analyze_nes_tail627 import deadlines

def run(a):
    phases=[]
    for phase in (1,2):
        base=a.traces/f'nes-seal625-tables-bg-{phase}'
        cutoff=deadlines(base)[951]['previous_cutoff']
        source=packets(base)[951]
        spi=[e for e in read(base/'events.json') if e['generation']==951 and e['event']=='SPI']
        preflight=0
        for opcode,size in (('0xe0',20),('0xe8',20),('0xe1',211)):
            transaction=next(e for e in spi if e['opcode']==opcode and e['bytes']==size)
            preflight+=transaction['clock']-transaction['start']
        original=csv_groups(base/'window.csv')
        show=lambda w,g:one([e for e in w[g] if e['op']==3],'reveal')['frame']
        target=show(original,950)+3
        phases.append({})
        for mode in ('neither','oam','scroll','both'):
            for schedule in (('paced','a'),('ready','a'),('ready','early2'),('ready','early3')):
                timing,suffix=schedule
                if (timing=='paced' and mode in ('oam','scroll')) or (suffix!='a' and mode!='both'):continue
                d=a.traces/f'nes-tail631-{mode}-{timing}-{phase}{suffix}'
                audit=read(d/'audit.json')
                assert audit['frames']==47 and read(d/'result.json')['last_status']==1
                assert all(sha(d/f'frame-{g}.rgb')==sha(base/f'frame-{g}.rgb') for g in range(905,952))
                w=csv_groups(d/'window.csv')
                assert show(w,950)==show(original,950)
                arrivals=[]
                for row in (d/'arrivals.tsv').read_text().splitlines()[:-1]:
                    t,h,_=row.split('\t');h=bytes.fromhex(h)
                    if int.from_bytes(h[8:10],'little')==951:arrivals.append((int(t),h))
                r=w[951]
                offset_by_index={e['index']:h for e,(_,h) in zip((e for e in r if e['event']=='load'),arrivals,strict=True)}
                # Idle DMA may log the next queue index before its head is loaded.
                # Bind attribution and all three durations to the held command.
                for entry in audit['packets']:
                    samples=[e for e in r if e['index']==entry['index']]
                    head=one(samples,'load');wire=offset_by_index[entry['index']]
                    assert (head['op'],head['section'])==tuple(wire[:2])
                    entry.update(op=head['op'],section=head['section'])
                    ticks=[one(samples,k)['clock'] for k in ('load','data631','accepted631','ack')]
                    assert entry['clocks']==[y-x for x,y in zip(ticks,ticks[1:])]
                costs=[]
                for section in (2,3,4,5):
                    entries=[v for v in audit['packets'] if v['section']==section]
                    costs.append(dict(section=section,count=len(entries),
                        stages_ms=[ms(sum(row['clocks'][k] for row in entries)) for k in range(3)]))
                seal=[e for e in r if e['op']==3]
                pushes=[t for t,h in arrivals if h[0]==7]
                early=[t for t,h in arrivals if h[1]==2 and int.from_bytes(h[10:12],'little')>=2048 and t<max(pushes)]
                ack=[e['clock'] for e in r if e['event']=='ack']
                # Every earlier offered head was actually accepted on these lightly loaded prefixes.
                early_depth=[]
                for tick in early:
                    pre=tick-round(preflight)
                    depth=sum(t<=pre for t,h in arrivals)-sum(t<=pre for t in ack)
                    assert 0<=depth<3
                    early_depth.append(depth)
                work=audit['packets']
                def command_cost(sec,limit):
                    return ms(sum(sum(q['clocks']) for q in work if q['section']==sec and
                                  int.from_bytes(offset_by_index[q['index']][10:12],'little')<limit))
                group=dict(mode=mode,timing=timing,early_depth=early_depth,count=len(work),sections=costs,
                           wire_delta_B=sum(len(h)+3 for _,h in arrivals)-sum(len(h)+3 for h,_,_ in source),
                           oam_ms=command_cost(4,544),scroll_prefix_ms=command_cost(5,1121),
                           interval=audit['interval'],seal_ms=audit['seal_ms'],upload_ms=audit['upload_ms'],
                           first_DMA_ms=audit['dma_ms'],target_DMA_B=sum(e['value'] for e in seal if e['frame']==target and e['event']=='ppu_dma'),
                           ack=audit['ack'],ack_delta625_ms=ms(audit['ack']-one([e for e in original[951] if e['op']==3],'ack')['clock']),
                           last_dma_ms=ms(max(e['clock'] for e in seal if e['event']=='ppu_last')-cutoff),
                           trace=sha(d/'window.csv'),client=audit['client'],offers=audit['offers'])
                phases[-1][f'{mode}_{timing}_{suffix}']=group
    guards=read(a.traces/'nes-tail631-guards02/guards.json')
    assert {r['boundary']:r['status'] for r in guards['cases']}=={
        **dict.fromkeys(('oam_length','oam_offset','oam_span','scroll_length','scroll_span','serial','cold'),224),
        'stop_oam':228,'stop':228}
    assert guards['restart']==dict(commits=2,status=1,restored_map_bytes=16384,restored_tail_bytes=3778)
    a.out.write_text(json.dumps(dict(phases=phases,guards=guards),indent=2)+'\n',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
