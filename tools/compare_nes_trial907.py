"""Compare the selected physical OBJ workloads and completion windows of 905 and 907."""
import argparse
import json
from pathlib import Path
from read_nes_supply905 import decode
from nes_windows518 import duration_ms, fps_delta, windows


def capture(folder, edition):
    def text(name):
        return (folder/f'nes-{name}-mmc{edition}.txt').read_text(encoding='utf-8-sig')
    game=dict(l.split('=',1) for l in text('game-last').splitlines() if '=' in l)
    elapsed=duration_ms(text('progress'))
    if game.get('candidate')!=f'NES-MMC{edition}' or game.get('safe_to_reload')!='1':
        raise ValueError('wrong edition or incomplete base recovery')
    shown=windows(text('budget'),elapsed)
    data=decode(folder/f'nes-frame-mmc{edition}.bin',edition)
    if not shown or data['mode']!=0 or any(data['dropped']) or any('invalid' in r for r in data['rows']):
        raise ValueError('requires a complete normal-mode capture')
    detailed=[r for r in data['rows'] if 'detail' in r]
    result=dict(display_windows=shown,display_count_55_60=data['displayed55'],
                frame_starts_55_60=len(data['rows']),window_display_FPS_55_60=None)
    if data['displayed55'] is not None:
        result['window_display_FPS_55_60']=data['displayed55']/5
    elif (data['rows'] and 5500<=int(game['profile_last_display_tick'])<6000):
        # One budget frame can be open at 55s. The recorded final display
        # is before 60s, so every recorded start here completed in-window.
        n=len(data['rows'])
        result['display_FPS_55_60_bounds']=[n/5,(n+1)/5]
    if not detailed:
        result['workload']=None
        return result
    row,=detailed
    meta={k:row[k] for k in ('tick','generation','BG','OBJ','map','tiles','chunks','last_bytes','last_offset',
                              'E9_to_last_publish_ms','input_to_final_ACK_ms','probe_total_ms')}
    detail=row['detail']
    meta['shape']=[[c['kind'],c['bytes']] for c in detail]
    meta['ROM_grants_by_chunk']=[c['ROM_grants'] for c in detail]
    meta['ROM_grants']=sum(meta['ROM_grants_by_chunk'])
    result['workload']=meta
    return result


def compare(old,new):
    a,b=old['workload'],new['workload']
    result=dict(MMC905=old,MMC907=new,display_FPS_deltas=fps_delta(old['display_windows'],new['display_windows']))
    if 'display_FPS_55_60_bounds' in old and new['window_display_FPS_55_60'] is not None:
        result['display_FPS_delta_55_60_bounds']=[round(new['window_display_FPS_55_60']-v,3)
                                                for v in reversed(old['display_FPS_55_60_bounds'])]
    if not (a and b):
        result['workload_comparison']='missing detailed capture'
        return result
    keys=('BG','OBJ','map','tiles','chunks','last_bytes','last_offset','shape')
    different={k:[a[k],b[k]] for k in keys if a[k]!=b[k]}
    result.update(workload_differences=different,start_tick_difference=b['tick']-a['tick'])
    if not different and abs(b['tick']-a['tick'])<=30:
        result['matched_deltas_907_minus_905']={k:round(b[k]-a[k],3) for k in
            ('ROM_grants','E9_to_last_publish_ms','input_to_final_ACK_ms')}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline_folder',type=Path)
    p.add_argument('trial_folder',type=Path)
    a=p.parse_args()
    print(json.dumps(compare(capture(a.baseline_folder,905),capture(a.trial_folder,907)),indent=2))
