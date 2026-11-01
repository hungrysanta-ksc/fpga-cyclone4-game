# SPDX-License-Identifier: MIT
"""Race real map rows against head and STOP in both banks, including 64-byte tail removal."""
import argparse
import json
from pathlib import Path
import shutil

from nes_raw506 import once
from test_nes_idle524_priority import case
from test_nes_prefix523_edges import pace_beam
from nes_map526 import build


def map_fixture(s,labels,duplicate=False):
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
    s=once(s,'assert(owner==activeImage() and word(0x1252)==initial+(lastWrite and 8 or 0))',
           'assert(owner==activeImage());checkRow(lastWrite)')
    # Exercise the independent bitmaps even after the descriptor is shortened
    # or removed. Keep version, identity and sequence intact.
    mutation="""local validity=0x1320+word(0x1254)
    local found=false
    for slot=0,1023 do
     local byte=slot//8;local bit=1<<(slot%8)
     if (rd(validity+byte)&bit)==0 then b[41+byte]=b[41+byte]|bit;found=true;break end
    end
    assert(found,'no missing reference in fixture')"""
    if duplicate:
        s=once(s,"if pb(0)==3 then\n   if MODE=='bad_version'", """if headACK and pb(1)==2 and (pb(0)==2 or pb(0)==4) then
   local off=dest-(word(0x1034)==0 and 0x6000 or 0xa000)
   b[11]=off&255;b[12]=off>>8
  end
  if pb(0)==3 then
   if MODE=='bad_version'""")
        mutation="error('duplicate map escaped to SEAL')"
    s=once(s,"b[37]=0x71;b[38]=0x22",mutation)
    expected="pb(1)==2 and pb(0)~=3" if duplicate else "pb(0)==3"
    s=once(s,"local function loaded()",f"""local failedMark526=false
emu.addMemoryCallback(function()
 if CASE=='bad_manifest' and packet and pw(8)==FAULT and {expected} then failedMark526=true end
end,emu.callbackType.exec,{labels['mark_bad212']})
local function loaded()""")
    return once(s,"assert(captured==commits and (CASE=='cold'", "assert(CASE~='bad_manifest' or failedMark526,'missing bitmap rejection');assert(captured==commits and (CASE=='cold'")


def rejected_edge(s,labels,*,tile=False):
    if not tile:
        s=map_fixture(s,labels)
    else:
        s=once(s,'held=index;initial=word(0x1252);owner=activeImage()',
               '''held=index;initial=word(0x1252);owner=activeImage()
  assert((word(0x4000+initial)&0x7000)~=0x5000 and
         (word(0x4000+word(0x1250)-8)&0x7000)~=0x5000,'expected a tile command')''')
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


def empty_then_append(a):
    """Split an actual 192B map packet and make the first 64B the only live work."""
    folder=a.out/'map-first';folder.mkdir()
    frames={905:[],906:[]}
    for line in (a.trace/'packets.jsonl').read_text().splitlines():
        row=json.loads(line);b=bytearray.fromhex(row[2]);g=int.from_bytes(b[8:10],'little')
        if g>906:break
        frames[g].append((row,b))
    group=frames[906]
    i=next(i for i,(_,b) in enumerate(group) if b[:2]==b'\x02\x02')
    row,b=group.pop(i)
    assert len(b)==208 and b[10:12]==b'\0\0'
    first=b[:80];first[12:14]=(64).to_bytes(2,'little')
    rest=b[:16]+b[80:];rest[10:14]=(64).to_bytes(2,'little')+(128).to_bytes(2,'little')
    group[1:1]=[(row.copy(),first),(row.copy(),rest)]
    with (folder/'packets.jsonl').open('w') as f:
        for g,records in frames.items():
            for seq,(row,b) in enumerate(records):
                b[2:4]=seq.to_bytes(2,'little');row[2]=b.hex();print(json.dumps(row),file=f)
            for name in (f'map-{g}.bin',f'expected-{g}.bin',f'frame-{g}.rgb'):
                shutil.copyfile(a.trace/name,folder/name)
    test=argparse.Namespace(**vars(a));test.trace=folder;test.out=folder/'test';test.out.mkdir()
    def fixture(s,labels):
        return once(map_fixture(s,labels),"(FAULT==906 and length>=128)","(FAULT==906 and initial==0 and tail==0 and length==64)")
    r=case(test,906,'late_head',edit_fixture=fixture)
    assert r['size']==64 and r['commits']==2
    return r


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
    dup=argparse.Namespace(**vars(a));dup.out=a.out/'duplicate';dup.out.mkdir()
    for g in (906,907):
        r=case(dup,g,'bad_manifest',edit_fixture=lambda s,l:map_fixture(s,l,True))
        r['case']='duplicate_map';results.append(r)
    (a.out/'priority.json').write_text(json.dumps(results,indent=2)+'\n',newline='\n')
    (a.out/'empty.json').write_text(json.dumps(empty_then_append(a),indent=2)+'\n',newline='\n')
    if a.late_map:
        paced=a.out/'paced-client';build(paced,pace_beam,late=True)
        edges=[case(a,906,'late_stop',paced,254,map_fixture)]
        for line in (255,256):
            edges.append(case(a,906,'stop',paced,line,rejected_edge))
        edges.append(case(a,906,'stop',paced,233,lambda s,l:rejected_edge(s,l,tile=True)))
        for edge,line,kind in zip(edges,(254,255,256,233),('map','map','map','tile')):
            edge.update(sample_line=line,command=kind)
        (a.out/'edges.json').write_text(json.dumps(edges,indent=2)+'\n',newline='\n')
