# SPDX-License-Identifier: MIT
"""Decode the64-bit PPU snapshot; retain raw values and evidence boundaries."""
import argparse,json
from pathlib import Path
FIELDS=[('line',9),('dot',9),('background_pattern_table',1),('sprite_fetch',1),('rendering',1),('ale',1),('read_2007_pipeline',5),('write_2007_pipeline',5),('vram_address',14),('address_latch',8),('bus_pins',8),('prefetch_hint',1),('address_valid',1)]
def decode(value):
 assert 0<=value<1<<64
 result={}
 for name,width in reversed(FIELDS):result[name]=value&((1<<width)-1);value>>=width
 assert value==0
 return dict(reversed(list(result.items())))
def main():
 p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args()
 rows=dict(line.split('=',1) for line in a.report.read_text().splitlines() if '=' in line)
 assert rows['candidate']=='NES-GAME-154'
 result={'candidate':rows['candidate'],'rom_error':int(rows['run_rom_error']),'ppu_state_valid':int(rows['ppu_state_valid'])}
 if result['ppu_state_valid']==1:
  value=(int(rows['ppu_state_hi'],16)<<32)|int(rows['ppu_state_lo'],16)
  result.update(raw=f'{value:016x}',ppu=decode(value))
 result['scope']='State at first fault, not a request history or proof of physical root cause. Compare original address context and actual screen outcome.'
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
