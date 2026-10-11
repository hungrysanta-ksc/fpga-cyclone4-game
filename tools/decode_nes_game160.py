# SPDX-License-Identifier: MIT
"""Decode160's unchanged157 history format, accepting only the160 identity."""
import argparse,json,re
from pathlib import Path
from decode_nes_game157 import decode

def main():
 p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args()
 f=dict(line.split('=',1) for line in a.report.read_text().splitlines() if '=' in line)
 assert f['candidate']=='NES-GAME-160' and f['board_observed_hex']=='69' and f['observer_id_hex']=='e3'
 result={'valid':int(f['ppu_history_valid']),'scope':'16 consecutive NES clocks, oldest first. Not CPU instruction or physical button timestamps.'}
 if result['valid']:
  count=int(f['ppu_history_count']);flags=int(f['ppu_history_flags']);assert 0<=count<=16 and flags&~3==0 and (not count or flags&1)
  rows=[]
  for i in range(count):
   raw=f[f'ppu_history_{i:02d}'];assert re.fullmatch('[0-9a-fA-F]{24}',raw)
   rows.append(dict(index=i,relative_clock=i-count+1,raw=raw,**decode(int(raw,16))))
  result.update(fault_edge_included=bool(flags&2),rows=rows)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
