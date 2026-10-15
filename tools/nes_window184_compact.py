# SPDX-License-Identifier: MIT
"""Candidate: reuse ACK work storage; invalidate ACK bytes during next write.

Retired credit stays valid; ACK bytes only matter to MCU when fully drained.
Each E0 still owns an immutable snapshot. No latency/check/clock change.
"""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha
from nes_clip178 import replace
from nes_window184 import board

def compact(s):
 s=replace(s,'reg [95:0] ack_work,completed_ack;','reg [95:0] ack_work;')
 s=replace(s,'ack_work<=0;completed_ack<=0;','ack_work<=0;')
 s=replace(s,'else begin ack_work[ack_index*8+:8]<=ack_byte;ack_mask[ack_index]<=1;end',
 '''// ACK bytes become invalid as soon as the next response is written.
    // Nonempty queue retains cumulative retired credit, not its old ACK.
    else begin ack_valid<=0;ack_work[ack_index*8+:8]<=ack_byte;ack_mask[ack_index]<=1;end''')
 assert s.count('completed_ack<=ack_work;')==2;s=s.replace('completed_ack<=ack_work;','')
 return replace(s,'ack_valid?completed_ack[j*8+:8]','ack_valid?ack_work[j*8+:8]')

def main():
 p=argparse.ArgumentParser()
 for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();m=board(a.prior,a.out);q=a.out/'nes_sink_spi165.sv'
 q.write_text(compact(q.read_text()),encoding='utf8',newline='\n');m['sources'][q.name]=sha(q)
 m['compact_ack_contract']='ACKvalid clears during next partial response; credits retained, ACK only required at full drain.'
 m['window184_sources']['tools/nes_window184_compact.py']=sha(Path(__file__))
 (a.out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
