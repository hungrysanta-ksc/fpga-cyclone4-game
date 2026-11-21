"""Compare physical 907/915 demo captures and bound the phase of COMMIT D2."""
import argparse
import json
import math
from pathlib import Path

from compare_nes_trial907 import capture
from nes_windows518 import fps_delta
from read_nes_supply905 import MS, decode

DOT=4000/21477272
PERIOD=262*341*DOT
HALF=PERIOD/2


def phase_bounds(row):
    """Positive means the nearest line 7 dot 257 opportunity is still ahead.

    A real fill grant qualifies in lines [242,260). The anchor is sampled
    inside the first 0x78 transaction. Both FPGA stamps truncate to 32768
    clocks. ARM stamps truncate to 512 clocks. Intersect all compatible
    phases, retaining split or ambiguous answers at frame wrap.
    """
    age=row.get('commit_age_ticks512')
    if age is None and 'commit_age_ticks512' in row:
        return dict(status='recorded COMMIT generation does not match')
    stamps=[t[k] for c in row['detail'] for t in c['tiles'] if t['grants']
            for k in ('first_grant_ms','last_grant_ms')]
    if not stamps:
        return dict(status='no physical ROM grant in selected detail')
    cycle=MS/64
    measured=age is not None
    low_age=age if measured else row['ACK_age_ticks512']
    high_age=age if measured else row['END_age_ticks512']
    if measured and 'commit_step_ticks512' in row:
        high_age+=1+row['commit_step_ticks512']
    query=row.get('first_query_ticks512',math.ceil((row['probe_total_ms']+0.0005)/cycle))
    if high_age*cycle>400 or (measured and query*cycle>row['probe_total_ms']+cycle):
        return dict(status='inconsistent ARM ages')
    if (high_age-low_age)*cycle>=PERIOD:
        return dict(status='END to final ACK spans a frame; COMMIT phase unresolved')
    remaining=[(-HALF,HALF)]
    for grant in stamps:
        age_at_anchor=row['E9_to_query_ms']-grant
        # Observer edge synchronizers, decimal decoding, possible odd-dot
        # shortening and up to 1000 ppm relative clock error across the span.
        error=MS+0.002+0.001*(high_age*cycle+abs(age_at_anchor)+PERIOD)
        lo=low_age*cycle-age_at_anchor+(262*341+7*341+257-260*341)*DOT-error
        hi=(high_age+query+2)*cycle-age_at_anchor+(262*341+7*341+257-242*341)*DOT+error
        overlap=[]
        for left,right in remaining:
            for turn in range(math.ceil((lo-right)/PERIOD),math.floor((hi-left)/PERIOD)+1):
                overlap.append((max(left,lo-turn*PERIOD),min(right,hi-turn*PERIOD)))
        remaining=[]
        for left,right in sorted(overlap):
            if remaining and left<=remaining[-1][1]:
                remaining[-1]=(remaining[-1][0],max(remaining[-1][1],right))
            else:
                remaining.append((left,right))
        if not remaining:break
    reference='ARM COMMIT receive step' if 'commit_step_ticks512' in row else 'ARM COMMIT D2 return'
    return dict(status='bounded' if remaining else 'inconsistent with nominal uninterrupted NTSC',
                reference=reference if measured else 'between END and final ACK',
                nearest_capture_minus_ARM_D2_ms=[[math.floor(l*1000)/1000,math.ceil(r*1000)/1000] for l,r in remaining])


def compare(old_dir,new_dir):
    a=capture(old_dir,907);b=capture(new_dir,915)
    result=dict(MMC907=a,MMC915=b,display_FPS_delta=fps_delta(a['display_windows'],b['display_windows']),
                FPS_delta_55_60=b['window_display_FPS_55_60']-a['window_display_FPS_55_60'])
    for directory,edition in ((old_dir,907),(new_dir,915)):
        rows=decode(directory/f'nes-frame-mmc{edition}.bin',edition)['rows']
        row=next((r for r in rows if 'detail' in r),None)
        result[f'MMC{edition}']['capture_phase']=phase_bounds(row) if row else dict(status='no complete detailed row')
    x,y=a['workload'],b['workload']
    if x and y:
        keys=('BG','OBJ','map','tiles','chunks','last_bytes','last_offset','shape')
        differences=[k for k in keys if x[k]!=y[k]]
        result.update(different_work=differences,start_delta_ticks=y['tick']-x['tick'])
        if not differences and abs(result['start_delta_ticks'])<=30:
            result['matched_deltas']={k:round(y[k]-x[k],3) for k in ('ROM_grants','E9_to_last_publish_ms','input_to_final_ACK_ms')}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('MMC907',type=Path);p.add_argument('MMC915',type=Path)
    a=p.parse_args()
    print(json.dumps(compare(a.MMC907,a.MMC915),indent=2))
