"""Replay CRC-accepted OBJ lookahead and bounded late DMA on the linked consumer."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from boot_nes_column854 import build
from build_nes_trace_replay import Code
from nes_raw506 import once
from nes_section910 import BASE
from nes_section910 import DIRECT
import replay_nes_peer906 as peer
from replay_nes_rows911 import AheadLink

OUT = BASE.parent/'nes-prefetch912'
ORIGIN = 0x7e2000
REFERENCE = peer.CLIENT
original_monitor = peer.monitor


def monitor(source, scene):
    source = original_monitor(source,scene)
    return once(source,'i<tail or n<=160','i<tail or n<=384')


class ReceivedPlan(AheadLink):
    def scan_start(self, batch):
        # Only the private copy is eligible after E9 CRC acceptance and CDC.
        # The primary decoder still owns its mailbox up to the original CHECK.
        return batch['seal'] + 8


class LeadingRecord(ReceivedPlan):
    def row_scan_time(self,batch,scan_end,record_index):
        if record_index==0:
            return scan_end
        # The auxiliary port holds only the first record from a queued
        # mailbox. The full scan may start once the primary port owns it.
        def checked():
            tick=batch.get('first_check')
            return None if tick is None else tick+20*batch['count']
        return checked


def client():
    labels = json.loads((REFERENCE/'labels.json').read_bytes())
    body = bytearray((REFERENCE/'body.bin').read_bytes())
    # Accept a single outstanding tile up to 384B and keep normal arbitration
    # and the last beam check. Only enlarge the head fast path, never a map.
    for label, seq in [('prefix523','c9 a1 00 b0 03 a8'),('late_tile681','c9 a1 00 b0 05 e2')]:
        pos = body.index(bytes.fromhex(seq),labels[label]-ORIGIN,labels[label]-ORIGIN+56)
        body[pos+1:pos+3] = (385).to_bytes(2,'little')
    # A small checked upload group may enter an already open blank through
    # line 229. The final palette/OAM still has its own line-246 check.
    c = Code(ORIGIN+len(body))
    c.labels.update(labels)
    c.label('group_wait912')
    c.absolute(0xad,0x1256)
    c.emit(0xc9,0,6)  # at least 1536 of 4192 byte-equivalents left
    c.branch(0x90,'fresh912')
    a = labels['wait_final516']-ORIGIN
    b = labels['borrow516']-ORIGIN
    check = bytes(body[a:b])
    assert check.count(bytes.fromhex('c9 f7'))==1 and check.endswith(bytes.fromhex('f0 02 80 b3'))
    check = check.replace(bytes.fromhex('c9 f7'),bytes.fromhex('c9 e6'))
    # Original skip branches land at fresh516, immediately after SEC/RTS.
    c.emit(*check[:-2])
    c.branch(0x80,'cancel912')
    c.emit(0x38,0x60)
    c.label('fresh8_912')
    c.emit(0xc2,0x20)
    c.label('fresh912')
    c.jump('wait169')
    c.label('cancel912')
    c.jump('cancel169')
    site = body.index(bytes.fromhex('20 68 2d'),labels['prepare665']-ORIGIN,labels['prepare665']-ORIGIN+30)
    body[site+1:site+3]=(c.labels['group_wait912']&65535).to_bytes(2,'little')
    body.extend(c.finish())
    build(REFERENCE,OUT/'consumer',bytes(body),c.labels)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['build','consumer','joint','reader','leading','framed'])
    p.add_argument('temp',type=Path,nargs='?')
    p.add_argument('phase',type=int,choices=(1,2),nargs='?')
    p.add_argument('--cold',action='store_true')
    args=p.parse_args()
    if args.mode=='build':
        client()
    else:
        port=AheadLink if args.mode=='consumer' else ReceivedPlan
        if args.mode in ('leading','framed'):
            port=LeadingRecord
        rom=REFERENCE if args.mode=='reader' else OUT/'consumer'
        oracle = original_monitor if args.mode=='reader' else monitor
        with patch.object(peer,'PeerLink',port),patch.object(peer,'CLIENT',rom),patch.object(peer,'monitor',oracle):
            peer.compare(args.temp,args.phase,args.cold,True,edition=907,
                         work_arm=DIRECT if args.mode=='framed' else BASE,
                         run_id='912b'+args.mode)
