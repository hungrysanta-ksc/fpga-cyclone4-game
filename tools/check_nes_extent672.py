"""Actual larger-tail DMA against a smaller accepted head, with STOP and new-head races."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from test_nes_idle524_priority import case
from test_nes_tile532_priority import prepare
from test_nes_tile532_edges import gate
from test_nes_seal538_stop import exercise
from nes_raw506 import once,sha


def run(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    source=a.out/'input'
    prepare(a.trace,source,False,map_first=True)
    rows=[json.loads(s) for s in (source/'packets.jsonl').read_text().splitlines()]
    ordered=[]
    for g in (905,906,907):
        group=[r for r in rows if int.from_bytes(bytes.fromhex(r[2])[8:10],'little')==g]
        if g==906:
            maps=[r for r in group if bytes.fromhex(r[2])[:2]==bytes((2,2))]
            assert len(maps)>8
            # Keep a real first192B head; withhold the second contiguous map.
            # The remaining original packets form a larger, disjoint tail.
            group=group[:1]+maps[:1]+maps[2:]+maps[1:2]+[r for r in group[1:] if r not in maps]
        for seq,r in enumerate(group):
            h=bytearray.fromhex(r[2]);h[2:4]=seq.to_bytes(2,'little');r[2]=h.hex()
        ordered.extend(group)
    (source/'packets.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in ordered))
    labels=json.loads((a.client/'labels.json').read_text())
    body=(a.client/'body.bin').read_bytes()
    beam=0x7e2000+body.index(bytes.fromhex('ad1242'),labels['prefix523']-0x7e2000)
    rows=[]
    for fault in ('late_stop','head','both','late_head'):
        sub=SimpleNamespace(trace=source,client=a.client,mesen=a.mesen,out=a.out/fault)
        sub.out.mkdir()
        def larger(script,symbols):
            s=gate(script,symbols,252,'map',beam,1152,last_map_line=252)
            s=once(s,"source=word(0x4000+tail);dest=word(0x4002+tail);length=word(0x4004+tail);savedRow=rowImage()",
                "assert(tail~=initial and word(0x4004+initial)<1152,'not a larger tail');source=word(0x4000+tail);dest=word(0x4002+tail);length=word(0x4004+tail);savedRow=rowImage()")
            # Tail-based oracle checks exact data, unchanged head and length
            # shortening/pop after synchronous completion. No fabricated grant.
            return s
        r=case(sub,906,fault,edit_fixture=larger)
        assert r['size']==(1152 if fault in ('late_stop','late_head') else 0)
        rows.append(r)
    recovery=case(SimpleNamespace(trace=source,client=a.client,mesen=a.mesen,out=a.out/'late_stop'),906,'cold')
    sealed=a.out/'sealed';sealed.mkdir()
    sub=SimpleNamespace(trace=a.trace,client=a.client,mesen=a.mesen,out=sealed)
    stops=[exercise(sub,g,label) for g in (906,907) for label in ('prepare665','final212')]
    result=dict(passed=True,client_SHA256=sha(a.client/'sink165.sfc'),larger_tail=rows,sealed_STOP=stops,cold_after_partial=recovery,
        scope='Unchanged candidate binary; reordered real cold packets retain identity and coverage. Final pixels, accepted-tail DMA data, head/tail retirement, STOP/new-head priority and retained visible bank checked on actual65816.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
