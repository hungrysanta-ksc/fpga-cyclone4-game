# SPDX-License-Identifier: MIT
"""Replay the installed ROM, observing queue eligibility or supplying a new head during map DMA."""
import argparse
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
import trace_nes_owner739 as owner
from nes_raw506 import once
from analyze_nes_owner739 import read


def run(a):
    labels=read(a.client/'labels.json')
    def edit(script):
        if a.one_input:
            import json
            from math import floor
            from analyze_nes_owner739 import packets, csv_groups
            group=packets(a.trace)[957]
            obj=next(i for i,(h,_,_) in enumerate(group) if h[:2]==bytes((7,1)))
            assert group[obj-1][0][1]==2 and group[obj+1][0][:2]==bytes((9,4))
            ack=[r for r in csv_groups(a.trace/'window.csv')[957] if r['event']=='ack'][obj-1]['clock']
            samples=[e for e in read(a.trace/'events.json') if e['event']=='idle676_return' and
                     e['generation']==957 and ack<e['begin']<e['clock']<group[obj][2]]
            # Optimistic fixed-clock diagnostic. Advance only the two immutable
            # arrivals by one actual empty callback. The linked trial pays the
            # real OAM drain and can consequently change later arrival clocks.
            ticks=floor(samples[0]['clock']-samples[0]['begin'])
            rows=(a.out/'arrivals.tsv').read_text().splitlines()
            marks={group[obj][2],group[obj+1][2]}
            changed=0
            for i,row in enumerate(rows):
                time,rest=row.split('\t',1)
                if int(time) in marks:
                    rows[i]=str(int(time)-ticks)+'\t'+rest
                    changed+=1
            assert changed==2 and ticks>0 and group[obj][2]-ticks>ack
            (a.out/'arrivals.tsv').write_text('\n'.join(rows)+'\n',newline='\n')
            (a.out/'one_input.json').write_text(json.dumps(dict(ticks=ticks,callback=samples[0],original=sorted(marks))))

        head = """
local fired748=false
checkedMem527(function()
 if fired748 or word(0x1226)~=957 or regs[0x4302]+256*regs[0x4303]~=22528 or
     regs[0x4305]+256*regs[0x4306]~=1536 then return end
 fired748=true
 local st=emu.getState()
 rpc()
 if sent==retired then
  assert(b522~='FINISH' and target522>st.masterClock)
  target522=st.masterClock;rpc()
 end
 assert(sent>retired and not packet)
 local f=assert(io.open(ROOT..'/head748.txt','w'))
 f:write(st.masterClock,' ',index,' ',requests[index]:byte(1),' ',requests[index]:byte(2));f:close()
end,emu.callbackType.write,0x2118)
"""
        if a.head:
            return once(script,'local finished522=false',head+'local finished522=false')
        from test_nes_input748 import instrument
        if 'dma748.csv' not in script:
            script=instrument(script)
        code="""local decision748=assert(io.open(ROOT..'/decision748.csv','w'))
decision748:write('pc,clock,frame,line,h,head,tail,src,n\\n')
local seen748={}
local function mark748(pc)
 if word(0x1226)~=957 then return end
 local head=word(0x1252);local tail=word(0x1250)
 if head>=tail or word(0x4000+head)~=19104 then return end
 local st=emu.getState()
 local key=pc..'/'..head..'/'..tail..'/'..st.frameCount..'/'..st['ppu.scanline']
 if seen748[key] then return end
 seen748[key]=true
 decision748:write(string.format('%s,%d,%d,%d,%d,%d,%d,%d,%d\\n',pc,st.masterClock,
  st.frameCount,st['ppu.scanline'],st['memoryManager.hClock'],head,tail,word(0x4000+head),word(0x4004+head)))
end
"""
        for name in ('prefix523','tail532','late_tile681','large_tile681','defer_beam','ready524'):
            code+=f"checkedMem527(function()mark748('{name}')end,emu.callbackType.exec,{labels[name]})\n"
        return once(script,'local function loaded()',code+'local function loaded()')
    def compare(ref, actual):
        if not a.head and not a.one_input:
            assert actual==ref
        else:
            before=lambda rows:[r for r in rows if int(r['g'])<957]
            assert before(ref)==before(actual)
        return dict(reference_events=len(ref),actual_events=len(actual))
    a.frames=53
    with patch.object(replay,'observe',owner.observe):
        replay.run(a,edit_script=edit,compare_trace=compare)
    if a.head:
        import csv
        tick,idx,op,sec=map(int,(a.out/'head748.txt').read_text().split())
        with (a.out/'window.csv').open() as f:
            nxt=next(r for r in csv.DictReader(f) if int(r['clock'])>tick and r['event'] in ('load','ppu_dma'))
        assert nxt['event']=='load' and (int(nxt['index']),int(nxt['op']),int(nxt['section']))==(idx,op,sec),nxt


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('trace','out','mesen','client'):p.add_argument('--'+k,type=Path,required=True)
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--head',action='store_true')
    mode.add_argument('--one-input',action='store_true')
    run(p.parse_args())
