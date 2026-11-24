"""Replay two output slots with charged E0 snapshots, separate tile and SEAL reservations."""
import argparse
import math
from pathlib import Path

from nes_overlap1002 import PACKED, ledger, once, read, replay, run
from test_nes_banks557 import crc

# The arbiter only learns a retirement by paying for a status transfer. Charge
# at the measured worst E0 duration and sample at its start (conservative).
ARBITER = """
  if operation=='EARLY' then
   if not inflight then
    if snapshot1004 then
     confirmed1002=snapshot1004
     snapshot1004=nil
    end
    while busy[block] and now>=busy[block][2] do block=block+1 end
    local horizon=busy[block] and busy[block][1] or math.huge
    local available=2-(sent-confirmed1002)
    assert(available>=0 and available<=2)
    local picked,span,poll=nil,0,0
    local waiting=false
    for i,j in ipairs(jobs1002) do
     if not j.sent and (not j.prev or jobs1002[j.prev].sent) and now>=j.ready
        and (j.op~=3 or issued1002==#jobs1002-1) then
      local ready=true
      if j.token and j.token>=33 then
       local release=returns1002[j.token-2]
       ready=release and now>=math.max(j.producer,release+j.fill)
      end
      local query=j.token and j.poll or 0
      local need=1
      if RESERVE_TILE and tiles1004>=RESERVE_FROM and tiles1004<8 and not j.token then need=2 end
      if RESERVE_SEAL and issued1002==#jobs1002-2 then need=2 end
      if ready then
       if available<need then waiting=true
       elseif now+query+j.duration<=horizon and (not picked or j.rank<jobs1002[picked].rank) then
        picked,span,poll=i,query+j.duration,query
       end
      end
     end
    end
    if not picked then
     if waiting and now+E0_COST<=horizon then
      snapshot1004=retired
      status1004:write(now,' ',sent,' ',confirmed1002,' ',retired,'\\n');status1004:flush()
      target=now+E0_COST
     end
     break
    end
    local j=jobs1002[picked]
    if j.token then tiles1004=tiles1004+1 end
    local bytes=unhex(j.hex)
    args={hex(bytes:sub(1,2)..string.pack('<I2',issued1002+1)..bytes:sub(5)),j.bulk}
    issued1002=issued1002+1;j.sent=true
    starts:write(j.id,' ',now+poll,' ',now+span,' ',sent-retired,' ',poll,' ',available,'\\n');starts:flush()
    target=now+span;inflight=true;break
   end
   inflight=false;operation='PUSH'
  end
"""


def seal_credit(events,jobs):
    table,seal=jobs[-2:]
    assert (table['section'],table['offset'],seal['op'])==(5,1322,3)
    polls=[e for e in events if e.get('generation')==912 and e.get('opcode')=='0xe0']
    def before(issue):
        event=next(e for e in reversed(polls) if e['clock']<=issue)
        b=bytes.fromhex(event['reply'])
        assert len(b)==20 and b[1]==247 and crc(b[1:19],8,7,0)==b[19]
        sent,retired=int.from_bytes(b[3:5],'big'),int.from_bytes(b[5:7],'big')
        assert not b[2]&0xf0 and 0<=sent-retired<=4
        return dict(sent=sent,retired=retired,clock=event['clock'],start=event['start'])
    old=before(table['issue'])
    new=before(seal['issue'])
    assert old['sent']==table['index']-1 and seal['index']-1-old['retired']==4
    assert new['sent']==seal['index']-1 and new['sent']-new['retired']<4
    return old,new


def original_order(temp,phase):
    # Best case after the last required, CRC-valid E0. Keep all earlier E1,
    # E8, D1 and D2 transfers fixed; zero the ARM's post-E0 dispatch cost.
    ref,commands,jobs,events=ledger(temp,phase)
    _,new=seal_credit(events,jobs)
    g,op,arrival,wire,bulk,ready,cost=commands[-1]
    start=math.ceil(new['clock'])
    end=start+cost
    assert end<arrival and not any(e['start']<end and e['clock']>start
        for e in events if 'start' in e and e.get('opcode')!='0xe1')
    commands[-1]=(g,op,end,wire,bulk,ready,cost)
    out=temp/f'nes-credit1004-fixed-p{phase}'
    pc=read(PACKED/'labels.json')['group_ready538']
    def instrument(lua):
        anchor='local sequence=0;'
        return once(lua,anchor,f"checkedMem527(function()sample516('group1002')end,emu.callbackType.exec,{pc})\n"+anchor)
    replay(temp,ref,out,'fixed',commands,912,observe=instrument)


def execute(temp, phase, policy, fault):
    _, _, jobs, events=ledger(temp,phase)
    tokens=[j['token'] for j in jobs if 'token' in j]
    assert tokens==list(range(31,39))
    e0=max(math.ceil(e['clock']-e['start']) for e in events
           if e.get('generation')==912 and e.get('opcode')=='0xe0')
    out=temp/(f'nes-credit1004-{policy}-p{phase}'+('-'+fault if fault else ''))

    def instrument(script):
        lo=script.index("  if operation=='EARLY' then")
        hi=script.index("  if operation=='PUSH'then",lo)
        body=ARBITER.replace('RESERVE_TILE',str(policy in ('tile','both','feed')).lower())
        body=body.replace('RESERVE_FROM','2' if policy=='feed' else '3')
        body=body.replace('RESERVE_SEAL',str(policy in ('seal','both')).lower()).replace('E0_COST',str(e0))
        script=script[:lo]+body+script[hi:]
        return once(script,'local function nextCommand()',"""local snapshot1004=nil
local tiles1004=0
local status1004=assert(io.open(ROOT..'/status1004.txt','w'))
local function nextCommand()""")
    run(temp,phase,'tail',fault,destination=out,extra=instrument)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('policy',choices=('control','tile','seal','both','feed','fixed'))
    p.add_argument('--fault',choices=('bad_seal','stop_decode'))
    args=p.parse_args()
    if args.policy=='fixed':
        assert not args.fault
        original_order(args.temp.resolve(),args.phase)
    else:
        execute(args.temp.resolve(),args.phase,args.policy,args.fault)
