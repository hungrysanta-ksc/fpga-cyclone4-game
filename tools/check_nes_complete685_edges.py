"""Retain the late252 boundary and reject253 after sharing the beam sample."""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from check_nes_complete685 import attempt
from check_nes_head637 import head_fixture
from test_nes_tile532_edges import gate
from test_nes_idle524_priority import case
from nes_raw506 import sha

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    cal=attempt(a,'calibration',251,200,limit=1152);rows=[]
    for event in ('latch','mdma'):
        delta=cal['beam'][event]['clock']-cal['beam']['entry']['clock']
        line,h=divmod(252*1364+1120-delta,1364)
        r=attempt(a,event,line,h,limit=1152)
        assert r['beam'][event]['line']==252 and r['beam'][event]['h']>=1000
        assert r['race']['size']==1152 and r['beam']['last']['line']<262
        rows.append(dict(case=event,**r))
    body=(a.client/'body.bin').read_bytes();labels=json.loads((a.client/'labels.json').read_text())
    pc=0x7e2000+body.index(bytes.fromhex('ad1242'),labels['prefix523']-0x7e2000)
    sub=SimpleNamespace(**vars(a));sub.out=a.out/'reject253';sub.out.mkdir()
    r=case(sub,906,'stop',edit_fixture=lambda s,l:head_fixture(gate(s,l,253,'map',pc,1152,last_map_line=252)))
    assert r['grant']==0 and r['size']==0;rows.append(dict(r,case='reject253'))
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,client=sha(a.client/'sink165.sfc'),calibration=cal,cases=rows),indent=2)+'\n')
    print('PASS685 late252 and reject253',len(rows))
