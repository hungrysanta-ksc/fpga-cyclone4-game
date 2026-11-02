# SPDX-License-Identifier: MIT
"""Check certified fills, arbitrary bytes, fragments, value changes, literals and format transitions."""
import argparse
import csv
import json
from pathlib import Path
from test_nes_history547_counts import run, payload, COUNTS
from nes_raw506 import sha
from replay_nes_receipt548 import receipt


def fixture(prefix,mask,count,gen):
    image,wire=payload(prefix,mask,count,gen)
    if count!=2:return image,wire
    rows=[bytes([0x37])*64]*4+[bytes(64),bytes([255])*64]
    if gen==912:rows[2:5]=[bytes([0x38])*64,bytes([0x37,0x2a])*32,bytes([255])*64]
    canonical=bytearray(image)
    for r,data in enumerate(rows):
        for i,value in enumerate(data):
            canonical[1121+i//2*64+r//2*16+r%2*2+i%2]=value
    return canonical,wire[:1121]+b''.join(rows)+wire[1505:]


def sections(wire,count,gen):
    def literals(start,end):
        return [(2,i,wire[i:min(i+240,end)],0) for i in range(start,end,240)]
    if count!=2:return literals(0,len(wire))
    def repeat(at,n):
        value=wire[at:at+2];assert wire[at:at+n]==value*(n//2)
        return (5 if n>240 else 4,at,value,n)
    if gen==912:
        raw=[repeat(1122,64),*literals(1186,1249),repeat(1249,64),repeat(1313,64),repeat(1377,64),repeat(1441,64)]
        return literals(0,1122)+raw+literals(1505,len(wire))
    return literals(0,1121)+[repeat(1121,256),repeat(1377,64),repeat(1441,64)]+literals(1505,len(wire))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('client','base','trace','mesen','out'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=False)
    for name,client in [('base',args.base),('new',args.client)]:
        run(args,args.out/name,client,name=='new',make_payload=fixture,encode=sections,probe=receipt)
    for g in range(905,913):assert sha(args.out/'base'/f'frame-{g}.rgb')==sha(args.out/'new'/f'frame-{g}.rgb')
    with (args.out/'new/history547.csv').open() as f:masks={int(r['g']):int(r['mask']) for r in csv.DictReader(f)}
    expected=63 if 'generic548' in json.loads((args.client/'labels.json').read_text()) else 48
    assert masks=={905:0,906:0,909:0,910:0,911:expected,912:32},masks
    (args.out/'result.json').write_text(json.dumps(dict(counts=COUNTS,masks=masks,RGB_frames=8))+'\n')
