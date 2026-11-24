"""Replay one ordinary E1 in the interval between generation 912 tokens 36 and 37."""
import argparse
import math
from pathlib import Path

from nes_credit1004 import PACKED, execute, ledger, once, read, replay
from test_nes_banks557 import crc

# IDs are from the pinned 978 trace. Only the first packet of an independent
# section can enter the gap. All variants have the same post-gap scheduler.
POLICIES = {'hold':0,'palette':185,'oam':190,'section':193,'precopy':193,'next_obj':184}


def run(temp,phase,policy,fault=None):
    ref,commands,jobs,events=ledger(temp,phase)
    selected=POLICIES[policy]
    head=jobs[8]
    next_tile=jobs[9]
    assert (head['token'],next_tile['token'])==(36,37)
    gate=next_tile['e8_start']
    snap=next(x for x in reversed(events) if x.get('opcode')=='0xe0' and x['clock']<=head['issue'])
    b=bytes.fromhex(snap['reply'])
    confirmed=int.from_bytes(b[5:7],'big')
    assert b[19]==crc(b[1:19],8,7,0) and int.from_bytes(b[3:5],'big')==confirmed==head['index']-1
    out=temp/(f'nes-gap1008-{policy}-p{phase}'+('-'+fault if fault else ''))

    def observe(script):
        # Replay the exact received bytes and enqueue clocks through token 36.
        path=out/'commands.txt'
        lines=path.read_text().splitlines()
        for j,cmd in zip(jobs[1:9],commands[-20:-12],strict=True):
            at=(j['index']-1)*5
            assert lines[at:at+4]==[str(j['index']),'0','EARLY',cmd[3]]
            lines[at+1:at+3]=[str(cmd[2]),'PUSH']
        path.write_text('\n'.join(lines)+'\n',encoding='ascii',newline='\n')
        script=once(script,'local issued1002=0', 'local issued1002=8\nfor i=1,8 do jobs1002[i].sent=true end')
        script=once(script,'local confirmed1002='+str(jobs[0]['index']-1),'local confirmed1002='+str(confirmed))
        for j in jobs[9:]:
            if 'assembled' in j:
                ready=j['assembled'] if policy!='precopy' else j['source']
                script=once(script,'id='+str(j['index'])+',op=',f'id={j["index"]},assembly={ready},op=')
        # When the gap closes use the recorded packet order among ready jobs.
        # The transfer may overlap 65816 service. Do not poll for nonexistent
        # second bank metadata until the first bank has physically returned.
        script=once(script,'local ready=true',f"""local ready=(now>={gate} or
            (j.id=={selected} and now+(j.token and j.poll or 0)+j.duration<={gate}))
        if j.assembly and now<j.assembly then ready=false end
        if j.token and not returns1002[j.token-1] then ready=false end
        j.rank=j.id""")
        script=once(script,'ready=release and now>=','ready=ready and release and now>=')
        return script

    execute(temp,phase,'control',fault,destination=out,observe=observe)


def fixed_window(policy,jobs,events):
    head=jobs[8]
    j=next(j for j in jobs if j['index']==POLICIES[policy])
    polls=[e for e in events if e.get('opcode')=='0xe0' and e['start']>=head['arrive']]
    if policy=='next_obj':
        receipt=next(e for e in polls if int.from_bytes(bytes.fromhex(e['reply'])[5:7],'big')==head['index'])
        data=bytes.fromhex(receipt['reply'])
        assert data[19]==crc(data[1:19],8,7,0) and data[7]==0 and data[15:17]==bytes((0x90,3))
        at=math.ceil(next(e['start'] for e in polls if e['start']>=receipt['clock']))
        return at,at+j['e8_cost']+j['issue']-j['e8_end']
    at=math.ceil(polls[0]['start'])
    return at,at


def fixed(temp,phase,policy,fault=None):
    """Move only one verified E1. Leave other wire times, including SEAL, fixed."""
    ref,commands,jobs,events=ledger(temp,phase)
    head=jobs[8]
    target=POLICIES[policy]
    order=list(range(len(jobs)))
    moved=None
    if target:
        pos=next(i for i,j in enumerate(jobs) if j['index']==target)
        job=jobs[pos]
        start,issue=fixed_window(policy,jobs,events)
        end=issue+job['duration']
        ready=job.get('producer',job.get('source',0))
        if policy!='precopy':
            ready=job.get('assembled',ready)
        if start>=ready:
            assert end<=jobs[9]['e8_start'] and all(e['opcode']=='0xe0' for e in events
                if 'start' in e and e['start']<end and e['clock']>start)
            order.remove(pos)
            order.insert(9,pos)
            moved=(pos,end)
    stream=commands[:-len(jobs)]
    for seq,original in enumerate(order):
        g,op,end,raw,bulk,seen,duration=commands[original-len(jobs)]
        header=bytearray.fromhex(raw)
        header[2:4]=seq.to_bytes(2,'little')
        if moved and original==moved[0]:
            end=moved[1]
        stream.append((g,op,end,header.hex(),bulk,seen,duration))
    pc=read(PACKED/'labels.json')['group_ready538']
    def monitor(lua):
        anchor='local sequence=0;'
        return once(lua,anchor,f"checkedMem527(function()sample516('group1002')end,emu.callbackType.exec,{pc})\n"+anchor)
    out=temp/(f'nes-gap1008-fixed-{policy}-p{phase}'+('-'+fault if fault else ''))
    replay(temp,ref,out,'fixed',stream,912,fault,observe=monitor)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('policies',nargs='+',choices=list(POLICIES))
    p.add_argument('--fixed',action='store_true')
    p.add_argument('--fault',choices=('stop_decode','bad_seal'))
    args=p.parse_args()
    for name in args.policies:
        (fixed if args.fixed else run)(args.temp,args.phase,name,args.fault)
