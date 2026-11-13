"""Price descriptor/receipt SPI on fixed 727 map arrivals and execute the 65816."""
import argparse
import json
from pathlib import Path
from analyze_nes_game215 import crc8
from analyze_nes_owner739 import packets, read
from replay_nes_beam741 import run
from nes_raw506 import once


def retime(folder, base, plan, policy, scroll_policy, pulse_folder=None, lead=0):
    heads=packets(base)[957]
    ref=read(Path('analysis/owner739-verification.json'))['phases'][str(plan['phase'])]['ref']['ticks']
    events=[e for e in read(base/'events.json') if e.get('generation')==957 and e['event']=='SPI']
    obj,oam,scroll=[next(t for h,_,t in heads if t==plan[k]) for k in ('first','last','scroll')]
    bulk=next(h for h,_,t in heads if t==obj)
    e8=next(e for e in events if e['opcode']=='0xe8' and abs(e['start']-ref['query_start'])<1)
    desc=bytes.fromhex(e8['reply'])
    assert desc[1:3]==bytes((0xd7,4)) and crc8(desc[1:19])==desc[19]
    assert desc[6:18]==bytes((1,1))+bulk[14:16]+bulk[10:12]+bulk[8:10]+bulk[16:20]
    receipt=plan['map_receipt']
    service=plan['input_service']
    offers=plan['map_offers']
    next_spi=lambda clock:next(e for e in events if e['start']>=clock)
    clocks=lambda e:e['clock']-e['start']
    orig_obj=next(e for e in events if e['opcode']=='0xe1' and abs(e['clock']-obj)<1)
    before=max((e for e in events if e['clock']<=orig_obj['start']),key=lambda e:e['clock'])
    assert before['opcode']=='0xe0'
    post_check=orig_obj['start']-before['clock']
    # Each poll pays the measured empty-loop dispatch including status CRC.
    poll=plan['grant']
    next_poll=next_spi(poll['clock'])
    assert next_poll['opcode']=='0xe0'
    gap=next_poll['start']-poll['clock']
    # Use the original OAM E1 -> E8 dispatch and service the input once.
    # Token 120 was already ready before the last map E1.
    assert ref['previous_BG_token']<offers[-1]
    first=offers[-1]+next_spi(oam)['start']-oam
    checks=[]
    done=first+clocks(e8)+(next_spi(e8['clock'])['start']-e8['clock'])
    done+=service['start']-receipt['clock']+clocks(service)
    sampling=done+next_spi(service['clock'])['start']-service['clock']
    reference_ack=ref['last_map_ACK']
    if policy=='floor':
        # 741 changes idle CPU cycles before the last map too. Use its
        # measured retirement while the pre-OBJ arrivals are still identical.
        reference_ack=read(Path('analysis/beam741-verification.json'))['phases'][str(plan['phase'])]['dynamic']['map_ACK']
        # Diagnostic lower bound: an oracle wakes the host at the actual ACK.
        sampling=max(sampling,reference_ack+1)
    while sampling<=reference_ack:
        checks.append(round(sampling))
        sampling+=clocks(receipt)+gap
    checks.append(round(sampling))
    push=round(sampling+clocks(receipt)+post_check+clocks(orig_obj))
    if lead:
        assert policy=='floor' and scroll_policy=='original'
        # Sensitivity only. This removes charged post-ACK work and must
        # never be counted as an implementable transaction schedule.
        push-=lead
    path=folder/'arrivals.tsv'
    pulse_shift=0
    if pulse_folder:
        assert scroll_policy=='first'
        pulse=int((pulse_folder/'pulse741.txt').read_text().splitlines()[0])
        pulse_shift=pulse-plan['pulse']
    rows=[]
    for line in path.read_text().splitlines():
        t,header,data=line.split('\t')
        t=int(t)
        if header!='FINISH':
            h=bytes.fromhex(header)
            if int.from_bytes(h[8:10],'little')==957:
                if h==bulk:
                    t=push
                elif h[:2]==bytes((9,4)):
                    t=push+oam-obj
        if t>=scroll-plan['tail_shift']:
            # The entire suffix is replayed at 727 clocks, so the late scroll
            # costs real SEAL latency and cannot get free earlier successors.
            t+=plan['tail_shift'] if scroll_policy=='original' else pulse_shift
        rows.append((t,header,data))
    assert all(a[0]<=b[0] for a,b in zip(rows,rows[1:]))
    path.write_text(''.join(f'{t}\t{h}\t{b}\n' for t,h,b in rows),newline='\n')
    (folder/'receipt742.json').write_text(json.dumps(dict(policy=policy,scroll=scroll_policy,
        hypothetical_lead_clocks=lead,descriptor_start=round(first),input_end=round(done),E0_starts=checks,
        stale_polls=len(checks)-1,last_map_ACK=reference_ack,OBJ_push=push,
        OBJ_after_map_ACK=push-reference_ack,post_check=post_check)))


def observe_bulk(script, client):
    check="pw(8)==957 and pb(1)==1 and #tile==288"
    script=once(script,"assert(tile,'unowned descriptor');local d=",
                "assert(tile,'unowned descriptor');if "+check+
                " then owner739('descriptor742',a) end;local d=")
    labels=read(client/'labels.json')
    hooks=[]
    for label in ('mark212','bits212','append212','append_new212','merge532'):
        hooks.append(f"checkedMem527(function() if tile and {check} then owner739('{label}',0) end end,emu.callbackType.exec,{labels[label]})")
    script=once(script,'local function loaded()','\n'.join(hooks)+'\nlocal function loaded()')
    return once(script,'reads=reads+1;return tile:byte(i+1)',
                "if "+check+" and (i==0 or i==1 or i==287) then owner739('bulk742',i) end;"+
                'reads=reads+1;return tile:byte(i+1)')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','out','client','mesen'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--phase',type=int,choices=(1,2),required=True)
    p.add_argument('--policy',choices=('poll','floor'),default='poll')
    p.add_argument('--scroll',choices=('first','original'),default='original')
    p.add_argument('--variant',choices=('control','budget'),default='budget')
    p.add_argument('--lead-clocks',type=int,choices=(0,1364,2728,4092),default=0)
    p.add_argument('--pulse-folder',type=Path)
    p.add_argument('--mode',choices=('trace','stale','stop'),default='trace')
    p.add_argument('--inject',choices=('none','before_bg','head'),default='none')
    p.set_defaults(calendar='first',lag_nops=0,feedback=None)
    a=p.parse_args()
    run(a,observe_script=lambda script:observe_bulk(script,a.client),adjust_arrivals=lambda f,b,s:retime(f,b,s,a.policy,a.scroll,a.pulse_folder,a.lead_clocks))
