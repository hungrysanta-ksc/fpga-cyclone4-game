# SPDX-License-Identifier: MIT
"""Check actual endpoint evidence and selected bank/copy behavior, not FPS."""
from pathlib import Path
import argparse, hashlib, json
from test_nes_client181 import expected
from test_nes_sinkpack181 import compare


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def seal(d,g):
    rows=[list(map(int,s.split())) for s in (d/f'seal-{g}.txt').read_text().splitlines()]
    bank,count,charge,chunks,clock=rows[0]
    assert len(rows)==count+1
    return dict(bank=bank,commands=count,charge=charge,chunks=chunks,clock=clock,items=rows[1:])


def main():
    p=argparse.ArgumentParser()
    for n in ('out','normal','steady','large','remaining','old_normal'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    reference=a.remaining/'client'
    for d in (a.normal.parent,a.steady.parent,a.large.parent):
        for name in ('body.bin','sink-program.hex','sink165.sfc'):
            assert (d/'client'/name).read_bytes()==(reference/name).read_bytes()
        assert (d/'nes_native_sink165.c').read_bytes()==(a.remaining/'nes_native_sink165.c').read_bytes()
    cases=[];pixels=0
    for d,scenes in ((a.normal,[(0,0),(7,0),(7,1),(0,0),(0,0),(1,0),(7,2)]),
                     (a.steady,[(0,0),(1,0),(7,0),(7,1),(7,1),(7,2),(0,0),(7,0),(7,1),(7,0)]),
                     (a.large,[(0,0),(1,0),(7,0),(7,1),(7,1),(7,2)])):
        r=json.loads((d/'consumer-result.json').read_text());assert r['passed']
        assert (d/'producer-done.txt').read_text().startswith('PASS ')
        for i,(count,phase) in enumerate(scenes,1):
            assert (d/f'frame-{i}.rgb').read_bytes()==expected(count,phase)
            pixels+=256*239
        r['mode']=d.name;cases.append(r)
    rest=json.loads((a.remaining/'result.json').read_text());assert rest['passed']
    cases+=rest['cases'];pixels+=sum(c['commits'] for c in rest['cases'])*256*239
    assert len(cases)==19 and len({c['mode'] for c in cases})==19
    n13,n14=seal(a.normal,13),seal(a.normal,14)
    s14,s15,s16,s17=(seal(a.steady,g) for g in (14,15,16,17))
    for prev,now,bank in ((n13,n14,1),(s14,s15,0)):
        assert prev['bank']==now['bank']==bank and now['chunks']==0
        assert now['charge']==2240 and now['commands']==2
        assert any(v[1:]==[0x5000,2048,0] for v in now['items'])
    assert s16['bank']==0 and s16['commands']==s16['charge']==s16['chunks']==0
    assert s17['bank']==0 and s17['chunks']==0 and s17['charge']==2598
    lg=a.large
    l14,l15,l16,l17=(seal(lg,g) for g in (14,15,16,17))
    assert l14['bank']==0 and l15['bank']==1 and l15['chunks']==7
    assert l16['bank']==1 and l16['commands']==l16['chunks']==0
    assert l17['bank']==0 and l17['chunks']==7
    for mode in ('stop_steady','stop_steady_final'):
        rows=(a.remaining/mode/'bus.tsv').read_text().splitlines()
        last=list(map(int,rows[-1].split()))
        assert last[1:4]==[3,15,0xe4]
    wire=compare(a.normal,a.old_normal)
    assert wire['logical_bytes']==50217
    result=dict(passed=True,scope=__doc__,cases=cases,actual_acks=sum(c['acks'] for c in cases),
                committed_scenes=sum(c['commits'] for c in cases),golden_pixels=pixels,
                normal_b=n14,steady_a=s15,noop=s16,moved_rows=s17,
                large_change=l15,other_large_change=l17,wire=wire,
                client=rest['client'],source_sha256={name:sha(Path(__file__).parent/name) for name in
                    ('nes_rawsteady181.py','test_nes_rawsteady181.py','check_nes_rawsteady181.py')},
                full_arm=False,new_fit=False,hardware=False,physical_fps=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('passed','actual_acks','committed_scenes','golden_pixels')}))


if __name__=='__main__':main()
