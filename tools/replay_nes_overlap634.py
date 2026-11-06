# SPDX-License-Identifier: MIT
"""Fit complete 951 RX blocks between 950 status samples, then replay unchanged output work."""
import argparse
from pathlib import Path
from statistics import median

from analyze_nes_map628 import csv_groups, ms, one, read, sha
import replay_nes_bank633 as bank
from nes_raw506 import once


def ledger(trace, policy):
    events=read(trace/'events.json')
    prev=[e for e in events if e['generation']==950]
    curr=[e for e in events if e['generation']==951]
    cpu=csv_groups(trace/'window.csv')
    prior=[e for e in cpu[950] if e['op']==3]
    ack=one(prior,'ack')['clock']
    ea=prev[-1]['clock']
    source=one(curr,'source_begin')
    assert prev[-1]['opcode']=='0xea' and source['clock']==ea
    seal=next(e for e in prev if e.get('packet_opcode')==3)
    tail=[e for e in prev if e['clock']>seal['clock']]
    polls=[e for e in tail if e.get('opcode')=='0xe0']
    # Preserve every changed reply, the final negative and the positive.
    assert all(e['reply']==polls[0]['reply'] for e in polls[:-1])
    assert polls[-1]['reply']!=polls[0]['reply'] and polls[-2]['start']<ack<=polls[-1]['start']
    assert {e.get('opcode') for e in tail if e['event']=='SPI'}=={'0xe0','0xe8','0xea'}
    obs=[e for e in tail if e['event']=='observer']
    # Retain all samples bordering observer work or a 100 Hz tick. This also
    # leaves the traced observer/IRQ slot free when coalescing identical polls.
    boundaries=[e['clock'] for e in obs]
    tick=21477272/100
    boundaries += [k*tick for k in range(int(seal['clock']/tick)+1,int(ea/tick)+1)]
    protected={0,len(polls)-2,len(polls)-1}
    for t in boundaries:
        for ix in range(len(polls)-1):
            if polls[ix]['start']<=t<=polls[ix+1]['start']:
                protected.update((ix,ix+1))
    spi=[e for e in curr if e['event']=='SPI']
    assert spi[0]['opcode']=='0xe8'
    blocks=[]
    for i in range(2,len(spi)-2,3):
        group=spi[i:i+3]
        if [e['opcode'] for e in group]!=['0xd1','0xd2','0xd0']:
            break
        # poll() returns after the token+1 D0 confirmation, whose positive
        # status can seed the next poll. Only the first block needs an entry D0.
        if not blocks:
            assert spi[i-1]['opcode']=='0xd0'
            group=[spi[i-1]]+group
        blocks.append(group)
    ix=0
    scheduled=[]
    kept=set(protected)
    skipped=set()
    gap_max=max(b['start']-a['clock'] for a,b in zip(polls,polls[1:]))
    first_d1=next(e for e in blocks[0] if e['opcode']=='0xd1')
    assert first_d1['clock']-first_d1['start']>gap_max
    for n,group in enumerate(blocks):
        start=spi[0]['clock'] if n==0 else blocks[n-1][-1]['clock']
        duration=group[-1]['clock']-start
        wire=sum(e['clock']-e['start'] for e in group)
        # Buffered candidate is charged only saved SPI occupancy on the new
        # critical path; restoring data/copying it is not assumed to be free in production.
        while ix<len(polls)-2:
            begin=polls[ix]['clock']
            end=begin+duration
            following=next((j for j in range(ix+1,len(polls)) if polls[j]['start']>=end),len(polls))
            if (begin>=source['capture_ready'] and following<=len(polls)-2 and
                not any(ix<j<following for j in protected) and not any(begin<=t<=end for t in boundaries)):
                break
            kept.add(ix)
            ix+=1
        else:
            break
        kept.update((ix,following));skipped.update(range(ix+1,following))
        scheduled.append(dict(n=n+1,start=begin,end=end,source_start=start,source_end=group[-1]['clock'],
                              spi_clocks=wire,buffer_B=next(e['bytes'] for e in group if e['opcode']=='0xd1')-3))
        ix=following
    assert scheduled and not kept.intersection(skipped)
    kept=sorted(set(range(len(polls)))-skipped)
    intervals=[(polls[x]['start'],polls[y]['start']) for x,y in zip(kept,kept[1:])]
    shift={'fixed':0,'buffer':sum(r['spi_clocks'] for r in scheduled),
           'restore':sum(r['source_end']-r['source_start'] for r in scheduled)}[policy]
    phase=read(trace/'obj-phases.json')['951']['cache611']
    assert len(phase)==96 and all(r[0]==1 and r[5]=='OBJ_capture' for r in phase)
    nextsrc=next(e for e in events if e['generation']==952 and e['event']=='source_begin')
    # Both capture banks must remain available for this diagnostic. Baseline
    # launches 952 capture on 951 input commit (which would also advance).
    following=next(e for e in events if e['generation']==953 and e['event']=='source_begin')
    old_phase=read(trace/'obj-phases.json')['950']
    assert max(source['capture_ready'],old_phase['end_accepted'],max(r[4] for r in old_phase['cache611']))<scheduled[0]['start']
    assert scheduled[-1]['end']<ack<ea
    assert source['capture_ready']<min(r[2] for r in phase)-shift
    return dict(policy=policy,ea=ea,ack=ack,show=one(prior,'reveal')['clock'],
                last_dma=max(r['clock'] for r in prior if r['event']=='ppu_last'),capture_ready=source['capture_ready'],
                seal_push=seal['clock'],first_D1_ms=ms(first_d1['clock']-first_d1['start']),
                max_fixed_gap_ms=ms(gap_max),shift=round(shift),scheduled=scheduled,
                omitted_original_polls=len(skipped),scheduled_poll_count=len(intervals)+1,max_poll_interval_ms=ms(max(y-x for x,y in intervals)),
                bytes=sum(r['buffer_B'] for r in scheduled),
                planner=one(curr,'planner_enter')['clock'],first_map=next(e['clock'] for e in curr if e.get('packet_opcode')==2),
                bg_frozen=one(curr,'bg_map_frozen')['clock'],first_plan=next(e['clock'] for e in spi if e['opcode']=='0xe9'),
                rom_kind='96 OBJ capture hits',last_obj=phase[-1][4],capture952_ready_recorded=nextsrc['capture_ready'],
                capture953_ready_recorded=following['capture_ready'])


def run(a):
    meta=ledger(a.trace,a.policy)
    base_schedule=bank.schedule
    def schedule(commands,pushes,mode):
        kept,removed,cost=base_schedule(commands,pushes,mode)
        offers=[(t-meta['shift'],h,b) for t,h,b in kept]
        assert offers[0][0]>meta['ea']
        return offers,removed,cost
    def guard_feedback(script):
        # Reissue a delayed recorded E0 on the measured poll cadence. Each
        # answer used by the original ARM requires a real 65816 retirement.
        events=[e for e in read(a.trace/'events.json') if e['generation']==951 and e['event']=='SPI']
        pending=[]
        gates={}
        seq=0
        last_offer=0
        saved=0
        omissions={13,14,15,16,18,19} if a.mode=='collapse' else set()
        first_retired=int.from_bytes(bytes.fromhex(next(e for e in events if e['opcode']=='0xe0')['reply'])[5:7],'big')
        baseline=csv_groups(a.trace/'window.csv')[951]
        assert first_retired==min(r['index'] for r in baseline if r['event']=='load')-1
        for e in events:
            if e['opcode']=='0xe0':
                count=int.from_bytes(bytes.fromhex(e['reply'])[5:7],'big')-first_retired
                assert 0<=count<=seq
                needed=first_retired+count-sum(i<count for i in omissions)
                pending.append((needed,round(e['start'])-meta['shift']-saved))
            elif e['opcode']=='0xe1':
                t=round(e['clock'])
                if seq in omissions:
                    saved+=t-last_offer
                else:
                    index=first_retired+seq+1-sum(i<seq for i in omissions)
                    gates[index]=pending
                pending=[];seq+=1;last_offer=t
        assert seq==30
        entries=[f"[{idx}]={{"+','.join('{%d,%d}'%row for row in items)+'}' for idx,items in gates.items()]
        poll=round(median([y['start']-x['start'] for x,y in zip(events,events[1:])
                           if x['opcode']==y['opcode']=='0xe0' and 5200<y['start']-x['start']<6800]))
        prefix="local gates634={"+','.join(entries)+"}\nlocal step634=1;local delay634=0\n"
        script=once(script,'local finished522=false',prefix+'local finished522=false')
        # FINISH remains pending behind the delayed last PUSH.
        script=once(script,'while now>=target522 do',f"""while now>=target522+delay634 do
  local gates=gates634[sent+1]
  if gates then
   while step634<=#gates do
    local g=gates[step634];local t=retiredAt[g[1]]
    if not t then return end
    local due=g[2]+delay634
    if t>due then delay634=delay634+math.ceil((t-due)/{poll})*{poll} end
    step634=step634+1
   end
   if now<target522+delay634 then return end
  end""")
        script=once(script,'  sent=sent+1','  step634=1;sent=sent+1')
        return once(script,'sent,target522,now,sent-retired','sent,target522+delay634,now,sent-retired')
    bank.run(a,schedule_offers=schedule,edit_after=guard_feedback if a.feedback else None,
             timing_metadata=dict(overlap=meta,feedback=a.feedback))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','client','out','mesen'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--mode',choices=('control','collapse'),required=True)
    p.add_argument('--policy',choices=('fixed','buffer','restore'),required=True)
    p.add_argument('--feedback',action='store_true')
    run(p.parse_args())
