"""Replay late generation-912 RTL head visibility against the 913 CPU schedule.

F models late returns. G and I enforce the actual head-visible clock of every
token. The separate E8 trace check covers earlier readiness as well. Other
generations and the SPI schedule come from the original 913 replay.
"""
import argparse
import json
import re
from pathlib import Path
from unittest.mock import patch

from nes_overlap913 import LeadingRecord, OUT, work, peer, monitor
from test_nes_raw506_joint import crc
from test_nes_banks557 import host_after, MASTER


class LateHead(LeadingRecord):
    def snapshot557(self,tx,start):
        reply=bytearray(super().snapshot557(tx,start))
        if self.generation==912 and tx[0]==0xe8 and reply[6]:
            token=int.from_bytes(reply[14:18],'little')
            sample=host_after(start+7.5*MASTER/2625000,3)
            if sample<self.limits.get(token,0):
                reply[6:18]=bytes(12)
                reply[19]=crc(reply[1:19],8,7,0)
        return bytes(reply)


def replay(temp,phase,cold,rev,*,arm=None,edition=907,wire_tag='914wire',run_id=None,transcript_dir=None):
    state='cold' if cold else 'warm'
    folder=temp/f'nes-tile821-obj-jointmirror-p{phase}-{wire_tag}-{state}-pair'
    origin=int((folder/'origin914.txt').read_text())
    jobs=[j for l in (folder/'producer.jsonl').read_text().splitlines() if (j:=json.loads(l))['generation']==912]
    board=temp/f'nes-port914{rev}/nes-trial816-board914'
    transcript=((transcript_dir or board)/f'trace-{phase}-{state}.log').read_text(errors='replace')
    assert 'PASS914 trace' in transcript
    rows=re.findall(r'chunk=(\d+) bytes=(\d+) head=(\d+) reference_producer=(\d+) reference_return=(\d+)',transcript)
    assert len(rows)==len(jobs)==8
    limits={}
    for (n,size,head,_,returned),j in zip(rows,jobs):
        assert int(size)==j['bytes']
        if rev!='F' or int(head)>int(returned):
            limits[j['token']]=origin+int(head)
    with patch.object(peer,'PeerLink',LateHead),patch.object(LateHead,'limits',limits,create=True),patch.object(peer,'CLIENT',OUT/'consumer'),patch.object(peer,'monitor',monitor):
        tag={'F':'914head','G':'914ghead','I':'914ihead'}[rev]
        peer.compare(temp,phase,cold,True,edition=edition,work_arm=arm or work('idle'),run_id=run_id or tag)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('temp',type=Path)
    ap.add_argument('phase',type=int)
    ap.add_argument('--cold',action='store_true')
    ap.add_argument('--rev',choices=('F','G','I'),default='I')
    a=ap.parse_args()
    replay(a.temp,a.phase,a.cold,a.rev)
