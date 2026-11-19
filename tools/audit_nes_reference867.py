"""Compare release identity, hardware counters and same-bank map traffic without changing firmware."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def release(archive, source):
    reference = json.loads((ROOT/'analysis/reference658-verification.json').read_bytes())
    assert digest(archive.read_bytes()) == reference['release']
    with ZipFile(archive) as z:
        for name, expected in reference['assets'].items():
            data = z.read('sd2snes/' + name)
            assert digest(data) == expected['sha256'] and len(data) == expected['bytes']
        perf_image = any(n.endswith('nes_snes_perf.bin') for n in z.namelist())
    details = json.loads((ROOT/'analysis/reference669-review.json').read_bytes())
    for name, expected in details['upstream_files'].items():
        path = source/name
        if not path.exists():
            path = source/path.name
        assert digest(path.read_bytes()) == expected['SHA256']
    return dict(zip_SHA256=reference['release'], source_commit=reference['source_commit'],
                verified_files=list(reference['assets']), separate_perf_image=perf_image)


def hardware(path):
    data = path.read_bytes()
    fields = dict(s.split('=',1) for s in data.decode().splitlines() if '=' in s)
    assert fields['cost_counter_available']=='1' and fields['cost_clock_hz']=='84000000'
    buckets = {}
    order = fields['cost_op_order'].split(',')
    for index, op in enumerate(order):
        calls, size, hi, lo, _ = map(int, fields[f'cost_op_{index:02}'].split(','))
        buckets[op] = (calls, size, (hi << 32) + lo)
    displayed = buckets['EA'][0]
    ops = {k:dict(calls_per_EA=round(c/displayed,3), bytes_per_EA=round(b/displayed,3),
                  ms_per_EA=round(t/84000/displayed,3)) for k,(c,b,t) in buckets.items()}
    counts = list(map(int, fields['display_1_30_60'].split(',')))
    return dict(sha256=digest(data), displays=counts, FPS=[round(c/n,3) for c,n in zip(counts,[29,30])],
                EA=displayed, ops=ops, all_ops_ms_per_EA=round(sum(v[2] for v in buckets.values())/84000/displayed,3))


def maps(temp, package):
    source = temp/'nes-ack861'
    index = json.loads((source/'index.json').read_bytes())
    frames = index['clips']['demo']['frames']
    assert [r['source'] for r in frames] == list(range(2120,2365,4))
    snapshots = []
    for r in frames:
        data = (source/f"capture/state-{r['source']:04d}.bin").read_bytes()
        assert len(data)==2384 and digest(data)==r['state']
        snapshots.append(data)
    with ZipFile(package) as z:
        manifest = json.loads(z.read('manifest.json'))
    assert manifest['edition']==866 and index['rom']==manifest['checks']['loader']['rom']
    results = []
    for phase in (1,2):
        folder = temp/f'nes-tile821-demo-jointmirror-p{phase}-866-on'
        joint = json.loads((folder/'joint.json').read_bytes())
        assert joint['passed'] and joint['commits']==62 and joint['firmware_SHA256']==manifest['ARM']
        assert joint['client_SHA256']==manifest['client']
        counts,wire,bank = Counter(),Counter(),{}
        spi = [e for e in json.loads((folder/'events.json').read_bytes()) if e.get('opcode')=='0xe1']
        for entry,event in zip((folder/'packets.jsonl').read_text().splitlines(),spi,strict=True):
            _,arrival,h,_ = json.loads(entry)
            b = bytes.fromhex(h)
            g = int.from_bytes(b[8:10],'little')
            assert len(b)+3==event['bytes'] and abs(arrival-event['clock'])<=1
            if b[0]==1:
                bank[g] = b[18]
            if b[1]==2 and b[0] in (2,4,9):
                counts[g]+=1
                wire[g]+=event['bytes']
        rows = []
        for i in range(2,len(frames)):
            g = 905+i
            assert bank[g]==bank[g-2]!=bank[g-1]
            a,b = snapshots[i-2],snapshots[i]
            prior = (folder/f'map-{g-2}.bin').read_bytes()
            target = (folder/f'map-{g}.bin').read_bytes()
            assert len(target)==len(prior)==4096
            words = [j for j in range(0,4096,2) if prior[j:j+2]!=target[j:j+2]]
            patch = b''.join(j.to_bytes(2,'little')+target[j:j+2] for j in words)
            restored = bytearray(prior)
            for j in range(0,len(patch),4):
                at = int.from_bytes(patch[j:j+2],'little')
                restored[at:at+2] = patch[j+2:j+4]
            assert restored==target and 8+len(patch)<=240
            rows.append(dict(source=frames[i]['source'], native_NT_bytes=sum(x!=y for x,y in zip(a[:2048],b[:2048])),
                             snes_words=len(words), map_E1_B=wire[g], map_packets=counts[g],
                             illustrative_wire_B=19+8+len(patch) if words else 0))
        results.append(rows)
    assert results[0]==results[1]
    rows=results[0]
    return dict(rom=index['rom'], sampled_stride=4, matched_phases=2, frames=len(rows),
                totals={k:sum(r[k] for r in rows) for k in rows[0] if k!='source'},
                active_frames=sum(bool(r['snes_words']) for r in rows), max_words=max(r['snes_words'] for r in rows),
                per_frame=rows)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('archive','source','temp','logs','package','out'):
        p.add_argument('--'+arg,type=Path,required=True)
    args=p.parse_args()
    result=dict(release=release(args.archive,args.source),hardware={
        n:hardware(args.logs/f'nes-budget-mmc{n}.txt') for n in (855,866)}, demo=maps(args.temp,args.package))
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
