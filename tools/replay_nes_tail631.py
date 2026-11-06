# SPDX-License-Identifier: MIT
"""Replace only contiguous eligible 951 sections and replay both receiver and paced gates."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
import replay_nes_map527 as replay
from replay_nes_map630 import bound_observer
from analyze_nes_map628 import csv_groups, ms, one, read, sha
from analyze_nes_tail627 import deadlines
from nes_raw506 import once

def specialize(rows,which):
    result=[]
    i=0
    while i<len(rows):
        clock,h,tile=rows[i]
        sec=h[1];off=int.from_bytes(h[10:12],'little')
        if off==0 and ((sec==4 and which in ('oam','both')) or (sec==5 and which in ('scroll','both'))):
            oam=sec==4
            batch=rows[i:i+(3 if oam else 2)]
            ops=[v[1] for v in batch]
            expected=[(2,0,112,0),(8,112,4,400),(4,512,2,32)] if oam else [(2,0,21,0),(5,21,2,1100)]
            spec=[(q[0],*(int.from_bytes(q[n:n+2],'little') for n in (10,12,14))) for q in ops]
            assert spec==expected and all(q[1]==sec and q[4:10]==h[4:10] for q in ops)
            assert ops[-1][-1]==ops[-1][-2]
            body=b''.join(q[16:] for q in ops[:-1])+ops[-1][-1:]
            h=bytes((9,sec))+h[2:12]+len(body).to_bytes(2,'little')+(544 if oam else 1121).to_bytes(2,'little')+body
            clock=batch[-1][0];i+=len(batch)
        else:i+=1
        h=h[:2]+len(result).to_bytes(2,'little')+h[4:]
        result.append((clock,h,tile))
    return result

def run(a):
    a.frames=47;cut=deadlines(a.trace)[951]['previous_cutoff']
    def observe(_,args,unused):
        s,new=bound_observer(a,args)
        hook=''
        for k in ('data','accepted'):
            hook+=f"checkedMem527(function()if packet and pw(8)==951 then sample516('{k}631')end end,emu.callbackType.exec,{new[k]})\n"
        s=once(s,"checkedMem527(function()sample516('seal')",hook+"checkedMem527(function()sample516('seal')")
        s=once(s,'and regs[0x4300]==8 then','and regs[0x4300]==8 and not (packet and pb(0)==9) then')
        # Compare every expanded byte while the head is held, independent of
        # the client's coverage and without waiting for the final PPU image.
        return once(s,'  lastStatus=ack[1];',"""  if packet and pb(0)==9 and ack[1]==0 then
   local oam=pb(1)==4;local base=0x10000+word(0x1020)+(oam and 0x6200 or 0x6500)
   for j=0,pw(14)-1 do
    local k=oam and (j<112 and j or (j<512 and (112+j%4) or 116)) or math.min(21,j)
    assert(rd(base+j)==pb(16+k),'compound WRAM mismatch '..j)
   end
  end
  lastStatus=ack[1];""")
    def edit(s):
        path=a.out/'arrivals.tsv';prefix=[];rows=[]
        for line in path.read_text().splitlines()[:-1]:
            clock,h,b=line.split('\t');head=bytes.fromhex(h)
            if int.from_bytes(head[8:10],'little')==951:rows.append((int(clock),head,b))
            else:prefix.append(line)
        idx=next(i for i,r in enumerate(rows) if r[1][1]==2 and r[1][10:12]==bytes((0,8)))
        assert rows[idx-1][1][0]==7
        ready=rows[idx-1][0]+1
        trial=specialize(rows,a.which)
        trial=[(ready if a.ready and j>=idx else t,h,b) for j,(t,h,b) in enumerate(trial)]
        if a.early:
            assert a.ready and a.which=='both'
            ev=[e for e in read(a.trace/'events.json') if e['generation']==951]
            cursor=one(ev,'bg_map_frozen')['clock']
            end=one(ev,'prepare_enter')['clock']
            spi=[e for e in ev if e['event']=='SPI']
            assert all(e['clock']<=cursor or end<=e['start'] for e in spi)
            def duration(op,size):
                e=next(e for e in spi if e['opcode']==op and e['bytes']==size)
                return e['clock']-e['start']
            early=[]
            for _,h,b in trial[idx:idx+a.early]:
                assert h[:2]==bytes((2,2)) and len(h)==208
                cursor+=duration('0xe0',20)+duration('0xe8',20)+duration('0xe1',211)
                early.append((round(cursor),h,b))
            assert cursor<=end
            trial=trial[:idx]+early+trial[idx+a.early:]
            trial.sort(key=lambda entry:entry[0])
        lines=[f'{t}\t{(h[:2]+j.to_bytes(2,"little")+h[4:]).hex()}\t{b}' for j,(t,h,b) in enumerate(trial)]
        path.write_text('\n'.join(prefix+lines+[f'{(ready if a.ready else trial[-1][0])+1}\tFINISH\t'])+'\n',newline='\n')
        return once(s,"assert(sent-retired<4,'queue overflow')","if sent-retired>=4 then return end")
    def compare(_,after):
        w=csv_groups(a.out/'window.csv');r=w[951]
        seal=[e for e in r if e['op']==3]
        show=lambda g:one([e for e in w[g] if e['op']==3],'reveal')['frame']
        head=lambda q,k:one(q,k)['clock']
        indices=sorted({x['index'] for x in r if x['section']==2})[2:]+sorted({x['index'] for x in r if x['section'] in (3,4,5)})
        details=[]
        for i in indices:
            sub=[e for e in r if e['index']==i]
            ts=[head(sub,k) for k in ('load','data631','accepted631','ack')]
            assert ts==sorted(ts)
            loaded=one(sub,'load')
            details.append(dict(index=i,op=loaded['op'],section=loaded['section'],clocks=[b-a for a,b in zip(ts,ts[1:])]))
        return dict(mode=a.which,ready=a.ready,packets=details,interval=show(951)-show(950),
                    seal_ms=ms(head(seal,'load')-cut),upload_ms=ms(head(seal,'upload165_entry')-cut),
                    dma_ms=ms(min(e['clock'] for e in seal if e['event']=='ppu_dma')-cut),
                    ack=head(seal,'ack'),client=sha(a.client/'sink165.sfc'),offers=sha(a.out/'arrivals.tsv'))
    with patch.object(replay,'observe',observe):
        replay.run(a,edit_script=edit,compare_trace=compare,source_client=a.base_client)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','base-client','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--which',choices=['neither','oam','scroll','both'],required=True)
    p.add_argument('--ready',action='store_true')
    p.add_argument('--early',type=int,choices=(0,2,3),default=0,
                   help='Place early map offers in the observed idle bus window; charge E0/E8/E1 wire only.')
    run(p.parse_args())
