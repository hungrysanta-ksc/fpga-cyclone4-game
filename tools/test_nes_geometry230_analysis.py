# SPDX-License-Identifier: MIT
"""Reject damaged packet contents, geometry and raw-screen evidence."""
from pathlib import Path
import argparse, hashlib, json, shutil
from analyze_nes_geometry230 import analyze, sha


def main():
    p=argparse.ArgumentParser()
    for n in ('host','capture','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    original={str(f):sha(f) for d in (a.host,a.capture) for f in d.iterdir() if f.is_file()}
    outcomes=[]
    for label in ('packet','geometry','raw_rgb'):
        d=a.out/label;h=d/'host';c=d/'capture';h.mkdir(parents=True);c.mkdir()
        for f in a.host.iterdir():
            if f.name in ('result.json','cost.csv') or f.name.startswith('frame'):shutil.copyfile(f,h/f.name)
        for f in a.capture.glob('frame-*.rgb'):shutil.copyfile(f,c/f.name)
        f=h/'frame907.packets' if label=='packet' else h/'frame907.geometry' if label=='geometry' else c/'frame-0907.rgb'
        b=bytearray(f.read_bytes())
        if label=='packet':
            # First record is BEGIN. Damage the following map DATA payload,
            # with lengths and frame identity preserved.
            pos=2+int.from_bytes(b[:2],'little')+2+16;b[pos]^=1
        elif label=='geometry':b[3872+(193-8)*8+6]^=2
        else:b[193*768]^=1
        f.write_bytes(b)
        if label!='raw_rgb':
            # Update outer artifact digest to exercise semantic comparison,
            # rather than merely detecting a stale manifest.
            meta=json.loads((h/'result.json').read_text());meta['evidence_files'][f.name]=sha(f)
            (h/'result.json').write_text(json.dumps(meta))
        try:analyze(h,c)
        except AssertionError as e:outcomes.append(dict(case=label,rejected=True,reason=str(e)))
        else:raise AssertionError(label+' unexpectedly accepted')
    assert all(sha(Path(p))==v for p,v in original.items()),'source evidence mutated'
    result=dict(passed=True,cases=outcomes,source_files_unchanged=len(original),script_sha256=sha(Path(__file__)))
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
