# SPDX-License-Identifier: MIT
"""Remove six real 951 heads and grant verified target-bank bytes at zero simulated cost."""
import argparse
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from analyze_nes_map628 import csv_groups, ms, one, packets, read, sha
from analyze_nes_tail627 import deadlines
from nes_raw506 import once
from replay_nes_map630 import bound_observer


def target(commands, section):
    result = bytearray()
    for h, _, _ in commands:
        if h[1] != section:
            continue
        offset, length, span = [int.from_bytes(h[i:i+2], 'little') for i in (10,12,14)]
        assert len(result) == offset and len(h) == 16+length
        assert h[0] in (2,4,8) and (h[0]==2 or span%length==0)
        result.extend(h[16:] if h[0]==2 else h[16:]*(span//length))
    return result


def schedule(commands, pushes, mode):
    kept = []
    removed = []
    cost = 0
    tail = max(i for i,(h,_,_) in enumerate(commands) if h[0]==7)
    bus = commands[tail][2]
    for i, ((h, bulk, t), e) in enumerate(zip(commands,pushes,strict=True)):
        assert abs(t-e['clock'])<=1 and len(h)+3==e['bytes']
        omit = h[1]==3 or (h[1]==4 and int.from_bytes(h[10:12],'little')>=112)
        if omit and mode!='control':
            assert i>tail
            # Give back the entire interval from the previous E1, including
            # preparation, polling/credit and SPI. Do not double-count SNES time.
            cost += t-commands[i-1][2]
            removed.append([i,h[1],e['bytes']])
            continue
        when = t
        if mode=='collapse':
            when -= cost
        elif mode=='wire' and i>tail:
            # Separate sensitivity: all retained tail data ready at last OBJ.
            bus += e['clock']-e['start']
            when = round(bus)
        h = h[:2]+len(kept).to_bytes(2,'little')+h[4:]
        kept.append((when,h,bulk))
    assert mode=='control' or ([r[0] for r in removed]==[13,14,15,16,18,19] and sum(r[2] for r in removed)==388)
    return kept, removed, cost


def run(a, *, schedule_offers=schedule, edit_after=None, timing_metadata=None,
        source_client=None, real_observer=None):
    a.frames=47
    a.base_client=source_client or a.client
    commands=packets(a.trace)
    pushes=[e for e in read(a.trace/'events.json') if e['generation']==951 and e.get('opcode')=='0xe1']
    kept, removed, cost=schedule_offers(commands[951],pushes,a.mode)
    cutoff=deadlines(a.trace)[951]['previous_cutoff']
    bank=csv_groups(a.trace/'seal528.csv')
    assert one(bank[949],'final_credit')['bank']==one(bank[951],'final_credit')['bank']!=one(bank[950],'final_credit')['bank']
    def observe(_,args,unused):
        s,labels=bound_observer(a,args)
        if real_observer:
            return real_observer(s,labels)
        if a.mode=='control':
            return s
        for section,size,skip in ((3,512,0),(4,544,112)):
            now=target(commands[951],section)
            prior=target(commands[949],section)
            assert len(now)==len(prior)==size and prior[skip:]==now[skip:]
            (a.out/f'section-{section}.bin').write_bytes(now)
        s=once(s,'local function loaded()',"""local bank949=nil
local function loaded()""")
        s=once(s,'  lastStatus=ack[1];',"""  if pw(8)==949 and pb(0)==3 and ack[1]==1 then bank949=word(0x1020) end
  lastStatus=ack[1];""")
        # Only the diagnostic harness advances two receive lengths. Preserve
        # existing data, DMA work, SEAL mask checks and all final ACK code.
        return once(s,'packet=requests[index];sample516("load");','''packet=requests[index];
 if pw(8)==951 and pb(0)==3 then
  assert(bank949==word(0x1020) and word(0x1244)==950 and word(0x1226)==951)
  for _,s in ipairs({{3,0x6000,0,512},{4,0x6200,112,544}}) do
   local oracle=file('section-'..s[1]..'.bin');local cur=0x1080+2*s[1]
   assert(word(cur)==s[3] and #oracle==s[4])
   for j=0,#oracle-1 do assert(rd(0x10000+bank949+s[2]+j)==oracle:byte(j+1),'retained byte '..j) end
   emu.write(cur,s[4]%256,emu.memType.snesWorkRam);emu.write(cur+1,s[4]//256,emu.memType.snesWorkRam)
  end
 end
 sample516("load");''')
    def edit(s):
        path=a.out/'arrivals.tsv'
        prefix=[]
        for line in path.read_text().splitlines()[:-1]:
            _,data,_=line.split('\t')
            if int.from_bytes(bytes.fromhex(data)[8:10],'little')!=951:
                prefix.append(line)
        for t,h,bulk in kept:
            prefix.append(f'{t}\t{h.hex()}\t{bulk.hex()}')
        path.write_text('\n'.join(prefix+[f'{kept[-1][0]+1}\tFINISH\t'])+'\n',newline='\n')
        s=once(s,"assert(sent-retired<4,'queue overflow')","if sent-retired>=4 then return end")
        s=once(s,'local finished522=false',"""local queue633=assert(io.open(ROOT..'/queue.csv','w'))
queue633:write('index,offer,admit,depth\\n')
local finished522=false""")
        s=once(s,'  frames[sent]=g-905;',"""  if g==951 then queue633:write(string.format('%d,%d,%d,%d\\n',sent,target522,now,sent-retired));queue633:flush() end
  frames[sent]=g-905;""")
        return edit_after(s) if edit_after else s
    def compare(before,after):
        if a.mode=='control' and timing_metadata is None:
            assert before==after
        if not real_observer:
            assert [r for r in before if int(r['g'])<=950]==[r for r in after if int(r['g'])<=950]
        w=csv_groups(a.out/'window.csv')
        seal=[r for r in w[951] if r['op']==3]
        prior=one([r for r in w[950] if r['op']==3],'reveal')
        show=one(seal,'reveal')
        goal=prior['frame']+3
        maps=[]
        events=w[951]
        for i,e in enumerate(events):
            if e['event']=='idle524' and e['value']>=65536:
                start=next(r for r in events[i+1:] if r['event']=='ppu_dma')
                end=next(r for r in events[i+1:] if r['event']=='ppu_last')
                assert start['op']==end['op']==-1 and start['clock']<=end['clock']
                maps.append(dict(frame=start['frame'],start=start['clock'],end=end['clock'],line=start['line'],
                                 end_line=end['line'],offset=e['value']-65536,size=start['value']))
        return dict(**(timing_metadata or {}),mode=a.mode,removed=removed,schedule_credit_ms=ms(cost),goal=goal,cutoff=cutoff,
                    maps=maps,interval=show['frame']-prior['frame'],show=show,ack=one(seal,'ack')['clock'],
                    seal=one(seal,'load')['clock'],upload=one(seal,'upload165_entry')['clock'],
                    previous=prior['clock'],client=sha(a.client/'sink165.sfc'),offers=sha(a.out/'arrivals.tsv'))
    with patch.object(replay,'observe',observe):
        replay.run(a,edit_script=edit,compare_trace=compare,source_client=a.base_client)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','client','out','mesen'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--mode',choices=('control','gap','collapse','wire'),required=True)
    run(p.parse_args())
