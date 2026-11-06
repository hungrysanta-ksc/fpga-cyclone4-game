# SPDX-License-Identifier: MIT
"""Replay 625 offers; substitute only actual 628 payloads for the eight 951 map packets."""
import argparse
import csv
import json
import re
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from analyze_nes_map628 import ms, packets, sha
from nes_raw506 import once

def run(a):
    a.frames=47
    original=a.mode=='base'
    if a.paced:
        assert a.mode in ('group','split')
        a.trace=a.compressed
    source=a.trace if original else a.compressed
    reference=a.base_client if original else a.group_client
    assert sha(source/'client.sfc')==sha(reference/'sink165.sfc')
    old=json.loads((reference/'labels.json').read_text())
    labels=json.loads((a.client/'labels.json').read_text())
    selected={h[10:12]:h for h,_,_ in packets(a.compressed)[951] if h[0]==9}
    assert len(selected)==8

    def observe(_,args,unused):
        s=(source/'capture.lua').read_text(encoding='utf8')
        s=once(s,'local ROOT='+json.dumps(source.resolve().as_posix()),'local ROOT='+json.dumps(args.out.as_posix()))
        s=once(s,"MODE=='normal'and 53 or","MODE=='normal'and 47 or")
        s=once(s,'checkedMem527(function()rpc()end','emu.addMemoryCallback(function()rpc()end')
        s=once(s,'checkedEvent527(function()\n if sequence==1','emu.addEventCallback(function()\n if sequence==1')
        mapped={}
        for name,pc in old.items():
            if name in labels:
                mapped.setdefault(pc,set()).add(labels[name])
        def address(m):
            pc=int(m[1])
            if pc not in mapped:return m[0]
            assert len(mapped[pc])==1
            return str(next(iter(mapped[pc])))
        return re.sub(r'\b(82[0-9]{5})\b',address,s)

    def edit(s):
        path=a.out/'arrivals.tsv'
        rows=path.read_text().splitlines()
        changes=0
        for i,row in enumerate(rows[:-1]):
            clock,hexhead,bulk=row.split('\t');h=bytes.fromhex(hexhead)
            if not a.paced and a.mode not in ('base','literal') and h[:2]==bytes((2,2)) and int.from_bytes(h[8:10],'little')==951 and h[10:12] in selected:
                v=selected[h[10:12]]
                assert h[4:12]==v[4:12] and h[12:14]==v[14:16]
                rows[i]=f'{clock}\t'+(v[:2]+h[2:4]+v[4:]).hex()+f'\t{bulk}'
                changes+=1
        assert changes==(8 if not a.paced and a.mode in ('group','split') else 0)
        path.write_text('\n'.join(rows)+'\n',newline='\n')
        # Never silently enqueue a fifth packet. Record the actual observation
        # delay and whether physical credit prevented an on-time offer.
        s=once(s,'local finished522=false',"""local admission=assert(io.open(ROOT..'/admit.csv','w'))
admission:write('target,observed,blocked,index\\n')
local blocked=false
local finished522=false""")
        s=once(s,"assert(sent-retired<4,'queue overflow')","""if sent-retired>=4 then blocked=true;return end
  admission:write(string.format('%d,%d,%d,%d\\n',target522,now,blocked and 1 or 0,sent+1));blocked=false""")
        s=once(s,'TOTAL=sent;finished522=true','admission:flush();TOTAL=sent;finished522=true')
        if a.mode in ('group','split'):
            points={k:labels[k] for k in ('row628','group628','copy628','verify628','accepted')}
            if a.mode=='split':
                points.update({k:labels[k] for k in ('sumrow629','rowend629')})
            else:
                # First instruction after the two checksum words.
                code=(a.client/'body.bin').read_bytes()
                start=code.index(bytes.fromhex('b77a186d6612'))
                tail=code.index(bytes.fromhex('98893f00'),start)
                points['rowcontrol']=labels['verify628']+tail-start
            chunk="local profile629=assert(io.open(ROOT..'/profile.csv','w'))\n"
            for name,pc in points.items():
                chunk+=f"checkedMem527(function() if packet and pw(8)==951 and pb(0)==9 then profile629:write(index..',{name},'..emu.getState().masterClock..'\\n') end end,emu.callbackType.exec,{pc})\n"
            s=once(s,'local trace516=',chunk+'local trace516=')
            s=once(s,"f:write(']}');f:close();emu.stop(0)","profile629:flush();f:write(']}');f:close();emu.stop(0)")
        return s

    def compare(before,after):
        if original or (a.paced and a.mode=='group'):assert before==after
        maps=[r for r in after if r['g']=='951' and r['section']=='2']
        def times(rs,k):return [int(r['clock']) for r in rs if r['event']==k]
        head=times(maps,'load');ack=times(maps,'ack')
        assert len(head)==len(ack)==10
        service=ms(sum(y-x for x,y in zip(head,ack)))
        buckets={}
        if a.mode in ('group','split'):
            prev=None
            for idx,name,t in csv.reader((a.out/'profile.csv').open()):
                t=int(t)
                if prev and idx==prev[0]:
                    key=prev[1]
                    buckets[key]=buckets.get(key,0)+t-prev[2]
                prev=idx,name,t
        commits=[r for r in after if r['event']=='reveal' and r['g'] in ('950','951')]
        assert len(commits)==2
        admission=list(csv.DictReader((a.out/'admit.csv').open()))
        return dict(service_ms=service,stages_ms={k:ms(v) for k,v in buckets.items()},
                    blocked=sum(r['blocked']=='1' for r in admission),interval=int(commits[1]['frame'])-int(commits[0]['frame']),
                    last_ACK=times([r for r in after if r['g']=='951' and r['op']=='3'],'ack')[0],
                    offers_sha=sha(a.out/'arrivals.tsv'),client_sha=sha(a.client/'sink165.sfc'))
    with patch.object(replay,'observe',observe):
        replay.run(a,edit_script=edit,compare_trace=compare,source_client=a.group_client if a.paced else a.base_client)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','compressed','base-client','group-client','client','mesen','out'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--mode',choices=['base','literal','group','split'],required=True)
    p.add_argument('--paced',action='store_true',help='Use the exact 628 PUSH clocks throughout, including the slower 951.')
    run(p.parse_args())
