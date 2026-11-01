# SPDX-License-Identifier: MIT
"""Race open/merged tile DMA against STOP/head; independently check cold recovery and map coverage."""
import argparse
import json
import shutil
from pathlib import Path
from nes_raw506 import once
from nes_tile532 import build
from test_nes_idle524_priority import case
from test_nes_map526_priority import map_fixture,rejected_edge
from test_nes_prefix523_edges import pace_beam
from test_nes_tile532_edges import width


def fixture(s,labels,merged=False,interior=False):
    pred='merged532' if merged else 'word(0x1252)+8==word(0x1250) and (word(0x4000+word(0x1252))&0x7000)<0x5000 and word(0x4004+word(0x1252))<=160'
    if interior:
        pred='word(0x1252)+16<word(0x1250) and (word(0x4000+word(0x1252))&0x7000)==0x5000 and (word(0x4008+word(0x1252))&0x7000)<0x5000 and word(0x400c+word(0x1252))<=160'
    s=once(s,'word(0x1252)+8<word(0x1250) then',pred+' then')
    s=once(s,'local function activeImage()',f"""local merged532=false;local src,dst,len,old,expected,tail
emu.addMemoryCallback(function()
 local x=emu.getState()['cpu.x'];local t=word(0x1250)-8
 if word(0x1226)==FAULT and x<t then
  assert(x>=word(0x1252) and t-x==8);merged532=true
 end
end,emu.callbackType.exec,{labels['merge_written532']})
local function take532(address,n,memory)
 local b={{}};for j=0,n-1 do b[#b+1]=string.char(emu.read(address+j,memory)) end
 return table.concat(b)
end
local function check532(sent)
 assert(take532(dst,len,emu.memType.snesVideoRam)==(sent and expected or old))
 if not sent then assert(word(0x1252)==initial and word(0x1250)==tail)
 elseif initial+8==tail then assert(word(0x1252)==0 and word(0x1250)==0)
 else assert(word(0x1252)==initial+8 and word(0x1250)==tail) end
end
local function activeImage()""")
    s=once(s,'owner=activeImage()',"""owner=activeImage();tail=word(0x1250)
  src=word(0x4000+initial);dst=word(0x4002+initial);len=word(0x4004+initial)
  old=take532(dst,len,emu.memType.snesVideoRam);expected=take532(0x10000+src,len,emu.memType.snesWorkRam)""")
    s=once(s,'if held==index and not released then return end',
           'if held==index and not released then return end\n if held==index and not packet then check532(lastWrite) end')
    s=once(s,"assert(word(0x1252)==initial+(targetedGrant and 8 or 0),'cursor at head ACK')",
           "assert(not targetedGrant or issuedSize==len)")
    s=once(s,'assert(owner==activeImage() and word(0x1252)==initial+(lastWrite and 8 or 0))',
           'assert(owner==activeImage());check532(lastWrite)')
    if interior:
        s=once(s,'src=word(0x4000+initial);dst=word(0x4002+initial);len=word(0x4004+initial)',
               'src=word(0x4008+initial);dst=word(0x400a+initial);len=word(0x400c+initial)')
        s=once(s,'issuedSize=word(0x4004+initial)','issuedSize=regs[0x4305]+256*regs[0x4306]')
    return s


def prepare(trace,out,merge,*,map_first=False):
    # Preserve payload/addresses and assign ordinary sequences in offered order.
    # In the merge fixture keep bulk tokens in the original order as well.
    out.mkdir()
    source=[json.loads(l) for l in (trace/'packets.jsonl').read_text().splitlines()]
    with (out/'packets.jsonl').open('w') as f:
        for g in (905,906,907):
            records=[(row.copy(),bytearray.fromhex(row[2])) for row in source if int.from_bytes(bytes.fromhex(row[2])[8:10],'little')==g]
            if g>=906:
                tiles=[r for r in records if r[1][0]==7]
                if map_first:
                    count=2 if g==906 else 1
                    take=[r for r in records if r[1][:2]==b'\x02\x02'][:count]
                    assert len(take)==count
                elif merge and g==906:
                    first,second=(next(r for r in tiles if r[1][1]==0 and int.from_bytes(r[1][10:12],'little')==off) for off in (1312,1328))
                    map_row=next(r for r in records if r[1][:2]==b'\x02\x02')
                    take=[first,map_row,second]
                    tokens=[bytes(r[1][16:20]) for r in tiles]
                else:take=[tiles[0]]
                records=records[:1]+take+[r for r in records[1:] if r not in take]
                if merge and g==906:
                    for r,token in zip((r for r in records if r[1][0]==7),tokens):r[1][16:20]=token
            for seq,(row,b) in enumerate(records):
                b[2:4]=seq.to_bytes(2,'little');row[2]=b.hex();print(json.dumps(row),file=f)
            for n in (f'map-{g}.bin',f'expected-{g}.bin',f'frame-{g}.rgb'):
                shutil.copyfile(trace/n,out/n)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('trace','client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--beam-only',action='store_true')
    p.add_argument('--interior-only',action='store_true')
    p.add_argument('--map-first-guards',action='store_true',help='Put actual map packets first for the map-specific fault injections.')
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    if a.beam_only:
        paced=a.out/'paced';build(paced,pace_beam)
        edges=[case(a,906,'late_stop',paced,254,map_fixture)]
        for line in (255,256):
            edges.append(case(a,906,'stop',paced,line,rejected_edge))
        edges.append(case(a,906,'stop',paced,233,lambda s,l:rejected_edge(s,l,tile=True)))
        (a.out/'edges.json').write_text(json.dumps(edges,indent=2)+'\n')
        raise SystemExit(0)
    root=a.out;trace=a.trace
    results=[]
    if a.interior_only:
        for name in ('head','stop','both','late_head','late_stop','cold'):
            results.append(case(a,906,name,edit_fixture=lambda s,l:fixture(s,l,interior=True)))
        assert all(r['size']>0 for r in results if r['grant'])
        (root/'interior.json').write_text(json.dumps(results,indent=2)+'\n')
        raise SystemExit(0)
    for group in ('single','merge'):
        a.trace=root/(group+'-trace');prepare(trace,a.trace,group=='merge')
        a.out=root/group;a.out.mkdir()
        for g in ((906,907) if group=='single' else (906,)):
            for name in ('head','stop','both','late_head','late_stop','cold'):
                r=case(a,g,name,edit_fixture=lambda s,l:fixture(s,l,group=='merge'))
                if r['grant']:assert r['size']==(80 if group=='merge' else 128 if g==906 else 16)
                results.append(dict(group=group,**r));print(results[-1],flush=True)
    a.trace=trace
    if a.map_first_guards:
        a.trace=root/'map-negative-trace'
        prepare(trace,a.trace,False,map_first=True)
    for g in (906,907):
        for duplicate in (False,True):
            a.out=root/('duplicate' if duplicate else 'missing');a.out.mkdir(exist_ok=True)
            def missing(s,l):
                s=map_fixture(s,l,duplicate)
                return width(s,json.loads((a.client/'build.json').read_text())['map_chunk_B']) if 'normal_length532' in l else s
            r=case(a,g,'bad_manifest',edit_fixture=missing)
            results.append(dict(group='duplicate' if duplicate else 'missing',**r))
    (root/'result.json').write_text(json.dumps(results,indent=2)+'\n')
