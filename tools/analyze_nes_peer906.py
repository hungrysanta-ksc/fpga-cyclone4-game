"""Keep board measurements, count-matched RTL, and linked game schedules distinct."""
import json
import re
import sys
from pathlib import Path

from analyze_nes_output822 import CLK_MS, resources, sha
from read_nes_supply905 import MS, decode


def read(path):
    return json.loads(path.read_bytes())


def physical(trace):
    row, = [r for r in decode(trace)['rows'] if 'detail' in r]
    chunk, = [c for c in row['detail'] if c['bytes']==608]
    long = []
    for i,t in enumerate(chunk['tiles'],1):
        if not t['grants']:
            continue
        a,b=t['first_grant_ms'],t['last_grant_ms']
        if b-a < 8:
            continue
        # 18 eligible NTSC scanlines. Allow 1 timestamp bin on relative
        # endpoints, and 1024 NES cycles for local byte work/mailbox overlap.
        # Assumes continuous clocks and no fault. These are intervals, not
        # timestamps of an observed interior grant or a sampled CHR address.
        window=18*341*4/CLK_MS
        local=1024/CLK_MS
        def bounds(lo,hi):
            return [round(lo-.001,3),round(hi+.001,3)]
        long.append(dict(tile=i,grants=t['grants'],first_ms=a,last_ms=b,
                         next_window_request_ms=bounds(a-MS,a+MS+window+local),
                         next_window_grant_ms=bounds(b-MS-window,b+MS)))
    assert [r['tile'] for r in long]==[2,5,9,15]
    assert sum(t['grants'] for t in chunk['tiles'])==204
    return dict(trace=sha(trace),generation=row['generation'],token=chunk['token'],tiles=long,
                first_E9_to_last_OBJ_ms=row['E9_to_last_publish_ms'])


def rtl(temp,baseline):
    measured=baseline['tiles']
    p=temp/'nes-peer906'
    counts=[int(s,16) for s in (p/'byte/counts.hex').read_text().splitlines()]
    rows=[]
    for phase in (1,2):
        for pattern in range(3):
            summary={}
            for variant in ('byte','pair'):
                path=p/variant
                log=(path/f'run-{phase}-{pattern}.log').read_text(errors='replace')
                assert 'PASS906' in log and 'Errors: 0,' in log
                tiles=[tuple(map(int,line)) for line in re.findall(r'^# TILE (\d+) (\d+) (\d+)$',log,re.M)]
                assert [i for i,_,_ in tiles]==list(range(31))
                if variant=='byte':
                    assert [n for _,n,_ in tiles]==counts
                lines=(path/f'requests-{phase}-{pattern}.tsv').read_text().splitlines()
                # Stop before the independent full-form/STOP/cold guard rows.
                grants=[tuple(map(int,line.split())) for line in lines[:sum(n for _,n,_ in tiles)]]
                assert all(req<=g for _,_,_,req,g in grants)
                split=[]
                for target in measured:
                    requests=[e for e in grants if e[0]==7+target['tile'] and e[2]>=0]
                    if requests:
                        _,n,prev,req,grant=max(requests,key=lambda e:e[4]-e[2])
                        split.append([target['tile'],n+1,prev,req,grant])
                summary[variant]=dict(grants608=sum(n for _,n,_ in tiles[8:27]),
                    all_grants=len(grants),last_tile_clocks=tiles[-1][-1],long_pairs=split,
                    observations_sha256=sha(path/f'requests-{phase}-{pattern}.tsv'))
            rows.append(dict(phase=phase,pattern=pattern,**summary))
    return rows


def linked(temp):
    rows=[]
    for phase in (1,2):
        for cache in ('warm','cold'):
            runs={}
            counts=[]
            for mode in ('byte','pair'):
                p=temp/f'nes-tile821-obj-jointmirror-p{phase}-906-{cache}-{mode}'
                j=read(p/'joint.json')
                assert j['passed'] and j['commits']==8 and j['last_status']==1
                assert j['firmware_SHA256']=='85514172e0706cff40e444d539ea31890c57a23172645586dd8e3f8cc2d10765'
                assert read(p/'verified905.json')['RGB']==8
                grants=read(p/'grants904.json')
                jobs=[json.loads(line) for line in (p/'producer.jsonl').read_text().splitlines()]
                display=read(p/'verified905.json')['intervals'][1]
                emitted={}
                for f in j['frames']:
                    g=f['generation']
                    tiles=[e for e in jobs if e['generation']==g]
                    obj=[e for e in tiles if e['kind']==1]
                    emitted[g]=dict(obj_bytes=sum(e['bytes'] for e in obj),last_OBJ=obj[-1]['producer'],
                                    grants=sum(k==1 and tag==g for tag,k,*_ in grants),ack=f['ACK_masterclock'])
                counts.append([(sum(e['bytes'] for e in jobs if e['generation']==g and e['kind']==k),
                                sha(p/f'frame-{g}.rgb'),sha(p/f'expected-{g}.bin'),sha(p/f'map-{g}.bin'))
                               for g in emitted for k in (0,1)])
                runs[mode]=dict(frames=emitted,display=display,final_ACK=j['frames'][-1]['ACK_masterclock'],
                    dma_bytes=j['vram_DMA_B'],client=j['client_SHA256'])
            assert counts[0]==counts[1]
            assert runs['byte']['client']==runs['pair']['client'] and runs['byte']['dma_bytes']==runs['pair']['dma_bytes']
            rows.append(dict(phase=phase,cache=cache,**runs))
    return rows


def directed(temp):
    result=[]
    for mode in ('byte','pair'):
        for phase in (1,2):
            p=temp/'nes-peer906'/mode
            assert 'PASS906 directed' in (p/f'edge-{phase}.log').read_text(errors='replace')
            events=[tuple(map(int,l.split())) for l in (p/f'edge-{phase}.tsv').read_text().splitlines()]
            for tile in (2,5,9,15):
                e=[v for v in events if v[0]==tile+7 and v[2]>=0]
                _,n,prev,req,grant=max(e,key=lambda v:v[4]-v[2])
                assert req>=prev and grant-req>300000
                result.append(dict(mode=mode,phase=phase,tile=tile,grant_number=n+1,
                                   previous_grant=prev,next_request=req,next_grant=grant))
    return result


if __name__=='__main__':
    temp,trace,out=map(Path,sys.argv[1:])
    measured=physical(trace)
    result=dict(physical=measured,rtl=rtl(temp,measured),directed=directed(temp),linked=linked(temp))
    result['fit']={str(n):resources(temp,str(n)) for n in (905,906)}
    for n in (905,906):
        project=temp/f'nes-trial816-board{n}'
        assert all(s>0 for s in result['fit'][str(n)]['min_slack_ns'].values())
        target={}
        for name in ('io612','paths612','paths801','phase801','reader661','word660'):
            lines=(project/f'{name}.tsv').read_text().splitlines()
            col=3 if name=='phase801' else 2
            target[name]=min(float(l.split('\t')[col]) for l in (lines if col==3 else lines[1:]))
        result['fit'][str(n)]['target_slack_ns']=target
    for name in ('nes_tile205.sv','nes_source_tile192.sv'):
        assert sha(temp/'nes-peer906/pair'/name)==sha(temp/'nes-trial816-board906'/name)
    manifest=read(Path(__file__).resolve().parents[1]/'analysis/supply905-package.json')
    proof=Path(__file__).resolve().parents[2]/'probes/nes-supply905/proof'
    for file in ('sram.json','loader.json','timer.json','menu.json','base/result.json'):
        assert sha(proof/file)==manifest['proof'][file]
    assert sha(temp/'nes-trial816-board905/sink-program.hex')==sha(temp/'nes-trial816-board906/sink-program.hex')
    result['retained_proof']=dict(ARM=manifest['ARM'],flash_bytes=manifest['flash_B'],
                                  sink_rom=sha(temp/'nes-trial816-board906/sink-program.hex'))
    out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
