# SPDX-License-Identifier: MIT
"""Compare fixed-arrival cap changes with continuous MMC533/535 runs at both ROM phases."""
import argparse
import json
from collections import Counter,defaultdict
from pathlib import Path

from analyze_nes_map526 import ROOT,Calendar,ms,read,run_cost,sha,tiles
from analyze_nes_output531 import WARM,DENSE,breakdown,csv_groups,summarize
from analyze_nes_quiet528 import packet_content
from analyze_nes_transfer512 import fpga
from verify_nes_trial533 import timing


def profile(folder):
    events=defaultdict(list)
    for event in read(folder/'events.json'):events[event['generation']].append(event)
    cpu=csv_groups(folder/'window.csv');samples=csv_groups(folder/'seal528.csv')
    records=[json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    packets=[bytes.fromhex(row[2]) for row in records];arrivals=[row[1] for row in records]
    rows=[breakdown(g,events[g],cpu[g],samples[g],packets,arrivals) for g in WARM]
    return dict(warm=summarize(rows),dense=summarize([r for r in rows if r['g'] in DENSE]),
                missed=[dict(g=r['g'],clocks=r['miss_clocks'],seal_bytes=r['seal_bytes']) for r in rows if r['miss_clocks']])


def grant_sizes(c):
    sizes=[]
    for i,r in enumerate(c):
        if r['event']=='idle524' and r['value']>=65536:
            dma=c[i+1]
            assert dma['event']=='ppu_dma' and dma['op']==-1
            sizes.append(dma['value'])
    return sizes


def analyze(a):
    ref=read(ROOT/'analysis/tile532-verification.json')
    release=read(ROOT/'analysis/trial533-verification.json')
    package=read(ROOT/'analysis/trial533-package.json')
    assert sha(ROOT/'analysis/trial533-verification.json')==package['evidence_SHA256']
    assert release['identical_functions']==788 and ref['target_met']['pair']
    old_image=sha(a.baseline_client/'sink165.sfc');new_image=sha(a.client/'sink165.sfc')
    assert old_image==ref['clients']['pair']['sha256']
    oracle=tiles(a.fixture,957);calendar=Calendar(a.calendar)
    plans={f['generation']:f for f in read(ROOT/'analysis/obj518-verification.json')['plans']['frames']}
    schedules=read(ROOT/'analysis/prefix523-verification.json')['phases']
    phases=[]
    for i,(baseline,candidate) in enumerate(zip(a.baseline,a.candidate)):
        old=ref['phases'][i]['variants']['pair']
        assert packet_content(baseline)==packet_content(candidate)
        assert all(sha(baseline/f'frame-{g}.rgb')==sha(candidate/f'frame-{g}.rgb') for g in range(905,958))
        variants={}
        for name,folder,firmware,limit,image in [('533',baseline,ref['ARM'],128,old_image),
                                                 ('535',candidate,release['firmware_SHA256'],256,new_image)]:
            costs,_=run_cost(folder,'row254',dict(schedules[i]['candidate'],firmware=firmware),plans,calendar,oracle,map_chunk=limit)
            assert costs['client']==image and all(costs[k]==old[k] for k in ('ROM_reads','dma_B','tiles','packets'))
            assert not any((folder/n).exists() for n in ('map-error.txt','callback-error.txt'))
            if name=='533':assert costs['pins']==old['pins'] and costs['final_ack']==old['final_ack']
            frames=costs.pop('frames')
            costs['display']=[{k:r[k] for k in ('g','gap_ms','display_VBlanks','seal_waits','final_waits','ack','early_B')} for r in frames]
            costs['output']=profile(folder)
            cpu=csv_groups(folder/'window.csv')
            histogram=Counter(n for g in range(905,958) for n in grant_sizes(cpu[g]))
            costs['map_grants_by_size']=dict(histogram)
            variants[name]=costs
        control,cost=variants.values()
        replay=read(a.audit[i]/'audit.json')
        assert replay['frames']==53 and replay['trace']==cost['pins']['window.csv']
        assert sha(a.audit[i]/'tile532.csv')==sha(candidate/'tile532.csv')
        cost['independent_replay']=replay
        fixed={}
        for g,folder in ((910,a.target910[i]),(922,a.target922[i]),(951,a.target951[i])):
            proof=read(folder/'audit.json')
            assert proof['g']==g and proof['candidate_SHA256']==new_image and proof['trace']==sha(folder/'window.csv')
            for key,d in [('reference',baseline),('candidate',folder)]:
                proof[key]['map_DMA_B']=grant_sizes(csv_groups(d/'window.csv')[g])
                latch=[r for r in csv_groups(d/'seal528.csv')[g] if r['event']=='latch']
                proof[key]['last_latch_line_h']=[latch[-1]['line'],latch[-1]['h']] if latch else None
            proof['delta_ACK_ms']=ms(proof['candidate']['ACK']-proof['reference']['ACK'])
            fixed[g]=proof
        phases.append(dict(start=schedules[i]['candidate']['parameters']['start'],variants=variants,fixed=fixed,
                           dense_VBlank_change=sum(cost['display'][g-905]['display_VBlanks']-control['display'][g-905]['display_VBlanks'] for g in DENSE),
                           dense_ms_change=cost['dense_ms']-control['dense_ms'],last_ACK_ms_change=ms(cost['final_ack']-control['final_ack'])))
    edges=read(a.edges/'edges.json')
    assert [(r['line'],r['size']) for r in edges]==[(254,256),(255,0),(256,0),(233,0)]
    assert 225<=edges[0]['start_line']<=edges[0]['end_line']<262
    guards=read(a.guards/'result.json');maps=read(a.map_guards/'result.json')
    assert len(guards)==22 and len(maps)==12
    for r in maps:
        assert r['size']==((256 if r['generation']==906 else 64) if r['grant'] else 0)
    cost=fpga(a.board)
    raw,worst,ucp=timing(a.board)
    old_raw,_,old_ucp=timing(a.reference_board)
    assert sha(a.reference_board/'output_files/board.sof')==release['SOF_SHA256']
    assert sha(a.board/'sink-program.hex')==sha(a.client/'sink-program.hex')
    assert [n for n,h in release['inputs'].items() if sha(a.board/n)!=h]==['sink-program.hex']
    board=dict(cost=cost,SOF=sha(a.board/'output_files/board.sof'),raw_worst_ns=worst,
               equal_raw_summary=raw==old_raw,equal_unconstrained=ucp==old_ucp)
    return dict(phases=phases,board=board,physical_baseline=read(ROOT/'analysis/hardware534-mmc533.json')['display'],
                original_body_B=(a.baseline_client/'body.bin').stat().st_size,body_B=(a.client/'body.bin').stat().st_size,
                full_map_STOP_head=maps,other_guard_cases=len(guards),edges=edges,
                comparison_passed=all(p['dense_VBlank_change']<0 and p['dense_ms_change']<0 and p['last_ACK_ms_change']<0 and
                    all(p['variants']['535']['display'][g-905]['final_waits']==0 for g in (952,954)) for p in phases))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('baseline','candidate','audit','target910','target922','target951'):p.add_argument('--'+name,nargs=2,type=Path,required=True)
    for name in ('client','baseline-client','fixture','calendar','edges','guards','map-guards','board','reference-board','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',newline='\n')
