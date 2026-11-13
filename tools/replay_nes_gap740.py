# SPDX-License-Identifier: MIT
"""Keep all eight 957 map offers fixed and retime the measured OBJ/OAM transaction group."""
import argparse
import csv
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
import trace_nes_owner739 as owner
from analyze_nes_owner739 import packets, read, sha
from nes_raw506 import once
from analyze_nes_game215 import crc8


def schedule(trace, phase, policy):
    reference = read(Path(__file__).resolve().parents[1]/'analysis/owner739-verification.json')['phases'][str(phase)]['ref']
    for name in ('events.json','packets.jsonl','window.csv'):
        assert sha(trace/name)==reference['input_sha256'][name],name
    times = reference['ticks']
    events = [e for e in read(trace/'events.json') if e['generation']==957 and e['event']=='SPI']
    heads = packets(trace)[957]
    maps = [t for h,_,t in heads if h[1]==2 and 2048<=int.from_bytes(h[10:12],'little')<=3392]
    assert len(maps)==8 and maps==sorted(maps)
    last_map = maps[-1]
    obj = next(t for h,_,t in heads if h[:2]==bytes((7,1)) and int.from_bytes(h[10:12],'little')==2720)
    oam = next(t for h,_,t in heads if h[:2]==bytes((9,4)))
    assert obj==times['OBJ_enqueued'] and last_map<times['last_map_ACK']<obj<oam
    # Preserve the measured E0-to-E8 dispatch gap, full E8/credit/E1 wire
    # and CPU work. Replace only the waits between the selected E0 and E8.
    prior = max(e['clock'] for e in events if e['clock']<=times['query_start'])
    boundary = last_map if policy in ('issued','checked','first','both') else times['last_map_ACK']
    grant = next(e for e in events if e['opcode']=='0xe0' and e['start']>=boundary)
    assert times['previous_BG_token']<grant['start']
    shift = round(prior-grant['clock'])
    query_start=times['query_start']-shift
    extra={}
    if policy in ('checked','first','both'):
        # Start E8 after the first post-E1 status. Use the recorded E0 which
        # proves actual map retirement, followed by its bounded D0 service.
        # Restore the observed dispatch into E1 after that service.
        receipt=next(e for e in events if e['opcode']=='0xe0' and e['start']>=times['last_map_ACK'])
        status=bytes.fromhex(receipt['reply'])
        assert status[1]==0xf7 and crc8(status[1:19])==status[19]
        assert status[3:5]==status[5:7] and status[2]==2
        header=next(h for h,_,t in heads if t==last_map)
        assert status[7:17]==bytes([0])+header[:1]+header[2:10] and status[17:19]==bytes((0x65,0x9a))
        service=next(e for e in events if e['start']>=receipt['clock'] and e['opcode']=='0xd0')
        observed=next(e for e in events if e['opcode']=='0xe0' and e['clock']>times['descriptor_checked'])
        assert query_start+(observed['start']-times['query_start'])<=receipt['start']
        shift=round(observed['clock']-service['clock'])
        extra=dict(map_receipt=receipt,input_service=service)
    if policy in ('first','both'):
        # These are conditional producer schedules. The first pulse is visible
        # on the existing E0 bit; the second is an oracle if that bit stays set.
        marker=trace.parent/f'nes-gap740-checked{phase}-pulses'/'progress740.csv'
        with marker.open() as f:
            pulses=[int(r['clock']) for r in csv.DictReader(f)]
        assert len(pulses)==2
        assert sha(marker.parent/'window.csv')==sha(trace.parent/f'nes-gap740-checked{phase}-trace'/'window.csv')
        pulse=pulses[0 if policy=='first' else 1]
        scroll=next(t for h,_,t in heads if h[1]==5)
        e8=max((e for e in events if e['opcode']=='0xe8' and e['clock']<scroll),key=lambda e:e['clock'])
        confirmed=max((e for e in events if e['opcode']=='0xe0' and e['clock']<e8['start']),key=lambda e:e['clock'])
        # Include one complete E0, dispatch, the empty E8 and the scroll E1.
        # Pin all later inter-packet spacings, including the final SEAL.
        shift_tail=round(confirmed['start']-pulse)
        extra.update(scroll=scroll,pulse=pulse,tail_shift=shift_tail,
                     callback_masterclocks=scroll-confirmed['start'])
    assert shift>0 and last_map<obj-shift
    return dict(first=obj,last=obj if policy=='obj' else oam,shift=shift,map_offers=maps,
                query_start=query_start,grant=grant,policy=policy,phase=phase,**extra)


def run(a):
    if not a.out.resolve().as_posix().isascii():
        raise ValueError('Mesen Lua trace output needs an ASCII path (use the replay temp folder)')
    plan=schedule(a.trace,a.phase,a.policy)
    original=replay.run
    def retimed(args, *, edit_script=None):
        def edit(script):
            script=edit_script(script)
            script=once(script,'local function loaded()', '''local started740=false
local progress740=assert(io.open(ROOT..'/progress740.csv','w'))
progress740:write('clock\\n')
checkedMem527(function(_,value)
 if started740 and value==0xa5 then
  progress740:write(tostring(emu.getState().masterClock)..'\\n');progress740:flush()
 end
end,emu.callbackType.write,0x601d)
local function loaded()''')
            script=once(script,' if pw(8)==957 then active739=true end',
                                  ' if pw(8)==957 and pb(0)==9 then started740=true end\n if pw(8)==957 then active739=true end')
            path=args.out/'arrivals.tsv'
            rows=[]
            changed=[]
            previous=0
            for line in path.read_text().splitlines():
                t,head,payload=line.split('\t')
                clock=int(t)
                if plan['first']<=clock<=plan['last']:
                    assert bytes.fromhex(head)[:2] in (bytes((7,1)),bytes((9,4)))
                    changed.append(clock)
                    clock-=plan['shift']
                elif 'scroll' in plan and clock>=plan['scroll']:
                    clock-=plan['tail_shift']
                assert clock>=previous
                previous=clock
                rows.append(f'{clock}\t{head}\t{payload}')
            assert changed==sorted({plan['first'],plan['last']})
            path.write_text('\n'.join(rows)+'\n',newline='\n')
            (args.out/'schedule.json').write_text(json.dumps(plan,indent=2)+'\n')
            return script
        def compare(old,new):
            assert [r for r in old if int(r['g'])<957]==[r for r in new if int(r['g'])<957]
            for event in ('load','ack','reveal'):
                def identities(rows):
                    return [tuple(r[k] for k in ('g','index','op','section','value'))
                            for r in rows if r['event']==event]
                assert identities(old)==identities(new),event
            return dict(prefix_events=sum(int(r['g'])<957 for r in old))
        original(args,edit_script=edit,compare_trace=compare)
    with patch.object(replay,'run',retimed):
        owner.run(a)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('trace','out','mesen','client'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--phase',type=int,choices=(1,2),required=True)
    parser.add_argument('--policy',choices=('obj','pair','issued','checked','first','both'),required=True)
    parser.add_argument('--mode',choices=('trace','stop','stale'),default='trace')
    run(parser.parse_args())
