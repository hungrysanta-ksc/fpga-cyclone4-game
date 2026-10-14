# SPDX-License-Identifier: MIT
"""Decode177 last16 clock samples without treating them as event history."""
from pathlib import Path
import argparse,json,re
STATES=['IDLE','HEADER','ASK','REPLY','VALUE','FSTART','FDATA','ENDING','WAIT_ACK','COMMIT','ABORT','DRAIN']
FLAGS=['owned','geometry_valid_raw','initialized','active','fill_busy','fill_done','fill_idle','fill_abort',
       'arbiter_fault','tx_valid','tx_ready','host_valid','host_ready','release']
def sample(value):
 if not re.fullmatch('[0-9a-fA-F]{24}',value):raise ValueError('Expected one96-bit sample')
 n=int(value,16);low=n&0x3fffff
 if low>>18!=6:raise ValueError('Not a177 low22 marker; wrong FPGA pair or absent sample')
 state=(low>>14)&15
 r=dict(scanline=(n>>87)&511,dot=(n>>78)&511,legacy_flags=(n>>66)&4095,
        rom_address=(n>>44)&0x3fffff,hint_address=(n>>22)&0x3fffff,
        export_state=STATES[state] if state<len(STATES) else 'INVALID_'+str(state))
 r.update({name:bool(low&(1<<(13-i))) for i,name in enumerate(FLAGS)})
 return r
def report(text):
 fields=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
 if fields.get('candidate')!='NES-GAME-177' or fields.get('ppu_history_kind')!='LAST16_BOUNDARY177_LOW22':
  raise ValueError('Wrong report version')
 if fields.get('ppu_history_valid')!='1':raise ValueError('No valid history')
 count=int(fields['ppu_history_count']);assert 0<=count<=16
 return dict(samples=[sample(fields[f'ppu_history_{i:02d}']) for i in range(count)],
  scope='Last16 NES clocks at stop/fault, not the first stall nor16 frames. Raw geometry excludes ROM/arbiter masking. No standalone root-cause/FPS claim.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args()
 print(json.dumps(report(a.report.read_text(encoding='utf8')),indent=2))
