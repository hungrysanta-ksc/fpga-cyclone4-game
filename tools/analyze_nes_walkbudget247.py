# SPDX-License-Identifier: MIT
"""Conditional same-frame serial wire+post-SEAL walk scenarios, not FPS/WCET."""
from pathlib import Path
import argparse,csv,json
from nes_delta231 import BASE,sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('walk','prior','relocation','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    walk=json.loads(a.walk.read_text(encoding='utf-8'));prior=json.loads(a.prior.read_text(encoding='utf-8'))
    relocation=list(csv.DictReader(a.relocation.open(encoding='utf-8',newline='')))
    rows=[];names=('full_codec_original16','semantic_shift_batched16','semantic_shift_sparse_raw_ceiling_batched16')
    for w,old,rel in zip(walk['rows'],prior['rows'],relocation):
        assert w['frame']==old['frame']==int(rel['frame'])
        row=dict(frame=w['frame'],measured_walk_ms=w['scan_ms'])
        for name in names:
            count=old['spi']['ready4_bytes'] if name==names[0] else int(rel[name+'.ready4'])
            row[name+'.ready4_wire_bytes']=count
            row[name+'.serial_wire_plus_walk_ms']=count*8/2625+w['scan_ms']
        rows.append(row)
    models={}
    for name in names:
        values=[r[name+'.serial_wire_plus_walk_ms'] for r in rows[2:]]
        models[name]=dict(minimum_ms=min(values),maximum_ms=max(values),
                         over_16_67_frames=[r['frame'] for r in rows[2:] if r[name+'.serial_wire_plus_walk_ms']>1000/60])
    result=dict(stage=247,passed=True,scope=__doc__,frames=len(rows),models=models,
        assumptions=['Ready4 modeled wire at2.625MHz and measured post-SEAL walk are serialized for a single-frame transaction.',
                     'No new cross-frame SPI/target ownership overlap is assumed. Such overlap needs an explicit schedule and lifetime proof.',
                     'Semantic input/raw relocation are unimplemented models; current walk measurements are only a conditional retained-consumer cost.'],
        exclusions=['Source prepare/ARM execution and gaps','SNES coverage,packet processing,VBlank wait,DMA/final ACK','New parallel raw control/compute costs'],
        decision='None of these serialized retained-consumer scenarios provides a joint60Hz bound. Not an impossibility proof for pipelined or relocated designs.',
        product_changed=False,selected_implementation=None,rows=rows,
        input_hashes={p.resolve().relative_to(BASE).as_posix():sha(p) for p in (a.walk,a.prior,a.relocation)},
        analyzer_sha256=sha(Path(__file__)))
    raw=a.out/'result.json';raw.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    public={k:v for k,v in result.items() if k not in ('rows','input_hashes')};public['private_result_sha256']=sha(raw)
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    with (a.out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    print(json.dumps(public,indent=2))


if __name__=='__main__':main()
