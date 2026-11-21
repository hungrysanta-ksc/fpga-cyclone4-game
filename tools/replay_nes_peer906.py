"""Compare cache-first OBJ row-pair supply with byte supply on fixed linked workloads."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from replay_nes_gap904 import TimedLink, CLIENT, gates, main, map_samples, monitor, once, sha
from replay_nes_supply905 import run
from test_nes_raw506_joint import wire_plan


class PeerLink(TimedLink):
    pair = False

    def __init__(self, args):
        super().__init__(args)
        self.peer = None
        self.saved = {}
        for plans in self.plansets.values():
            assert all(wire_plan(q)[0] == 0x81 for q in plans if q[6] == 1)

    def next_rom(self, t):
        kind, addr = self.pending[0]
        peer, self.peer = self.peer, None
        if self.pair and kind == 1 and (self.generation, addr) == peer:
            self.pending.popleft()
            self.saved[self.generation] = self.saved.get(self.generation, 0) + 1
            return t + 1
        before = len(self.grants)
        end = super().next_rom(t)
        if kind == 1 and addr & 8 == 0 and len(self.grants) > before:
            # Only an accepted backing read supplies both planes. A capture
            # hit does not qualify whatever PSRAM happened to return last.
            self.peer = self.generation, addr + 8
        return end

    def exchange(self, seq, t, op, args):
        result = super().exchange(seq, t, op, args)
        if op == 'FINISH':
            (self.a.out/'peers906.json').write_text(json.dumps(self.saved))
        return result


def compare(temp, phase, cold, paired):
    work = temp/'nes-gap904'
    source = json.loads((work/'sender-obj/sender.json').read_bytes())
    tag = f'906-{"cold" if cold else "warm"}-{"pair" if paired else "byte"}'
    prefix = f'nes-tile821-obj-jointmirror-p{phase}-'
    def workload(temp, _, edition, clip, phase, *, candidate_arm, replay_tag):
        def adapt(s):
            return map_samples(once(monitor(s, 'demo'), 'local n=pb(0)==2 and pw(12) or pw(14)',
                                    'local n=pb(0)==9 and 1472 or pb(0)==2 and pw(12) or pw(14)'))
        args = ['replay','','','','','',tag,str(Path.home()/'Downloads/nes-budget-mmc872.txt')]
        with patch.object(sys,'argv',args), patch.object(PeerLink,'pair',paired), \
             patch.object(PeerLink,'cold_obj',cold), patch.object(PeerLink,'lookup_file',work/'hits-obj/hits.json'), gates(source,True):
            main(work/'data-obj','obj','jointmirror',phase,temp,arm=candidate_arm,client=CLIENT,
                 client_hash=sha(CLIENT/'sink165.sfc'),link_class=PeerLink,packet_source=source,adapt_template=adapt)
    run(temp,'late',phase,tag=tag,out=temp/(prefix+tag),base=temp/(prefix+'904-retire'),runner=workload)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=[1,2])
    p.add_argument('--cold',action='store_true')
    p.add_argument('--pair',action='store_true')
    a=p.parse_args()
    compare(a.temp,a.phase,a.cold,a.pair)
