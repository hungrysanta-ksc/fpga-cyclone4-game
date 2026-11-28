"""Compare a completed Kirby debug run with both physical MMC1035 runs."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import median
from read_nes_kirby1034 import decode, MS

def intervals(row):
    return [row['banks'][-1]['return_tick'],row['SEAL_tick'],row['show_tick'],row['final_ACK_tick']]

def compare(frame,last,baseline):
    text=dict(field.split('=',1) for field in last.read_text().split())
    if (text['id'],text['crc'],text['err'],text['rom'],text['se'],text['start'],text['stop'],
        text['base'],text['menu'])!=('7c','248c7140','0','0','00','1','1','1','PREPARED_RESET_HELD'):
        raise ValueError('not a completed Kirby run')
    fps=[int(text[k])/seconds for k,seconds in [('w1',29),('w2',30)]]
    new=decode(frame.read_bytes(),1054)['rows']
    history=json.loads((Path(__file__).resolve().parents[1]/'analysis/kirby1035-hardware.json').read_text(encoding='utf8'))
    output=[]
    for file in baseline:
        data=file.read_bytes()
        ref=next(r for r in history if r['edition']==1035 and r['files']['frame']==hashlib.sha256(data).hexdigest())
        old=decode(data,1035)['rows']
        def samples(rows):
            return [r for r in rows if 'banks' in r and r['banks'] and 5500<=r['tick']<6000]
        def key(r):
            return tuple(r[k] for k in ('tiles','chunks','BG','OBJ','map','bank'))
        available=samples(old)
        diffs=[]
        for row in samples(new):
            group=[r for r in available if key(r)==key(row) and abs(r['tick']-row['tick'])<=100]
            if not group:continue
            match=min(group,key=lambda r:abs(r['tick']-row['tick']))
            available.remove(match)
            diffs.append([(b-a)*MS for a,b in zip(intervals(match),intervals(row))])
        output.append(dict(reference_run=ref['run'],reference_fps=ref['fps'],
                           fps_delta=[round(b-a,3) for a,b in zip(ref['fps'],fps)],
                           matched_55_60s=len(diffs),median_delta_ms_from_previous_show=
                           dict(zip(('last_tile_return','SEAL','show','final_ACK'),map(median,zip(*diffs)))) if diffs else None))
    return dict(display_fps=[round(x,3) for x in fps],reference=output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('frame',type=Path);p.add_argument('last',type=Path)
    p.add_argument('baseline',type=Path,nargs=2)
    a=p.parse_args()
    print(json.dumps(compare(a.frame,a.last,a.baseline),indent=2))
