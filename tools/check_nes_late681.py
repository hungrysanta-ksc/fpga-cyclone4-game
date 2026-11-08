"""Real beam/atomic DMA limits for the existing small-tile class, not extra VBlank."""
import argparse,inspect,json,shutil
from pathlib import Path
from types import SimpleNamespace
import check_nes_beam639 as beam
from test_nes_tile532_priority import prepare,fixture
from test_nes_idle524_priority import case
from nes_raw506 import once,sha


def tile_attempt(a,name,line,h,fault='late_stop'):
    # Reuse the verified caller-only phase aligner. The entire production body
    # is restored/compared on entry; real latch, DMA writes and STOP are traced.
    source=inspect.getsource(beam.attempt)
    source=once(source,'script=head_fixture(width(map_fixture(script,symbols),1152))',
                'script=fixture(script,symbols)')
    source=once(source,"script=once(script,'and mapTail() then','and mapTail() and word(0x4004+word(0x1252))>=1152 then')",'pass')
    source=once(source,"result['size']==1152","result['size']==160")
    env=dict(vars(beam));env['fixture']=fixture
    exec(compile(source,__file__,'exec'),env)
    return env['attempt'](a,name,line,h,fault)


def run(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    original=a.trace;single=a.out/'single-input';prepare(original,single,False)
    rows=[];sub=SimpleNamespace(trace=single,client=a.client,mesen=a.mesen,out=a.out/'races');sub.out.mkdir()
    for g in (906,907):
        for name in ('head','stop','both','late_head','late_stop','cold'):
            r=case(sub,g,name,edit_fixture=fixture);rows.append(r)
            print(g,name,'PASS',flush=True)
    # Directed maximum-size accepted command. Payload, descriptor and receiver
    # agree; STOP prevents this altered frame from being presented. Unmodified
    # captured 128/16B commands above cover exact pixels and cold restoration.
    maximum=a.out/'max-input';shutil.copytree(single,maximum)
    records=[json.loads(x) for x in (maximum/'packets.jsonl').read_text().splitlines()]
    for row in records:
        b=bytearray.fromhex(row[2])
        if b[0]==7 and int.from_bytes(b[8:10],'little')==906:
            assert int.from_bytes(b[14:16],'little')==128
            b[14:16]=(160).to_bytes(2,'little');row[2]=b.hex()
            row[3]=(bytes.fromhex(row[3])+bytes(range(32))).hex();break
    else:raise AssertionError('missing directed tile')
    (maximum/'packets.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in records))
    sub=SimpleNamespace(trace=maximum,client=a.client,mesen=a.mesen,out=a.out/'beam');sub.out.mkdir()
    cal=tile_attempt(sub,'calibration',251,200);b=cal['beam'];edges={}
    for event in ('mdma','latch'):
        offset=b[event]['clock']-b['entry']['clock']
        line,h=divmod(252*1364+1120-offset,1364)
        r=tile_attempt(sub,event,line,h)
        e=r['beam'][event];assert e['line']==252 and 1000<e['h']<1364,e
        edges[event]=r
    sub.trace=single
    for fault in ('head','both'):
        r=tile_attempt(sub,fault,line,h,fault)
        assert r['race']['size']==0 and 'mdma' not in r['beam'];edges[fault]=r
    result=dict(client=sha(a.client/'sink165.sfc'),passed=True,races=rows,calibration=cal,late=edges,
        scope='Actual 65816; unmodified captured tile races/cold recovery plus directed160B accepted payload at actual252-line latch/MDMA. No final display of synthetic160B frame.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
