"""Real CPU full-range/late cap, STOP/head, independent coverage and recovery."""
import argparse,inspect,json
from pathlib import Path
from types import SimpleNamespace
import check_nes_beam639 as beam
from check_nes_head637 import head_fixture
from check_nes_progress680_interior import prepare as interior_prepare,fixture
from test_nes_tile532_priority import prepare
from test_nes_idle524_priority import case
from test_nes_seal538_stop import exercise
from nes_raw506 import once,sha

def attempt(a,name,line,h,fault='late_stop',limit=1536,minimum=1536):
    s=inspect.getsource(beam.attempt).replace('1152',str(limit))
    old=f"word(0x4004+word(0x1252))>={limit} then"
    s=once(s,old,f"word(0x4004+word(0x1252))>={minimum} then")
    ns=dict(vars(beam));exec(compile(s,'complete685-beam','exec'),ns)
    return ns['attempt'](a,name,line,h,fault)

def run(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    source=a.out/'input';prepare(a.trace,source,False,map_first=True)
    records=[json.loads(x) for x in (source/'packets.jsonl').read_text().splitlines()];new=[]
    for gen in (905,906,907):
        rows=[r for r in records if int.from_bytes(bytes.fromhex(r[2])[8:10],'little')==gen]
        if gen==906:
            maps=[r for r in rows if bytes.fromhex(r[2])[:2]==bytes((2,2))]
            rows=rows[:1]+maps+[r for r in rows[1:] if r not in maps]
        for seq,r in enumerate(rows):
            b=bytearray.fromhex(r[2]);b[2:4]=seq.to_bytes(2,'little');r[2]=b.hex()
        new+=rows
    (source/'packets.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in new))
    sub=SimpleNamespace(trace=source,client=a.client,mesen=a.mesen,out=a.out/'beam');sub.out.mkdir()
    cal=attempt(sub,'calibration',247,200);rows=[]
    for event in ('latch','mdma'):
        delta=cal['beam'][event]['clock']-cal['beam']['entry']['clock']
        line,h=divmod(248*1364+1120-delta,1364)
        r=attempt(sub,event,line,h);assert r['beam'][event]['line']==248 and r['beam'][event]['h']>=1000
        assert r['race']['size']==1536 and r['beam']['last']['line']<262;rows.append(dict(case=event,**r))
    for fault in ('head','both'):
        r=attempt(sub,fault,line,h,fault);assert r['race']['size']==0;rows.append(dict(case=fault,**r))
    # The same accepted1536B range after248 must retain1152B partial progress.
    for name,line,h,minimum in [('late249',249,200,1536),('late252',252,200,1536),('oversize',247,200,1600)]:
        r=attempt(sub,name,line,h,limit=1152,minimum=minimum);assert r['race']['size']==1152
        rows.append(dict(case=name,**r))
    # Interior full1344B retire and whole64B: preserve all other live records.
    source=a.out/'interior-input';interior_prepare(a.trace,source);body=(a.client/'body.bin').read_bytes();races=[]
    for gen in (906,907):
        sub=SimpleNamespace(trace=source,client=a.client,mesen=a.mesen,out=a.out/f'map{gen}');sub.out.mkdir()
        for name in ('head','stop','both','late_head','late_stop','cold','bad_manifest'):
            def edit(s,l):return fixture(s,l,body).replace('1152','1536')
            r=case(sub,gen,name,edit_fixture=edit)
            if r['grant']:assert r['size']==(1344 if gen==906 else 64)
            races.append(dict(r,case=name));print(gen,name,'PASS',flush=True)
    sub=SimpleNamespace(trace=a.trace,client=a.client,mesen=a.mesen,out=a.out/'final');sub.out.mkdir()
    final=[exercise(sub,g,'final212') for g in (906,907)]
    result=dict(passed=True,client=sha(a.client/'sink165.sfc'),calibration=cal,beam=rows,interior=races,final_ACK_cancel=final,
        scope='Actual65816 with original program restored at aligned caller; fresh beam/PPU writes/STOP. Full1536 only through248, old1152 after248 or length>1536; full/partial range accounting and cold/independent coverage.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS685',len(rows)+len(races)+len(final),'CPU boundary cases')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
