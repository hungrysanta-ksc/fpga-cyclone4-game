# SPDX-License-Identifier: MIT
"""Parse bounded210 post-STOP bins; never label ROM reuse model as real FPS.
Use video elapsed-time context to select sustained-scroll bins.10ms ticks
cannot certify60Hz jitter. Incomplete frames and bin edges remain explicit.
"""
from pathlib import Path
import argparse,json
FIELDS='frames recv plan seal maxgap ingress e8 e9 e0 e1 other plans out reuse reuseplan complex bg obj mapdirty'.split()
def analyze(path):
 raw=path.read_text(encoding='utf-8-sig');d=dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
 assert d['budget_schema']=='210' and d['values']=='HEX32' and d['columns']==','.join(FIELDS)
 bins=[]
 for i in range(12):
  parts=d[f'b{i:02}'].split(',');assert len(parts)==len(FIELDS) and all(len(x)==8 for x in parts)
  row=dict(zip(FIELDS,(int(x,16) for x in parts)));assert all(x<=0xffffffff for x in row.values())
  clock=sum(row[x] for x in ['ingress','e8','e9','e0','e1','other']);n=row['frames']
  assert row['reuse']<=row['out'] and row['complex']<=row['out']
  # Model omits bank/slot ownership and metadata/dirty API implementation.
  # Subtract ONLY equal-key plan payload, never imaginary poll/ACK savings.
  remaining=max(0,clock-row['reuseplan'])
  row.update(frame_start_window_seconds=[i*5,(i+1)*5],scene='UNCLASSIFIED',clocked_bytes=clock,
   actual_spi_floor_ms_per_completed=clock*8000/2625000/n if n else None,
   hypothetical_plan_only_floor_ms_per_completed=remaining*8000/2625000/n if n else None,
   max_display_gap_ms=row['maxgap']*10,complete_window=False)
  bins.append(row)
 return dict(schema=210,bins=bins,open_frame=int(d['open']),failed_transfers=int(d['failed_transfers']),
  physical_scroll_classified=False,adopt_reuse=False,fps60_proven=False,
  limitations=['frame-start bins may finish beyond their5s edge; no instantaneousFPS',
   'failed/partial next frame can contribute bytes without a displayed frame',
   '256-entry direct cache MODEL: collisions underestimate possible reuse; no live-slot/base/eviction proof',
   'immutable ROM-session keys only; not CHR-RAM or mapper-state compatibility proof',
   'source read misses, SNES compare/fallback/VBlank counts remain unmeasured',
   'only runtime transfer wrapper bytes; separate service/audio SPI traffic excluded',
   '10ms timestamps cannot certify16.67ms cadence; no median/p95 available'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();r=analyze(a.log)
 s=json.dumps(r,indent=2);a.out.write_text(s+'\n',encoding='utf8') if a.out else print(s)
