"""Reject a larger176B tile after232 and every tile after252 on the real beam."""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from test_nes_tile532_priority import prepare
from test_nes_tile532_edges import gate
from test_nes_idle524_priority import case
from nes_raw506 import once,sha


def run(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    source=a.out/'input';prepare(a.trace,source,False,two_tiles=True)
    small=a.out/'small-input';prepare(a.trace,small,False,two_tiles=True)
    records=[json.loads(x) for x in (source/'packets.jsonl').read_text().splitlines()]
    for row in records:
        b=bytearray.fromhex(row[2])
        if b[0]==7 and int.from_bytes(b[8:10],'little')==906:
            assert int.from_bytes(b[14:16],'little')==128
            b[14:16]=(176).to_bytes(2,'little');row[2]=b.hex()
            row[3]=(bytes.fromhex(row[3])+bytes(range(48))).hex();break
    (source/'packets.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in records))
    body=(a.client/'body.bin').read_bytes();labels=json.loads((a.client/'labels.json').read_text())
    pc=0x7e2000+body.index(bytes.fromhex('ad1242'),labels['prefix523']-0x7e2000)
    results=[]
    for line in (240,253):
        sub=SimpleNamespace(client=a.client,mesen=a.mesen,trace=source if line==240 else small,out=a.out/str(line));sub.out.mkdir()
        def edit(s,l):
            s=gate(s,l,line,'tile',pc)
            # The measured fallback has real instruction cost after the latch.
            # Eligibility is tested at the latch, not at the eventual RTS.
            s=once(s,'line<=pacedLine+1','line<=pacedLine+4')
            return s
        r=case(sub,906,'stop',edit_fixture=edit);assert r['size']==0 and r['grant']==0
        results.append(dict(latch_window_line=line,**r))
    (a.out/'result.json').write_text(json.dumps(dict(client=sha(a.client/'sink165.sfc'),passed=True,cases=results),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
