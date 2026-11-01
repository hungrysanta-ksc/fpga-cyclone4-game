# SPDX-License-Identifier: MIT
"""Race real map rows against head and STOP in both banks, including 64-byte tail removal."""
import argparse
import json
from pathlib import Path

from nes_raw506 import once
from test_nes_idle524_priority import case
from test_nes_prefix523_edges import pace_beam
from nes_map526 import build


def map_fixture(s,labels):
    s=once(s,'local function activeImage()',"""local tail,source,dest,length,savedRow
local function mapTail()
 local t=word(0x1250)-8
 return t>=word(0x1252) and (word(0x4000+t)&0x7000)==0x5000
end
local function rowImage()
 local a={}
 for i=0,63 do a[i+1]=string.char(emu.read(dest+i,emu.memType.snesVideoRam)) end
 return table.concat(a)
end
local function checkRow(sent)
 if not sent then
  assert(word(0x1252)==initial and word(0x1250)==tail+8)
  assert(word(0x4000+tail)==source and word(0x4002+tail)==dest and word(0x4004+tail)==length)
  assert(rowImage()==savedRow,'deferred map DMA wrote VRAM')
  return
 end
 local offset=dest-(word(0x1034)==0 and 0x6000 or 0xa000)
 assert(rowImage()==file('map-'..FAULT..'.bin'):sub(offset+1,offset+64),'early row payload')
 if length>64 then
  assert(word(0x1252)==initial and word(0x1250)==tail+8)
  assert(word(0x4000+tail)==source+64 and word(0x4002+tail)==dest+64 and word(0x4004+tail)==length-64)
 elseif tail~=initial then
  assert(word(0x1252)==initial and word(0x1250)==tail,'tail not removed')
 else
  assert(word(0x1250)==0 and word(0x1252)==0,'empty list can extend retired range')
 end
end
local function activeImage()""")
    s=once(s,'word(0x1252)+8<word(0x1250) then','mapTail() then')
    s=once(s,'owner=activeImage()','''owner=activeImage();tail=word(0x1250)-8
  source=word(0x4000+tail);dest=word(0x4002+tail);length=word(0x4004+tail);savedRow=rowImage()
  assert((FAULT==906 and length>=128) or (FAULT==907 and length==64),'wrong tail fixture')''')
    s=once(s,'issuedSize=word(0x4004+initial)','issuedSize=regs[0x4305]+256*regs[0x4306];assert(issuedSize==64)')
    # Verify state before the next real packet is allowed to extend the list.
    s=once(s,'if held==index and not released then return end',
           'if held==index and not released then return end\n if held==index and not packet then checkRow(lastWrite) end')
    s=once(s,"assert(word(0x1252)==initial+(targetedGrant and 8 or 0),'cursor at head ACK')",'assert(issuedSize==0 or issuedSize==64)')
    return once(s,'assert(owner==activeImage() and word(0x1252)==initial+(lastWrite and 8 or 0))',
                'assert(owner==activeImage());checkRow(lastWrite)')


def rejected_edge(s,labels,*,tile=False):
    if not tile:
        s=map_fixture(s,labels)
    # If the late beam check incorrectly allows this command, fail even
    # though a subsequent STOP would otherwise mask the bad grant.
    s=once(s,'if index==held and not armed then','if index==held and not armed then error("late beam admitted");')
    return once(s,'local function loaded()',f"""emu.addMemoryCallback(function()
 if held and index==held and not armed then
  local line=emu.getState()['ppu.scanline'];assert(line>=pacedLine and line<=pacedLine+1,'wrong beam rejection')
  armed=true;stopping=true
 end
end,emu.callbackType.exec,{labels['defer_beam']})
local function loaded()""")


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('mesen','client','trace','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--late-map',action='store_true')
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    results=[]
    for g in (906,907):
        for name in ('head','stop','both','late_head','late_stop','bad_manifest','cold'):
            r=case(a,g,name,edit_fixture=map_fixture);results.append(r);print(r,flush=True)
    (a.out/'priority.json').write_text(json.dumps(results,indent=2)+'\n',newline='\n')
    if a.late_map:
        paced=a.out/'paced-client';build(paced,pace_beam,late=True)
        edges=[case(a,906,'late_stop',paced,254,map_fixture)]
        for line in (255,256):
            edges.append(case(a,906,'stop',paced,line,rejected_edge))
        edges.append(case(a,906,'stop',paced,233,lambda s,l:rejected_edge(s,l,tile=True)))
        (a.out/'edges.json').write_text(json.dumps(edges,indent=2)+'\n',newline='\n')
