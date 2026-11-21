"""Price a physical OBJ row-pair refill cache behind both capture probes."""
import argparse
import json
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import replay_nes_peer906 as peer
from nes_section910 import BASE
from prepare_nes_opening818 import ADVENTURE_SHA
from test_nes_obj609 import lanes
from test_nes_raw506_joint import wire_plan


class RowLink(peer.PeerLink):
    enabled = True

    def __init__(self, args):
        super().__init__(args)
        self.lines = {}
        self.cache_generation = None
        self.blocked = {}
        self.counts = Counter()
        game = Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes'
        assert peer.sha(game) == ADVENTURE_SHA
        self.chr = game.read_bytes()[-131072:]

    def advance(self, now):
        super().advance(now)
        # rpc() calls advance at the exact return edge *before* popping the
        # oldest bank. A completed flight is blocked only in this state.
        if self.flight and self.flight[2] <= now and not self.open and len(self.jobs) == 2:
            token = self.jobs[0]['token']
            self.blocked.setdefault(token, [self.generation, self.flight[2]])

    def next_rom(self, t):
        kind, addr = self.pending[0]
        g = self.generation
        if g != self.cache_generation:
            self.lines.clear()  # no inherited refill data, even with a warm capture
            self.cache_generation = g
        if not self.enabled or kind != 1 or addr & 8 or self.peer == (g, addr):
            return super().next_rom(t)
        tag, row = divmod(addr, 16)
        slot = ((tag ^ (tag >> 7)) & 15, row)
        capture = self.cache[str(g)].get(str(tag % 128))
        if (self.lookups[str(g)][str(addr)] == 1 or
                (capture and capture[0] == tag and str(row) in capture[1])):
            return super().next_rom(t)
        value = (self.chr[addr], self.chr[addr+8])
        # These short OBJ records probe primary and mirror before filling.
        if slot in self.lines and self.lines[slot][0] == tag:
            assert self.lines[slot][1] == value
            self.counts[g] += 1
            self.pending.popleft()
            self.peer = g, addr+8
            return t + 8 + 2 * (self.lookups[str(g)][str(addr)] == 2) + 2
        n = len(self.grants)
        end = super().next_rom(t + 2)
        assert len(self.grants) == n+1 and self.peer == (g, addr+8)
        self.lines[slot] = tag, value
        return end

    def exchange(self, seq, t, op, args):
        lines = super().exchange(seq, t, op, args)
        if op == 'FINISH':
            (self.a.out/'rows911.json').write_text(json.dumps(
                dict(blocked=self.blocked, saved=self.counts)))
        return lines


class AheadLink(RowLink):
    """Bounded second reader of CRC-accepted short OBJ plans, normal arbiter slots."""
    def __init__(self, args):
        super().__init__(args)
        assert args.rom_phase == 0
        self.owner = None
        self.free = 0
        self.spec = []
        self.stopped = False

    def cancel_supply(self):
        # A granted PSRAM operation keeps its slot until its physical reply.
        # Dropping all eligibility also discards an already scheduled fill
        # whose response would have arrived after STOP.
        self.stopped = True
        self.active = False
        self.peer = self.owner = None
        self.queue = []
        self.ready_rows = {}
        self.tags = set()
        self.seen_rows = set()

    def restart_supply(self):
        assert self.stopped
        self.stopped = False
        self.begin()

    def begin(self):
        if self.owner != self.generation:
            self.owner = self.generation
            self.active = False
            self.next_batch = 0
            self.tags = set()
            self.queue = []
            self.ready_rows = {}
            self.seen_rows = set()

    def scan_start(self, batch):
        return batch.get('first_check')

    def row_scan_time(self, batch, scan_end, record_index):
        return scan_end

    def pump(self, now):
        if self.stopped:
            return
        self.begin()
        if not self.active:
            return
        batches = self.phases.get(self.owner,{}).get('banks557',[])
        while self.next_batch < len(batches):
            b = batches[self.next_batch]
            start = self.scan_start(b)
            if start is None:
                break
            records = self.plansets[self.owner][b['first']:b['first']+b['count']]
            # Private copy at CRC acceptance; conservatively charge the whole
            # scan after the original reader's first CHECK. No future E9.
            at = start + 20*b['count']
            for record_index,q in enumerate(records):
                if q[6] != 1:
                    continue
                assert len(wire_plan(q)) == 8
                tag = int.from_bytes(q[4:6], 'little')
                if tag not in self.tags and len(self.tags) == 16:
                    continue
                self.tags.add(tag)
                for lane,addr in lanes(q):
                    if lane%2==0 and addr not in self.seen_rows:
                        self.seen_rows.add(addr)
                        self.queue.append((addr,self.row_scan_time(b,at,record_index)))
            self.next_batch += 1
        while self.queue:
            addr, at = self.queue[0]
            if callable(at):
                at=at()
                if at is None:
                    break
            if addr in self.ready_rows:
                self.queue.pop(0)
                continue
            grant, reply = self.original_select(max(at,self.free))
            if grant >= now:  # tie goes to the normal port
                break
            self.queue.pop(0)
            self.free = reply+1
            self.ready_rows[addr] = (reply,self.chr[addr],self.chr[addr+8])
            self.spec.append((self.owner,addr,grant,reply))

    def select(self, request):
        assert not self.stopped
        grant, reply = self.original_select(max(request,self.free))
        self.grants.append((self.generation,self.read_kind,request,grant,reply))
        self.free = reply+1
        return grant,reply

    def next_rom(self, t):
        assert not self.stopped
        self.pump(t)
        kind,addr = self.pending[0]
        n = len(self.grants)
        if kind == 1 and not addr&8:
            tag,lane = divmod(addr,16)
            line = self.cache[str(self.owner)].get(str(tag%128))
            lookup = self.lookups[str(self.owner)][str(addr)]
            capture_hit = lookup == 1 or (line and line[0]==tag and str(lane) in line[1])
            if not capture_hit:
                t += 2  # extra synchronous result lookup after capture misses
                if addr in self.ready_rows:
                    ready,lo,hi = self.ready_rows[addr]
                    assert (lo,hi) == (self.chr[addr],self.chr[addr+8])
                    self.counts[self.owner] += 1
                    self.pending.popleft()
                    self.peer = self.owner,addr+8
                    return max(t+8+2*(lookup==2),ready+1)
        end = peer_base_next(self,t)
        if kind == 1 and not addr&8 and len(self.grants)>n:
            self.active = True
            if addr in self.seen_rows:
                self.ready_rows[addr] = (end,self.chr[addr],self.chr[addr+8])
        return end

    def decode557(self,q,arrived,now):
        at = super().decode557(q,arrived,now)
        if at<=now and q[6]==3:
            self.pump(at)
            self.active=False
        return at

    def exchange(self,seq,t,op,args):
        lines = super().exchange(seq,t,op,args)
        if op=='FINISH':
            all_slots = [r[3] for r in self.grants]+[r[2] for r in self.spec]
            assert len(all_slots)==len(set(all_slots))
            (self.a.out/'ahead911.json').write_text(json.dumps(self.spec))
        return lines


peer_base_next = peer.PeerLink.next_rom


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp', type=Path)
    p.add_argument('phase', type=int, choices=(1, 2))
    p.add_argument('--cold', action='store_true')
    variants = p.add_mutually_exclusive_group()
    variants.add_argument('--reference', action='store_true')
    variants.add_argument('--ahead', action='store_true')
    args = p.parse_args()
    model = AheadLink if args.ahead else RowLink
    with patch.object(peer, 'PeerLink', model), patch.object(model, 'enabled', not args.reference):
        peer.compare(args.temp, args.phase, args.cold, True, edition=907, work_arm=BASE,
                     run_id='911ref' if args.reference else '911ahead' if args.ahead else '911')
