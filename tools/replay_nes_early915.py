"""Expose the final physical head when it precedes the estimated tile-ready time.

This only adapts the sampled E8 reply. The unmodified producer must still
validate the token and payload by the later E1, and an independent RTL replay
checks the new E9/return schedule and every changed status sample.
"""
import argparse
import re
import struct
from pathlib import Path
from unittest.mock import patch

from fixture_nes_port914 import FixtureLink, fixture, OUT, peer, monitor
from prepare_nes_trial915 import WORK
from test_nes_banks557 import host_after, MASTER
from test_nes_raw506_joint import crc


def run(temp):
    old=temp/'nes-tile821-obj-jointmirror-p2-915wire-warm-pair'
    phases=temp/'nes-trial915-rtl'
    import json
    records=[j for line in (old/'producer.jsonl').read_text().splitlines()
             if (j:=json.loads(line))['generation']==910]
    last=records[-1]
    descriptor=next(r[6:18] for e in json.loads((old/'events.json').read_bytes())
                    if e.get('opcode')=='0xe8' and e['generation']==910 and (r:=bytes.fromhex(e['reply']))[6]
                    and int.from_bytes(r[14:18],'little')==last['token'])
    assert struct.unpack_from('<H',descriptor,2)[0]==last['bytes']
    transcript=(phases/'lead-910-2-warm.log').read_text(errors='replace')
    assert len(records)==3 and last['bytes']==320
    clock,=re.findall(r'PORT914 chunk=3 bytes=320 head=(\d+)',transcript)
    start=int((old/'gen910/origin914.txt').read_text())
    wire=json.loads((old/'banks904.json').read_bytes())['910']['banks557']
    assert len(wire)==1
    class PhysicalHead(FixtureLink):
        def snapshot557(self,tx,t):
            data=bytearray(super().snapshot557(tx,t))
            if self.generation==910 and tx[0]==0xe8 and not data[6] and not self.end and self.accepted==1:
                sample=host_after(t+7.5*MASTER/2625000,3)
                if start+int(clock)<=sample<last['producer']:
                    assert self.phases[910]['banks557'][0]['seal']==wire[0]['seal']
                    data[3]=2
                    data[6:18]=descriptor
                    data[19]=crc(data[1:19],8,7,0)
            return bytes(data)
    with patch.object(peer,'PeerLink',PhysicalHead),patch.object(peer,'CLIENT',OUT/'consumer'),patch.object(peer,'monitor',monitor):
        peer.compare(temp,2,False,True,edition=915,work_arm=WORK,run_id='915physical')
    for g in (910,911,912):fixture(temp,2,False,g,'915physical')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('temp',type=Path)
    run(p.parse_args().temp)
