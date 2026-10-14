# SPDX-License-Identifier: MIT
"""Decode schema2 event records; neither per-frame telemetry nor measured FPS."""
from pathlib import Path
import argparse,json,re

FIELDS=[('kind',2),('generation_mod256',8),('errors',25),('first_line',9),('first_dot',9),
        ('first_mask',8),('rows',8),('groups',6),('objects',8),('exceptions',8),('palettes_saturated31',5)]


def record(raw):
    assert re.fullmatch('[0-9a-fA-F]{24}',raw)
    v=int(raw,16);remaining=96;r={}
    for n,bits in FIELDS:
        remaining-=bits;r[n]=(v>>remaining)&((1<<bits)-1)
    assert remaining==0 and r['kind'] in [1,2]
    r['event']='REJECT' if r['kind']==1 else 'RECOVERY'
    e=r['errors'];r.update(rom_fault=bool(e>>24),fetch_errors=e&255,compact_errors=(e>>8)&255,raster_errors=(e>>16)&255)
    r['position_observed']=r['first_line']!=511
    return r


def decode(text):
    kv=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
    assert kv['ppu_history_kind']=='LAST16_REJECT180_V2','wrong history schema'
    assert kv['ppu_history_valid']=='1','invalid/absent optional history'
    count=int(kv['ppu_history_count']);assert 0<=count<=16
    rows=[(int(k),v) for k,v in re.findall(r'^ppu_history_(\d+)=(\w+)$',text,re.M)]
    assert [i for i,_ in rows]==list(range(count)),rows
    return dict(events=[record(v) for _,v in rows],flags=int(kv['ppu_history_flags']),
                scope='last16 reject-signature changes/recoveries after a valid frame; first observed error clock, not original write; generation modulo256; counts at seal; not FPS')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('log',type=Path);a=p.parse_args()
    print(json.dumps(decode(a.log.read_text(encoding='utf8')),ensure_ascii=False,indent=2))
