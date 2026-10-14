# SPDX-License-Identifier: MIT
"""Schema3 episodes: no first-error position or intermediate error changes."""
from pathlib import Path
import argparse,json,re
from decode_nes_reject180 import record as prior_record

def record(raw):
    r=prior_record(raw)
    assert r.pop('first_line')==511 and r.pop('first_dot')==511,'schema3 reserved position'
    r['candidate_display_mask']=r.pop('first_mask')
    assert not r['position_observed']
    return r

def decode(text):
    kv=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
    assert kv['ppu_history_kind']=='LAST16_EPISODE180_V3','wrong history schema'
    assert kv['ppu_history_valid']=='1','invalid/absent optional history'
    count=int(kv['ppu_history_count']);assert 0<=count<=16
    rows=[(int(k),v) for k,v in re.findall(r'^ppu_history_(\d+)=(\w+)$',text,re.M)]
    assert [i for i,_ in rows]==list(range(count)),rows
    return dict(events=[record(v) for _,v in rows],flags=int(kv['ppu_history_flags']),scope='last16 first reject/recovery episodes after valid geometry; errors/counts at ownership; candidate display mask, not error-time mask; no error location or changes during rejection; generation modulo256; not FPS')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('log',type=Path);a=p.parse_args()
    print(json.dumps(decode(a.log.read_text(encoding='utf8')),ensure_ascii=False,indent=2))
