# SPDX-License-Identifier: MIT
"""Check the published record at the end of every 65816 final-ACK handler, including its cost."""
import argparse
import json
import struct
from pathlib import Path
from measure_nes_trim514_consume import run

OBSERVER = """
local receipts={@RECEIPTS@}
local publishClock=nil;local published=0
local times=assert(io.open(ROOT..'/publication.csv','w'))
times:write('generation,receipt,clocks_after_final_write\\n')
emu.addMemoryCallback(function(a,v)
 if packet and pb(0)==3 then publishClock=emu.getState().masterClock end
end,emu.callbackType.write,0x601c)
emu.addMemoryCallback(function()
 if lastStatus~=1 or not publishClock then return end
 local g=completedFrame;local b=(g-905)%2;local hex=''
 for i=0,7 do
  local v=rd(0x1460+b*8+i)
  assert((v~rd(0x1480+b*8+i))==255,'receipt complement')
  hex=hex..string.format('%02x',v)
 end
 assert(rd(0x1260+b)==1 and word(0x1470+b*2)==g-904 and hex==receipts[g],'publication mismatch')
 times:write(string.format('%d,%s,%d\\n',g,hex,emu.getState().masterClock-publishClock))
 publishClock=nil;published=published+1
 if published==12 then times:close() end
end,emu.callbackType.exec,@PUBLISHED@)
"""
def measure(a):
    rows={}
    for line in (a.candidate/'packets.jsonl').read_text().splitlines():
        b=bytes.fromhex(json.loads(line)[2])
        op,section,_,_,g,at,n,span=struct.unpack_from('<BBHIHHHH',b)
        if section!=2 or op not in (2,4,11):continue
        hi=at+(span if op==4 else n)
        mask=sum(1<<r for r in range(at//64,(hi+63)//64))
        assert not rows.get(g,0)&mask
        rows[g]=rows.get(g,0)|mask
    assert len(rows)==12
    table=','.join(f'[{g}]="{v.to_bytes(8,"little").hex()}"' for g,v in rows.items())
    address=json.loads((a.client/'labels.json').read_text())['no_publish514']
    # Observe the ACK before the original callback can retire the head.
    obs=OBSERVER.replace('if packet and pb(0)==3 then','if (packet and pb(0)==3) or lastStatus==1 then')
    obs=obs.replace('@PUBLISHED@',str(address)).replace('@RECEIPTS@',table)
    run(a,a.candidate,a.out,observer=obs)
    assert len((a.out/'publication.csv').read_text().splitlines())==13
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('candidate','client','out','mesen'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--dotnet',type=Path,default=Path('C:/works/dotnet'))
    a=p.parse_args();a.out=a.out.resolve();measure(a)
