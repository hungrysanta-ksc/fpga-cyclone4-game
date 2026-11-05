# SPDX-License-Identifier: MIT
"""Exercise the late tile grant and both ends of the 144-byte SEAL bitmap."""
import argparse
import json
from pathlib import Path

from nes_raw506 import once
from test_nes_idle524_priority import case
from test_nes_map526_priority import map_fixture
from test_nes_tile532_edges import width
from test_nes_tile532_priority import fixture, prepare


def coverage_fault(source, labels, byte):
    s = width(map_fixture(source, labels), 1152)
    start = s.index('local validity=0x1320+word(0x1254)')
    end = s.index("assert(found,'no missing reference in fixture')", start)
    mask = 128 if byte % 2 else 1
    s = s[:start] + f"""local addr=0x1320+word(0x1254)+{byte}
    emu.write(addr,rd(addr)&~{mask},emu.memType.snesWorkRam)
    b[{41+byte}]=b[{41+byte}]|{mask}
    """ + s[end+len("assert(found,'no missing reference in fixture')"):]
    s = once(s, 'local failedMark526=false', f"""local caught619=false
emu.addMemoryCallback(function() if packet and pw(8)==FAULT then caught619=true end end,emu.callbackType.exec,{labels['missing619']})
local failedMark526=false""")
    return once(s, "or failedMark526,'missing bitmap rejection'", "or (caught619 and failedMark526),'missing bitmap rejection'")


def tile_gate(source, labels, boundary, length, rejected):
    s = fixture(source, labels)
    pred = 'word(0x1252)+8==word(0x1250) and (word(0x4000+word(0x1252))&0x7000)<0x5000 and word(0x4004+word(0x1252))<=160'
    s = once(s, pred, f'word(0x1252)+8<word(0x1250) and word(0x4004+word(0x1252))=={length} and (word(0x4000+word(0x1250)-8)&0x7000)<0x5000')
    # Suppress offers until the real beam reaches the chosen horizontal edge.
    # Distinguish the initial status read from the subsequent hardware recheck.
    hook = f"""local initial619=false
emu.addMemoryCallback(function()initial619=true end,emu.callbackType.exec,{boundary})
emu.addMemoryCallback(function()initial619=false end,emu.callbackType.exec,{boundary+3})
local attempted619,cap619=false,false
emu.addMemoryCallback(function()
 if held and index==held and attempted619 then cap619=true end
end,emu.callbackType.exec,{labels['tile619']})
emu.addMemoryCallback(function(a,v)
 if not initial619 or word(0x1226)~=FAULT then return end
 local st=emu.getState()
 if not held or armed or st['ppu.scanline']~=252 or st['memoryManager.hClock']<950 or st['memoryManager.hClock']>1090 then return v&127 end
 attempted619=true
end,emu.callbackType.read,0x4212)
"""
    if rejected:
        hook += f"""emu.addMemoryCallback(function()
 if attempted619 and not armed then armed=true;stopping=true end
end,emu.callbackType.exec,{labels['defer_beam']})
"""
        s = once(s,'if index==held and not armed then','if index==held and not armed then error("oversize tile admitted");')
    s=once(s, 'local function loaded()', hook + 'local function loaded()')
    return once(s, "assert(captured==commits and (CASE=='cold'", "assert(cap619,'tile size check not reached');assert(captured==commits and (CASE=='cold'")


def run(a):
    a.out=a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    labels=json.loads((a.client/'labels.json').read_text())
    raw=(a.client/'body.bin').read_bytes()
    boundary=0x7e2000+raw.index(bytes.fromhex('ad1242'),labels['prefix523']-0x7e2000)
    results=[]
    map_trace=a.out/'map-first'
    prepare(a.trace,map_trace,False,map_first=True)
    for gen in (906,907):
        for byte in (0,15,16,143):
            sub=argparse.Namespace(**vars(a));sub.trace=map_trace;sub.out=a.out/f'bank-{gen}-{byte}';sub.out.mkdir()
            r=case(sub,gen,'bad_manifest',edit_fixture=lambda s,l:coverage_fault(s,l,byte))
            results.append(dict(byte=byte,**r))
    if 'tile619' not in labels:
        (a.out/'edges.json').write_text(json.dumps(results,indent=2)+'\n')
        return
    for length in (128,384,400):
        trace=a.out/f'tiles-{length}'
        prepare(a.trace,trace,False,two_tiles=True)
        records=[json.loads(row) for row in (trace/'packets.jsonl').read_text().splitlines()]
        edits=0
        for r in records:
            b=bytearray.fromhex(r[2])
            if length!=128 and b[0]==7 and int.from_bytes(b[8:10],'little')==906 and edits<2:
                n=length if edits==0 else 16
                assert b[1]==0
                b[10:12]=(edits*2048).to_bytes(2,'little');b[14:16]=n.to_bytes(2,'little')
                r[2]=b.hex();r[3]=bytes(i%256 for i in range(n)).hex();edits+=1
        assert edits==(0 if length==128 else 2)
        (trace/'packets.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
        for name in ({128:('head',),384:('late_stop','both'),400:('stop',)}[length]):
            sub=argparse.Namespace(**vars(a));sub.trace=trace;sub.out=a.out/f'{length}-{name}';sub.out.mkdir()
            r=case(sub,906,name,edit_fixture=lambda s,l:tile_gate(s,l,boundary,length,length>384))
            assert r['size']==(384 if name=='late_stop' else 0)
            if r['size']:assert 252<=r['start_line']<=r['end_line']<262
            results.append(dict(tile_B=length,**r))
    (a.out/'edges.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('client','mesen','trace','out'):p.add_argument('--'+n,required=True,type=Path)
    run(p.parse_args())
