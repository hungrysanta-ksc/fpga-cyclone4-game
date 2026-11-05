"""Bind current PPU strobes, 608 deadlines, ownership and 53 displayed frames."""
import argparse
import json
from pathlib import Path
from collections import Counter
from bisect import bisect_right

from analyze_nes_phase537 import Calendar, ROOT, csv_groups, ms, one, read, sha
from budget_nes_planner607 import phase
from check_nes_wire600 import pin
from test_nes_obj609 import lanes

CAPTURE=240*341*4
WATCH=(952,954)


def strobe(a,g):
    manifest=read(a.geometry/'result.json')
    pin(a.geometry/'result.json',read(ROOT/'analysis/geometry230-verification.json')['stimulus_result_sha256'])
    path=a.geometry/f'frame{g}.hex'
    pin(path,next(r for r in manifest['frames'] if r['frame']==g)['stimulus_sha256'])
    result=[]
    for dot,line in enumerate(path.read_bytes().splitlines()):
        word=int(line,16)
        if (word>>54)&3==3 and ((word>>49)&15) in (4,8):
            result.append((dot,word&131071))
    return result


def physical_set(a,g,slots):
    plans=[bytes.fromhex(h) for _,h in read(a.plans/f'frame{g}/plans.json')]
    return {address for q in plans if q[6]==1 and int.from_bytes(q[2:4],'little') in slots
            for _,address in lanes(q)}

def dma_split(folder,g):
    rows=csv_groups(folder/'window.csv')[g]
    seals=csv_groups(folder/'seal528.csv')[g]
    packet=[r for r in rows if r['op']==3]
    head=one(packet,'load');final=one(packet,'final212');reveal=one(packet,'reveal')
    early=[r for r in rows if r['event']=='ppu_dma' and r['clock']<head['clock']]
    late=[r for r in seals if r['event']=='dma' and r['clock']<final['clock']]
    return dict(early_B=sum(r['value'] for r in early),early_count=len(early),
        SEAL_B=sum(r['bytes'] for r in late),SEAL_count=len(late),
        SEAL_line=head['line'],final_line=final['line'],
        SEAL_to_final_ms=ms(final['clock']-head['clock']),
        final_to_reveal_ms=ms(reveal['clock']-final['clock']),
        remaining_credit_B=one(seals,'final_credit')['bytes'])


def phase_budget(a,i,stim,sim,ref):
    # 607 phase() checks real ARM/client hashes, all displays/DMA/ACK and periodic BG grants.
    verified=phase(a,i,'nes-obj609-phase')
    base=ref['phases'][i-1]['candidate']
    prior=a.traces/f'nes-quiet608-palette{i}'
    for name,h in base['pins'].items():pin(prior/name,h)
    run=a.traces/f'nes-obj609-phase{i}';obj=read(run/'obj-phases.json')
    events=read(run/'events.json');cpu=csv_groups(run/'window.csv')
    joint=read(run/'joint.json')
    assert joint['max_bulk_banks']==2
    calendar=Calendar(a.calendar)
    source={e['generation']:e for e in events if e['event']=='source_begin'}
    assert set(source)==set(range(905,958))
    all_obj=hits=overlap=0; watched={};min_reuse=None
    evidence=ref['phases'][i-1]['traces']['recent607']['frames']
    for g in range(905,958):
        d=obj[str(g)];queries=d.get('OBJ609',[])
        ready=source[g]['capture_ready']
        previous=one([r for r in cpu[g-1] if r['op']==3],'reveal')['clock'] if g>905 else ready
        final=one([r for r in cpu[g] if r['op']==3],'ack')['clock']
        assert final<=d['ea']
        if g+2 in source:
            reuse=source[g+2]['capture_ready']-CAPTURE-d['ea']
            assert reuse>=0
            min_reuse=reuse if min_reuse is None else min(min_reuse,reuse)
        generation_overlap=0
        for slot,addr,t,r,hit in queries:
            assert ready<=t<r<=final
            if hit:assert r==t+8
            else:assert calendar.select(t+8)[1]==r
            if g+1 in source:
                end=source[g+1]['capture_ready']
                if t<end and r>end-CAPTURE:generation_overlap+=1
        all_obj+=len(queries);hits+=sum(q[-1] for q in queries);overlap+=generation_overlap
        if g not in WATCH:continue
        old=evidence[str(g)]['deadline']
        addrs=physical_set(a,g,{s['slot'] for s in old['late_slots']})
        assert len(addrs)==96
        late=[q for q in queries if q[1] in addrs]
        assert len(late)==96 and all(q[-1] for q in late)
        first={};cache={};unresolved=set(addrs);stable=None
        for dot,addr in stim[g]:
            tag=addr//16;ix=tag%128
            if ix not in cache or cache[ix][0]!=tag:
                if ix in cache:unresolved.update(cache[ix][1]&addrs)
                cache[ix]=(tag,set())
            cache[ix][1].add(addr)
            if addr in addrs:
                first.setdefault(addr,dot);unresolved.discard(addr)
            if unresolved:stable=None
            elif stable is None:stable=dot+1
        assert len(first)==96 and stable is not None and stable*4<CAPTURE
        oldb=base['watched'][str(g)]
        new=verified['candidate']['watched'][g]
        # Resolve addresses again against the actual producer output; cache collisions must be misses.
        for _,addr,_,_,hit in queries:
            entry=cache.get((addr//16)%128)
            assert bool(hit)==bool(entry and entry[0]==addr//16 and addr in entry[1])
        fresh_last=ms(max(q[3] for q in late)-previous)
        watched[g]=dict(OBJ_reads=len(queries),hits=sum(q[-1] for q in queries),late_distinct=len(addrs),
            late_hits=len(late),stable_after_capture_ms=ms(stable*4),
            held_before_first_query_ms=ms(min(q[2] for q in late)-(ready-CAPTURE+4*stable)),
            previous_display_to_last_late_ms=fresh_last,
            target_margin_ms=old['ten_ms_earlier_ms']-fresh_last,
            capture_overlap_queries=generation_overlap,
            vs_palette608={k:new[k]-oldb[k] for k in ('last_OBJ_after_previous_reveal_ms',
                'last_payload_after_previous_reveal_ms','transaction_B','interval_ms','interval_VB')},
            vs_MMC577_wire_B=new['transaction_B']-verified['control']['watched'][g]['transaction_B'],
            display_interval_ms=new['interval_ms'],display_interval_VB=new['interval_VB'],final_waits=new['final_waits'],
            SPI_B=new['transaction_B'],SPI_by_op=new['wire_by_op'],first_BG_wait_ms=new['BG_wait_ms'],
            SEAL_after_previous_reveal_ms=new['last_payload_after_previous_reveal_ms'],
            SEAL_to_reveal_ms=new['interval_ms']-new['last_payload_after_previous_reveal_ms'],
            DMA_before=dma_split(prior,g),DMA_after=dma_split(run,g))
    assert (all_obj,hits)==(sim['queries'],sim['hits'])
    curr=verified['candidate'];load=Counter()
    pushes=[json.loads(line)[1] for line in (run/'packets.jsonl').read_text().splitlines()]
    retired=sorted(row['clock'] for rows in cpu.values() for row in rows if row['event']=='ack')
    for q in events:
        if q.get('opcode')=='0xe0':
            b=bytes.fromhex(q['reply']);used=int.from_bytes(b[3:5],'big')-int.from_bytes(b[5:7],'big')
            sent=int.from_bytes(b[3:5],'big')
            assert (sent,sent-used)==(bisect_right(pushes,q['start']),bisect_right(retired,q['start']))
            assert 0<=used<=4;load[used]+=1
    return dict(phase=i,firmware=joint['firmware_SHA256'],client=joint['client_SHA256'],
        captures=53,working_ROM_demands=curr['ROM_reads'],qualified_ROM_reads=curr['ROM_reads']-hits,
        OBJ_reads=all_obj,OBJ_hits=hits,overlap_queries=overlap,
        min_bank_reuse_margin_ms=ms(min_reuse),E0_outstanding_counts=load,
        max_bulk=joint['max_bulk_banks'],watched=watched,final_wait957=curr['watched'][957]['final_waits'],
        dense_VB=curr['dense_VB'],dense_ms=curr['dense_ms'],baseline_dense_ms=base['dense_ms'],
        dense_frames=curr['dense_frames'],last_ACK=curr['last_ACK'],
        last_ACK_change_ms=ms(curr['last_ACK']-base['last_ACK']),last_ACK_vs_MMC577_ms=-verified['last_ACK_gain_ms'],
        wire_change_vs_palette608_B=sum(curr['SPI_B'].values())-sum(base['SPI_B'].values()),
        SPI_B=curr['SPI_B'],IRQ=curr['IRQ'],ARM_instructions=curr['ARM_instructions'],DMA_B=curr['DMA_B'],pins=curr['pins'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','calendar','geometry','firmware','client','plans','simulation','mapped','reference_map','report'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    ref=read(ROOT/'analysis/quiet608-palette.json')
    pin(a.firmware,ref['ARM']);pin(a.client/'sink165.sfc',ref['client'])
    sim=read(a.simulation/'result.json');mapped=read(a.mapped/'result.json')
    pin(a.simulation/'sim.log',sim['log']);pin(a.mapped/'region.map.rpt',mapped['report'])
    pin(ROOT/'rtl/nes_obj_capture609.sv',mapped['RTL']);assert sim['RTL']==mapped['RTL']
    stimuli={g:strobe(a,g) for g in range(905,958)}
    active=[rows for rows in stimuli.values() if rows]
    first_sample=min(rows[0][0] for rows in active)
    last_sample=max(rows[-1][0] for rows in active)
    min_gap=min(t1-t0 for rows in active for (t0,_),(t1,_) in zip(rows,rows[1:]))
    assert first_sample>128 and (last_sample+1)*4<CAPTURE and min_gap>=2
    assert sum(map(len,active))==sim['fills']
    stim={g:stimuli[g] for g in WATCH}
    reference_map=read(a.reference_map/'result.json')
    pin(a.reference_map/'region.map.rpt',reference_map['report'])
    report=dict(stage=609,phases=[phase_budget(a,i,stim,sim,ref) for i in (1,2)],simulation=sim,
        standalone_MAP=mapped,separate_read_MAP=reference_map,
        capture=dict(first_OBJ_dot=first_sample,last_OBJ_dot=last_sample,min_spacing_dots=min_gap),
        harness_sha256={name:sha(ROOT/'tools'/name) for name in
            ('test_nes_obj609.py','test_nes_quiet608.py','test_nes_close561.py',
             'test_nes_raw506_joint.py','test_nes_banks557.py','test_nes_service509_schedule.py')},
        cold905='Input capture already sealed at model entry.',physical=False,whole_board_FIT=False)
    a.report.write_text(json.dumps(report,indent=2)+'\n')
