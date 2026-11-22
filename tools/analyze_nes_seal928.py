"""Compare the physical endpoints, the fixed-offer phase sweep and the closed-loop ARM runs."""
import argparse
import hashlib
import json
from pathlib import Path

from read_nes_display927 import decode
from replay_nes_seal928 import ROOT, read_csv

MASTER_PER_MS=21477.272


def read(path):
    return json.loads(path.read_bytes())


def physical(path):
    data=decode(path)
    assert data['mode']==0 and not any(data['dropped'])
    by_gen={r['generation']:r for r in data['rows'] if 'invalid' not in r}
    rows={}
    for g in (1225,1227):
        r=by_gen[g]
        assert (r['BG'],r['OBJ'],r['map'],r['bank'])==(529,18,0,0)
        assert (r['first_post_seal'][1],r['last_post_seal'][1])==('VRAM-low','OAM')
        marks=[r['last_tile'],r['seal'],r['first_post_seal'][0],r['last_post_seal'][0],r['reveal'],r['ACK']]
        rows[g]=[round(t-r['previous_reveal'],3) for t in marks]
    return dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),physical_ms=rows,
                events=['tile','SEAL','VRAM start','OAM end','reveal','ACK'])


def report(temp,out,log):
    from analyze_nes_window924 import coverage,sample
    from prepare_nes_trial925 import WORK
    package=read(ROOT/'analysis/trial925-package.json')
    evidence=dict(hardware=physical(log),phase={},joint={})
    for p,edge in ((1,195),(2,196)):
        trace=temp/f'nes-tile821-obj-jointmirror-p{p}-925final-warm-pair'
        packets=[bytes.fromhex(json.loads(line)[2]) for line in (trace/'packets.jsonl').read_text().splitlines()]
        tile_extents={(int.from_bytes(pkt[10:12],'little'),int.from_bytes(pkt[14:16],'little')):pkt[1]
                      for pkt in packets if pkt[0]==7 and pkt[8:10]==b'\x90\x03'}
        base=out/f'p{p}-200'
        summary=read(base/'summary.json')
        jobs=summary['jobs']
        dma=[r for r in read_csv(base,'seal528.csv') if r['g']=='912' and r['event']=='dma' and
             int(r['clock'])>summary['seal'][2]]
        assert len(dma)==len(jobs)
        for job,row in zip(jobs,dma):
            if job[0]=='VRAM':
                # Bank 1 OBJ cache is staged at $C000 and targets VRAM byte $8000.
                assert int(row['bank'])==1 and int(row['src'])-0xc000==int(row['dst'])-0x8000
                assert tile_extents[int(row['dst'])-0x8000,job[1]]==1
                job[0]='OBJ'
        first,second=jobs[0][2],jobs[-1][2]
        assert second==first+1 and [(r[0],r[1]) for r in jobs if r[2]==second]==[
            ('raw',64),('raw',64),('raw',64),('CGRAM',512),('OAM',544)]
        sweep={}
        for target in (0,188,192,194,195,196,198,200,204,208,214):
            for policy in ('baseline','group','edge'):
                suffix='' if policy=='baseline' else '-'+policy
                result=out/f'p{p}-{target}{suffix}'/'summary.json'
                if result.exists():
                    s=read(result)
                    sweep[f'{target}-{policy}']=[s['seal'],s['show'],s['ack'][2]]
        orig,patch=(sweep[f'{edge}-{pol}'] for pol in ('baseline','edge'))
        assert orig[0]==patch[0] and orig[1][0]==patch[1][0]+1
        stop=read(out/f'p{p}-{edge}-edge-stop/result.json')
        assert stop['last_status']==0xe4 and stop['commits']==7
        canceled=[r['event'] for r in read_csv(out/f'p{p}-{edge}-edge-stop','window.csv')
                  if r['g']=='912' and r['op']=='3']
        assert 'load' in canceled and not {'reveal','ppu_dma'}.intersection(canceled)
        earlier=sweep['194-baseline']
        assert earlier[1][0]==first and earlier[1][1]<=246
        bus=read(trace/'events.json')
        idx=next(i for i,e in enumerate(bus) if e.get('generation')==912 and e.get('packet_opcode')==3)
        tail=bus[idx-5:idx+1]
        assert [e.get('packet_opcode') for e in tail]==[7,2,None,None,2,3]
        assert [e['opcode'] for e in tail[2:4]]==['0xe0','0xe8']
        evidence['phase'][p]=dict(sweep=sweep,first_blank=first,dma_201=jobs,
            edge_gain_ms=round((orig[2]-patch[2])/MASTER_PER_MS,5),
            seal_advance_to_195_ms=round((summary['seal'][2]-earlier[0][2])/MASTER_PER_MS,5),
            OBJ_end_to_SEAL_end_ms=round((tail[-1]['clock']-tail[0]['clock'])/MASTER_PER_MS,5),
            tail_spi_ms=[round((e['clock']-e['start'])/MASTER_PER_MS,5) for e in tail[1:]],
            tail_gaps_ms=round(sum(b['start']-a['clock'] for a,b in zip(tail,tail[1:]))/MASTER_PER_MS,5),
            stop_status=stop['last_status'])
        for cache in ('warm','cold'):
            tag=f'{p}-{cache}'
            folder=temp/f'nes-tile821-obj-jointmirror-p{p}-928edge-{cache}-pair'
            joint=read(folder/'joint.json')
            assert joint['passed'] and joint['firmware_SHA256']==package['firmware']
            assert joint['client_SHA256']==hashlib.sha256((out/'edge928/sink165.sfc').read_bytes()).hexdigest()
            verified=read(folder/'verified905.json')
            row,_=sample(folder,WORK)
            ref=package['cases'][tag]
            assert verified['RGB']==8 and row['ack912']==verified['final_ACK'][-1]
            retained=len(coverage(row['pre912']))
            if cache=='cold':
                assert retained==ref['pre912_B']==496
            evidence['joint'][tag]=dict(intervals=[ref['intervals'],row['intervals']],gaps=row['gaps'],
                ACK_clocks=[ref['final_ACK'],row['ack912']],delta_ms=round((row['ack912']-ref['final_ACK'])/MASTER_PER_MS,5),
                pre912_bytes=retained,RGB=verified['RGB'])
    return evidence


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('temp','out','log','json'):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    a.json.write_text(json.dumps(report(a.temp,a.out,a.log),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
