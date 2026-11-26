"""Pair the physical input completion clock with SEAL and publication on both boards."""
import argparse
import hashlib
import json
from pathlib import Path

from read_nes_tail1012 import decode
from read_nes_ingress1029 import boundaries


def compare(directory):
    runs={}
    hashes={}
    for edition in (1025,1028):
        for trial in (1,2):
            file,=directory.glob(f'nes-frame-mmc{edition}-{trial}*.bin')
            data=file.read_bytes()
            hashes[f'{edition}-{trial}']=hashlib.sha256(data).hexdigest()
            rows={}
            for index,row in enumerate(decode(data,edition)['rows']):
                b=boundaries(data,index,row)
                if b is not None:
                    slot=row['tick']//40
                    assert slot not in rows
                    rows[slot]=dict(tick=row['tick'],generation=row['generation'],
                                    work=[row[f] for f in ('BG','OBJ','map','tiles','chunks')],**b)
            runs[edition,trial]=rows
    comparisons=[]
    for ref in (1,2):
        for candidate in (1,2):
            a,b=runs[1025,ref],runs[1028,candidate]
            pairs=[]
            for k in sorted(a.keys()&b.keys()):
                x,y=a[k],b[k]
                if x['work']!=y['work']:
                    continue
                if y['previous_show_to_ACK_ms']-x['previous_show_to_ACK_ms']<12:
                    continue
                xl,xh=x['previous_show_to_input_complete_ms']
                yl,yh=y['previous_show_to_input_complete_ms']
                pairs.append(dict(ticks=[x['tick'],y['tick']],late_input_ms=[yl-xh,yh-xl]))
            comparisons.append(dict(reference=ref,candidate=candidate,late_ACK_pairs=pairs))
    return dict(hashes=hashes,case_4361={f'{e}-{t}':runs[e,t][109] for e,t in runs},
                comparisons=comparisons,clock_resolution_ms=32768/84000)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    args.output.write_text(json.dumps(compare(args.directory),indent=2)+'\n',encoding='utf8')
