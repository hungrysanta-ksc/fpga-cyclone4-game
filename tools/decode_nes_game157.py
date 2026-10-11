# SPDX-License-Identifier: MIT
"""Decode chronological157 history. Last row is fault edge only with flag bit1."""
import argparse,json,re
from pathlib import Path
FIELDS=[('line',9),('dot',9),('flags',12),('transaction_address',22),('hint_address',22),('ppu_address',22)]
FLAGS=['request','response','ready','busy','pending_ppu','cpu_need','cpu_sample','ppu_sample','ppu_valid','hint_valid','use_prefetch','prefetch_hit']
def decode(value):
 assert 0<=value<1<<96
 row={}
 for key,bits in reversed(FIELDS):row[key]=value&((1<<bits)-1);value>>=bits
 for i,name in enumerate(FLAGS):row[name]=(row['flags']>>(11-i))&1
 return row
def main():
 p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args()
 f=dict(line.split('=',1) for line in a.report.read_text().splitlines() if '=' in line)
 assert f['candidate']=='NES-GAME-157' and f['board_observed_hex']=='66' and f['observer_id_hex']=='e0'
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
