# SPDX-License-Identifier: MIT
"""Decode only the immutable139 first-event context from a final TXT."""
from pathlib import Path
import argparse,json
def decode(text):
 f=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
 assert f['candidate']=='NES-SCREEN-139' and f['board_observed_hex']=='5b' and f['observer_id_hex']=='d6'
 valid=int(f['fault_context_valid']);assert valid in (0,1)
 c=(int(f['fault_context_hi'],16)<<32)|int(f['fault_context_lo'],16)
 assert 0<=c<1<<63
 result=dict(first_run_error=int(f['run_first_error']),stop_error=int(f['run_stop_error']),rom_error=int(f['run_rom_error']),context_valid=bool(valid))
 if valid:
  result.update(cpu_address=f"0x{c&0x1ffffff:07x}",pending_address=f"0x{(c>>25)&0x3fffff:06x}",age_nes_clocks=(c>>47)&255)
  for i,n in enumerate(['ppu_valid','cpu_valid','ppu_sample','cpu_sample','rom_response','rom_ready','pending_ppu','busy']):result[n]=bool(c&(1<<(55+i)))
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args();print(json.dumps(decode(a.report.read_text()),indent=2))
