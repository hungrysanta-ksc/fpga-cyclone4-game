# SPDX-License-Identifier: MIT
"""Verify head-map retirement, STOP and independent coverage at real beam boundaries."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from test_nes_tile532_edges import gate, width
from test_nes_map526_priority import map_fixture
from test_nes_idle524_priority import case
from nes_raw506 import once
from test_nes_tile532_priority import prepare


def head_fixture(text):
    # The 616 oracle treated every map as the tail. Keep the allocation tail
    # separately from the selected address, including both possible full pops.
    text=once(text,'local tail,source,dest,length,savedRow','local tail,selected,source,dest,length,savedRow')
    text=once(text,'return t>=word(0x1252) and (word(0x4000+t)&0x7000)==0x5000',
              'return t>=word(0x1252) and (word(0x4000+word(0x1252))&0x7000)==0x5000')
    text=text.replace('word(0x4004+word(0x1250)-8)>=1152','word(0x4004+word(0x1252))>=1152')
    text=once(text,'owner=activeImage();tail=word(0x1250)-8','owner=activeImage();tail=word(0x1250)-8;selected=initial')
    for offset in ('4000','4002','4004'):
        text=text.replace('word(0x'+offset+'+tail)','word(0x'+offset+'+selected)')
    return once(text,"assert(word(0x1252)==initial and word(0x1250)==tail,'tail not removed')",
                "assert(word(0x1252)==initial+8 and word(0x1250)==tail+8,'head not removed')")


def run(a):
    # Present the actual 906 cold-map packets contiguously so an accepted
    # head >=1152 B exists for the last-line stress case. Retain token order.
    source=a.out.with_name(a.out.name+'-input')
    prepare(a.trace,source,False,map_first=True)
    path=source/'packets.jsonl'
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    reordered=[]
    for gen in (905,906,907):
        group=[row for row in rows if int.from_bytes(bytes.fromhex(row[2])[8:10],'little')==gen]
        if gen==906:
            maps=[row for row in group if bytes.fromhex(row[2])[:2]==bytes((2,2))]
            group=group[:1]+maps+[row for row in group[1:] if row not in maps]
        for seq,row in enumerate(group):
            head=bytearray.fromhex(row[2]);head[2:4]=seq.to_bytes(2,'little');row[2]=head.hex()
        reordered.extend(group)
    path.write_text(''.join(json.dumps(row)+'\n' for row in reordered))
    a.out.mkdir()
    labels=json.loads((a.client/'labels.json').read_text())
    body=(a.client/'body.bin').read_bytes()
    beam_pc=0x7e2000+body.index(bytes.fromhex('ad1242'),labels['prefix523']-0x7e2000)
    last=json.loads((a.client/'build.json').read_text())['map_last_line']
    results=[]
    for line,name in ((last,'late_stop'),(last+1,'stop'),(last,'head'),(last,'both')):
        sub=SimpleNamespace(trace=source,client=a.client,mesen=a.mesen,out=a.out/f'line{line}-{name}')
        sub.out.mkdir()
        def at_line(script,symbols):
            return head_fixture(gate(script,symbols,line,'map',beam_pc,1152,last_map_line=last))
        observed=case(sub,906,name,edit_fixture=at_line)
        assert observed['size']==(1152 if name=='late_stop' else 0)
        if observed['size']:
            assert line<=observed['start_line']<=observed['end_line']<262
        results.append(dict(line=line,**observed))
    negative=a.out/'neg-input'
    prepare(source,negative,False,map_first=True)
    for g in (906,907):
        for fault in ('missing','duplicate'):
            sub=SimpleNamespace(trace=negative,client=a.client,mesen=a.mesen,out=a.out/f'{g}-{fault}')
            sub.out.mkdir()
            def damaged(script,symbols):
                return head_fixture(width(map_fixture(script,symbols,fault=='duplicate'),1152))
            results.append(dict(fault=fault,**case(sub,g,'bad_manifest',edit_fixture=damaged)))
    (a.out/'edges.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','client','mesen','out'):parser.add_argument('--'+key,required=True,type=Path)
    run(parser.parse_args())
