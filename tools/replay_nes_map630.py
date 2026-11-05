# SPDX-License-Identifier: MIT
"""Hold the actual 625 stream through the last tile. Compare bounded tail schedules."""
import argparse
import json
import re
from pathlib import Path
from unittest.mock import patch
import replay_nes_map527 as replay
from analyze_nes_map628 import csv_groups, ms, one, read, sha
from analyze_nes_tail627 import deadlines
from nes_raw506 import once

WIRE_CLOCKS=21477272*8/2625000

def pack(h):
    assert h[:2]==bytes((2,2)) and len(h)==208
    payload=bytearray()
    for pos in range(16,208,64):
        row=h[pos:pos+64]
        assert row[34:]==bytes(30)
        payload.extend(bytes((34,0))+row[:34])
    return bytes((9,))+h[1:12]+bytes((108,0,192,0))+payload

def schedule(rows,events,mode):
    spi=[e for e in events if e['event']=='SPI']
    sends=[e for e in spi if e['opcode']=='0xe1']
    start=next(i for i,r in enumerate(rows) if r[1][1]==2 and int.from_bytes(r[1][10:12],'little')==2048)
    assert len(rows)==len(sends) and rows[start-1][1][0]==7
    order=list(range(start,len(rows)))
    if mode in ('priority','busy','ideal'):
        order.sort(key=lambda i: (0 if rows[i][1][1] in (3,4) else 1,i))
    assert order[-1]==len(rows)-1
    now=sends[start]['start']
    result=[]
    for slot,idx in enumerate(order,start):
        ts,h,bulk=rows[idx];e=sends[idx]
        assert abs(ts-e['clock'])<=1
        wire=e['clock']-e['start']
        if h[1]==2 and mode!='readybase':
            packed=pack(h);wire-=(len(h)-len(packed))*WIRE_CLOCKS;h=packed
        # Preserve the original gap preceding each position in the tail.
        # busy keeps only observed intervening non-E1 wire time; ideal keeps none.
        if slot>start:
            prev=sends[slot-1]['clock'];cur=sends[slot]['start']
            if mode=='busy':
                now+=sum(x['clock']-x['start'] for x in spi if x['opcode']!='0xe1' and prev<=x['start'] and x['clock']<=cur)
            elif mode!='ideal':now+=cur-prev
        now+=wire
        if mode=='fixed':now=ts
        # Receiver-only bound. All remaining work is available immediately
        # after the original OBJ PUSH. Never bypass a held head or four credits.
        if mode in ('ready','readybase'):now=rows[start-1][0]+1
        result.append((round(now),h[:2]+rows[slot][1][2:4]+h[4:],bulk))
    return rows[:start]+result

def run(a):
    a.frames=47
    events=[e for e in read(a.trace/'events.json') if e['generation']==951]
    cutoff=deadlines(a.trace)[951]['previous_cutoff']
    def observe(_,args,unused):
        s=(a.trace/'capture.lua').read_text()
        s=once(s,'local ROOT='+json.dumps(a.trace.resolve().as_posix()),'local ROOT='+json.dumps(args.out.as_posix()))
        s=once(s,"MODE=='normal'and 53 or","MODE=='normal'and 47 or")
        s=once(s,'checkedMem527(function()rpc()end','emu.addMemoryCallback(function()rpc()end')
        s=once(s,'checkedEvent527(function()\n if sequence==1','emu.addEventCallback(function()\n if sequence==1')
        old=read(a.base_client/'labels.json');new=read(a.client/'labels.json')
        pcs={v:new[k] for k,v in old.items()}
        s=re.sub(r'\b(82[0-9]{5})\b',lambda m:str(pcs.get(int(m[1]),int(m[1]))),s)
        s=once(s,'(pb(0)==2 or pb(0)==4) then','(pb(0)==2 or pb(0)==4 or pb(0)==9) then')
        if a.mode=='readybase':
            hooks=''
            for label in ('data','accepted'):
                hooks+=f"checkedMem527(function()if packet and pw(8)==951 then sample516('{label}630') end end,emu.callbackType.exec,{new[label]})\n"
            s=once(s,"checkedMem527(function()sample516('seal')",hooks+"checkedMem527(function()sample516('seal')")
        s=once(s,'and regs[0x4300]==8 then','and regs[0x4300]==8 and not (packet and pb(0)==9) then')
        return once(s,' if a==0x2116 or a==0x2117',""" if a==0x420b and v==1 and packet and pb(0)==9 then
  local n=regs[0x4305]+256*regs[0x4306];local src=regs[0x4302]+256*regs[0x4303]
  assert(regs[0x4301]==128 and regs[0x4304]==64,'map WRAM port')
  if regs[0x4300]==8 then assert(n==30 and src==17);sample516('fill630',n)
  else assert(regs[0x4300]==0 and n==34 and (src==18 or src==54 or src==90));sample516('literal630',n) end
 end
 if a==0x2116 or a==0x2117""")
    def edit(s):
        path=a.out/'arrivals.tsv';prefix=[];rows=[]
        for line in path.read_text().splitlines()[:-1]:
            clock,hexhead,bulk=line.split('\t');h=bytes.fromhex(hexhead)
            if int.from_bytes(h[8:10],'little')==951:rows.append((int(clock),h,bulk))
            else:prefix.append(line)
        trial=schedule(rows,events,a.mode)
        path.write_text('\n'.join(prefix+[f'{t}\t{h.hex()}\t{b}' for t,h,b in trial]+[f'{trial[-1][0]+1}\tFINISH\t'])+'\n',newline='\n')
        return once(s,"assert(sent-retired<4,'queue overflow')","if sent-retired>=4 then return end")
    def compare(before,after):
        w=csv_groups(a.out/'window.csv');r=w[951]
        out={'mode':a.mode,'cutoff':cutoff,'issue_trace':sha(a.out/'arrivals.tsv'),'client':sha(a.out/'client.sfc')}
        def clock(v,k):return one(v,k)['clock']
        def rel(t):return ms(t-cutoff)
        for n,sec in [('map',2),('palette',3),('oam',4),('hdma',5)]:
            subset=[e for e in r if e['section']==sec]
            out[n+'_ACK']=rel(max(e['clock'] for e in subset if e['event']=='ack'))
        compressed=[e for e in r if e['op']==9]
        costs=[]
        for index in sorted({e['index'] for e in compressed}):
            packet=[e for e in compressed if e['index']==index]
            assert [e['event'] for e in packet if e['event'] in ('fill630','literal630')]==['literal630','fill630']*3
            costs.append(ms(clock(packet,'ack')-clock(packet,'load')))
        assert len(costs)==(0 if a.mode=='readybase' else 8)
        if not costs:
            for index in sorted({e['index'] for e in r if e['section']==2})[2:]:
                packet=[e for e in r if e['index']==index]
                costs.append(ms(clock(packet,'ack')-clock(packet,'load')))
        seal=[e for e in r if e['op']==3]
        last=lambda g:one([e for e in w[g] if e['op']==3],'reveal')
        out.update(map8_service_ms=sum(costs),interval=last(951)['frame']-last(950)['frame'],
                   SEAL_offer=rel(int((a.out/'arrivals.tsv').read_text().splitlines()[-2].split('\t')[0])),
                   SEAL_head=rel(clock(seal,'load')),beam_check=rel(clock(seal,'final212')),
                   last_dma=rel(max(e['clock'] for e in seal if e['event']=='ppu_last')),
                   display=rel(last(951)['clock']),ACK=rel(clock(seal,'ack')))
        return out
    with patch.object(replay,'observe',observe):
        replay.run(a,edit_script=edit,compare_trace=compare,source_client=a.base_client)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','base-client','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--mode',choices=['fixed','wire','priority','busy','ideal','ready','readybase'],required=True)
    run(p.parse_args())
