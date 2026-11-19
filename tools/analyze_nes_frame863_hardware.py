"""Compare the returned 60 s board runs with MMC855/860 and preserve the raw-file identities."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean

from read_nes_frame862 import compare, decode


def fields(path):
    return dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line)


def analyze(folder):
    runs={}
    traces={}
    hashes={}
    for edition,control in ((855,False),(860,False),(862,False),(862,True),(863,False),(863,True)):
        key=f"{edition}-{'control' if control else 'mmc3'}"
        suffix=' (1)' if control else ''
        budget,game,progress=[folder/f'nes-{kind}-mmc{edition}{suffix}.txt'
                              for kind in ('budget','game-last','progress')]
        files=[budget,game,progress]
        b,g=fields(budget),fields(game)
        assert g['candidate']==f'NES-MMC{edition}' and g['loaded_bytes']==g['compared_bytes']=='393216'
        assert all(g[k]=='1' for k in ('verified','run_passed','stop_ok','base_restored','safe_to_reload'))
        assert all(g[k]=='0' for k in ('run_error','run_stop_error','trace_aborts'))
        assert b['failed_transfers']=='0' and 'stage=MENU_PREPARED' in progress.read_text()
        bins=[dict(zip(b['columns'].split(','),[int(v,16) for v in b[f'b{i:02}'].split(',')],strict=True))
              for i in range(12)]
        counts=list(map(int,b['display_1_30_60'].split(',')))
        mid=bins[7]
        runs[key]=dict(display_counts=counts,display_FPS=[counts[0]/29,counts[1]/30],
                       demo_frame_starts=[row['frames'] for row in bins[6:]],
                       demo_max_gaps_ms=[10*row['maxgap'] for row in bins[6:]],
                       mid_frames=mid['frames'],mid_budget_output_ms=10*mid['seal']/mid['frames'])
        if edition>=862:
            path=folder/f"nes-frame-{'ctl' if control else 'mmc'}{edition}.bin"
            files.append(path)
            trace=decode(path)
            assert trace['edition']==edition and trace['control']==control and not trace['dropped']
            rows=trace['rows']
            assert len(rows)==mid['frames'] and all('invalid' not in r for r in rows)
            assert all((a['gen']+1)&65535==b['gen'] for a,b in zip(rows,rows[1:]))
            assert all(sum(r[k] for r in rows)==mid[col] for k,col in [('map','mapdirty'),('BG','bg'),('OBJ','obj')])
            traces[key]=trace
            runs[key].update(mid_cycle_output_ms=mean(r['total'] for r in rows),
                             mid_probe_ms=mean(r['probe_ms'] for r in rows),mid_full_SEAL=sum(r['seal_B']==168 for r in rows))
            if not control:
                runs[key]['DMA_boundaries']=dict(Counter(r.get('boundary','none') for r in rows))
        hashes.update({file.name:hashlib.sha256(file.read_bytes()).hexdigest() for file in files})
    a,b=(traces[f'{n}-mmc3'] for n in (862,863))
    c,d=(traces[f'{n}-control'] for n in (862,863))
    widths=(1,1,1)
    # Same start tick and complete workload; local generation numbers may differ across boots.
    def key(r):return tuple(r[k] for k in ('tick','bank','BG','OBJ','map','seal_B'))
    cases=[(x,y) for x in a['rows'] for y in b['rows'] if key(x)==key(y) and y.get('boundary')=='OBJ -> raw']
    assert len(cases)==1
    x,y=cases[0]
    return dict(runs=runs,trace_exact=compare(a,b,widths),control_exact=compare(c,d,widths),
                trace_generation_work=compare(a,b,widths,True),control_generation_work=compare(c,d,widths,True),
                same_tick_OBJ_raw=[x,y],file_SHA256=hashes)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('logs',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(analyze(args.logs),indent=2)+'\n',encoding='utf8',newline='\n')
