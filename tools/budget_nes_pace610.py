"""Compare same-workload credit pacing and replaced source with complete display ACKs."""
import argparse
import json
from bisect import bisect_right
from collections import Counter
from pathlib import Path
from statistics import median
from analyze_nes_phase537 import ROOT,read,sha,one,ms,csv_groups,Calendar
from budget_nes_planner607 import phase
from budget_nes_obj609 import dma_split
from check_nes_wire600 import pin


def removed_line_hits(samples):
    pin(samples,read(ROOT/'analysis/snoop601-verification.json')['fixture_sha256'])
    tag=-1;valid={};g=904;rows=[]
    for line in samples.read_text().splitlines():
        op,kind,address,value,_=line.split()
        if op=='0':g+=1
        elif op=='2':
            address=int(address,16);value=int(value,16)
            if tag==address//16 and address%16 in valid:
                assert valid[address%16]==value
                rows.append(dict(generation=g,kind=int(kind),address=address))
            else:
                if tag!=address//16:tag=address//16;valid={}
                valid[address%16]=value
    assert len(rows)==48 and all(r['kind']==0 for r in rows)
    return dict(samples_sha256=sha(samples),rows=rows,
                by_generation=Counter(r['generation'] for r in rows))


def terminal(folder,g):
    events=[e for e in read(folder/'events.json') if e['generation']==g]
    enter=one(events,'end_enter')['clock']
    end=read(folder/'obj-phases.json')[str(g)]['end_accepted']
    window=[e for e in events if enter<=e['clock']<=end]
    return dict(END_ms=ms(end-enter),
        ready_E8=sum(e.get('opcode')=='0xe8' and bytes.fromhex(e['reply'])[6]==1 for e in window),
        map_attempts=sum(e['event']=='map_credit_attempt' for e in window),
        E1_by_op=Counter(e['packet_opcode'] for e in window if e.get('opcode')=='0xe1'),
        END_clock=end)


def compare(a,i):
    metric=phase(a,i,a.prefix)
    old=read(ROOT/'analysis/obj609-verification.json')['phases'][i-1]
    baseline=a.traces/f'nes-obj609-phase{i}'
    for name,h in old['pins'].items():pin(baseline/name,h)
    palette=read(ROOT/'analysis/quiet608-palette.json')['phases'][i-1]['candidate']
    path=a.traces/f'{a.prefix}{i}';events=read(path/'events.json')
    cpu=csv_groups(path/'window.csv');obj=read(path/'obj-phases.json')
    packets=[json.loads(line) for line in (path/'packets.jsonl').read_text().splitlines()]
    pushed=[p[1] for p in packets]
    retired=sorted(r['clock'] for rows in cpu.values() for r in rows if r['event']=='ack')
    occupancy=Counter()
    for e in events:
        if e.get('opcode')=='0xe0':
            b=bytes.fromhex(e['reply']);sent=int.from_bytes(b[3:5],'big');done=int.from_bytes(b[5:7],'big')
            assert (sent,done)==(bisect_right(pushed,e['start']),bisect_right(retired,e['start']))
            occupancy[sent-done]+=1
        if e.get('opcode')=='0xe1':
            sent=bisect_right(pushed,e['start'])
            if not a.bulk_map and (not a.map_only or (sent and bytes.fromhex(packets[sent-1][2])[1]==2)):
                assert sent==bisect_right(retired,e['start'])
    assert max(occupancy)<= (4 if a.map_only or a.bulk_map else 1)
    hits=sum(q[-1] for p in obj.values() for q in p.get('OBJ609',[]))
    assert hits==old['OBJ_hits']==1200
    source={e['generation']:e for e in events if e['event']=='source_begin'}
    assert set(source)==set(range(905,958))
    calendar=Calendar(a.calendar);reuse=[]
    for g in range(905,958):
        d=obj[str(g)];final=one([r for r in cpu[g] if r['op']==3],'ack')['clock']
        assert final<=d['ea']
        if g+2 in source:
            reuse.append(source[g+2]['capture_ready']-240*341*4-d['ea'])
        for _,_,t,r,cached in d.get('OBJ609',[]):
            assert source[g]['capture_ready']<=t<r<=final
            assert r==(t+8 if cached else calendar.select(t+8)[1])
    assert min(reuse)>=0
    joint=read(path/'joint.json');assert joint['max_bulk_banks']==2
    watched={}
    candidate=metric['candidate']
    oldcpu=csv_groups(baseline/'window.csv')
    reveals=[one([r for r in oldcpu[g] if r['op']==3],'reveal')['clock'] for g in range(905,958)]
    intervals=sorted(ms(b-a) for a,b in zip(reveals[1:],reveals[2:]))
    old_intervals=dict(intervals=len(intervals),median_ms=median(intervals),
        p95_nearest_rank_ms=intervals[-3],max_ms=max(intervals),mean_ms=sum(intervals)/len(intervals))
    for g in (951,952,954,957):
        before=dma_split(baseline,g);after=dma_split(path,g)
        seal=[r for r in cpu[g] if r['op']==3]
        prev=one([r for r in cpu[g-1] if r['op']==3],'reveal')
        reveal=one(seal,'reveal');last=one(seal,'ack');final=one(seal,'final212')
        oldseal=[r for r in oldcpu[g] if r['op']==3]
        oldprev=one([r for r in oldcpu[g-1] if r['op']==3],'reveal')
        oldreveal=one(oldseal,'reveal')
        wire=sum(e['bytes'] if e['event']=='SPI' else 8 for e in events
                 if e['generation']==g and e['event'] in ('SPI','observer'))
        watched[g]=dict(DMA_before=before,DMA_after=after,
            old_interval_ms=ms(oldreveal['clock']-oldprev['clock']),interval_ms=ms(reveal['clock']-prev['clock']),
            old_interval_VB=oldreveal['frame']-oldprev['frame'],interval_VB=reveal['frame']-prev['frame'],
            final_waits=sum(r['event']=='wait169' and r['clock']>=final['clock'] for r in seal),
            ACK_absolute_change_ms=ms(last['clock']-one(oldseal,'ack')['clock']),SPI_B=wire,
            terminal_before=terminal(baseline,g),terminal_after=terminal(path,g))
    return dict(phase=i,firmware_B=a.firmware.stat().st_size,firmware=sha(a.firmware),client=sha(a.client/'sink165.sfc'),
        dense_VB=candidate['dense_VB'],dense_ms=candidate['dense_ms'],old_dense_ms=old['dense_ms'],old_dense_VB=old['dense_VB'],
        last_ACK=candidate['last_ACK'],last_ACK_change_vs609_ms=ms(candidate['last_ACK']-old['last_ACK']),
        last_ACK_change_vs608_ms=ms(candidate['last_ACK']-palette['last_ACK']),
        last_ACK_change_vs577_ms=-metric['last_ACK_gain_ms'],after_first_two=candidate['after_first_two'],
        old_after_first_two=old_intervals,
        occupancy=occupancy,OBJ_hits=hits,qualified_ROM_reads=candidate['ROM_reads']-hits,
        min_bank_reuse_ms=ms(min(reuse)),max_bulk=joint['max_bulk_banks'],
        SPI_B=candidate['SPI_B'],ARM_instructions=candidate['ARM_instructions'],IRQ=candidate['IRQ'],
        DMA_B=candidate['DMA_B'],watched=watched,pins=candidate['pins'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prefix',default='nes-pace610-phase')
    p.add_argument('--map-only',action='store_true')
    p.add_argument('--bulk-map',action='store_true')
    for n in ('traces','plans','calendar','firmware','client','reference','replacement','simulation','guards','samples','report'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    # Supply549 logs 952 before the dispatcher; Obj518 logs 954 after it.
    # The original records are retained. Charge the same real one-clock BG
    # dispatch in Calendar.select and compare its grant/response exactly.
    a.request_log_offsets={952:1}
    ref=read(a.reference/'result.json');rep=read(a.replacement/'result.json');sim=read(a.simulation/'result.json')
    for folder,r in ((a.reference,ref),(a.replacement,rep)):
        pin(folder/'region.map.rpt',r['report'])
        for name,h in r['inputs'].items():pin(folder/name,h)
    assert sim['inputs']==rep['inputs']
    pin(a.simulation/'sim.log',sim['log']);pin(ROOT/'tools/nes_source_replace610_tb.sv',sim['testbench'])
    for n in ('nes_chr_cache610.sv','nes_obj_capture609.sv'):pin(ROOT/'rtl'/n,rep['inputs'][n])
    guards=read(a.guards);pin(a.firmware,guards['firmware'])
    lost=removed_line_hits(a.samples);calendar=Calendar(a.calendar)
    lost['baseline_first_BG_waits']=[]
    for i in (1,2):
        obj=read(a.traces/f'nes-obj609-phase{i}'/'obj-phases.json')
        for g in lost['by_generation']:
            t=obj[str(g)]['first_BG561'];grant,response=calendar.select(t)
            lost['baseline_first_BG_waits'].append(dict(phase=i,generation=g,
                wait_ms=ms(grant-t),response_ms=ms(response-t)))
    phases=[compare(a,i) for i in (1,2)]
    assert a.firmware.stat().st_size<=212992
    schedule_gate=all(p['dense_VB']<p['old_dense_VB'] and p['dense_ms']<p['old_dense_ms'] and
        p['last_ACK_change_vs609_ms']<0 and p['watched'][957]['final_waits']==0 and
        p['watched'][952]['interval_VB']<p['watched'][952]['old_interval_VB'] and
        p['watched'][952]['DMA_after']['early_B']>p['watched'][952]['DMA_before']['early_B'] for p in phases)
    report=dict(stage=610,phases=phases,source_reference=ref,source_replacement=rep,
        delta={k:rep[k]-ref[k] for k in ('LE','comb','FF','bits')},source_simulation=sim,ARM_guards=guards,
        prior_board_margin_LE=148,arithmetic_remaining_LE=148-(rep['LE']-ref['LE']),
        whole_board_FIT=False,physical=False,legacy_single_line_hits_removed=48,
        removed_cache_hits=lost,
        ARM_schedule_gate=schedule_gate,selected_for_hardware=False,
        remaining_gates=['Preserve or fairly time the 48 legacy BG hits',
                         'Bind actual board capture/lifecycle ports within 319LE and zero additional M9K',
                         'Whole Lite FIT/STA and retained STOP/menu recovery boundary'],
        limitation='The common timeline charges qualified service for every non-capture hit; old one-line hits are not timed in this model. The 601 replay counted 48 such hits, none on 952/954.')
    a.report.write_text(json.dumps(report,indent=2)+'\n')
