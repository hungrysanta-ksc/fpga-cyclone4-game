"""Schedule checked OBJ returns before OAM or the section-5 pair on the 932 supplier."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_window924
from nes_raw506 import once
from nes_rows932 import ORIGINAL, SlotRun


def image(mode):
    arm, _ = MODES[mode]
    return ORIGINAL.parent/f'nes-banks933-{arm}' if arm else ORIGINAL


def prepare(mode):
    link = image(mode)/'link'
    shutil.copytree(ORIGINAL/'link', link)
    path = link/'src/nes_native_sink165.c'
    anchor = {'palette': ' if(!span(s,3,0,p->cgram,512))return false;',
              'oam': ' if(!oam227(s,p->oam))return false;',
              'pair': '  if(!packet(s,2,5,offset,joined,201))return false;'}[mode]
    # An accepted small BG can precede a long stretch of nonresident OBJ.
    # Let the actual producer/consumer drain before lending credits to the
    # ordinary tail. FINAL services plan END; only the later SEAL can display.
    service = ''' if(s->plan && s->plan->bulk_valid && !s->plan->bulk[1] &&
    s->plan->bulk[2]==16 && !s->plan->bulk[3] &&
    !nes_plan200_progress(s->plan,NES_FINAL553))return fail(s,5);
'''
    path.write_text(once(path.read_text(), anchor, service+anchor), newline='\n')


class RetainedRows(SlotRun):
    """Model a tagged, initially empty, 128-entry row store for immutable CHR ROM."""

    def __init__(self, args):
        super().__init__(args)
        self.history = {}
        self.hits933 = []

    def cancel_supply(self):
        super().cancel_supply()
        self.history.clear()

    buckets = 16

    def index(self, address):
        tag, row = divmod(address, 16)
        return ((tag ^ (tag >> 7)) & (self.buckets-1), row)

    def store_reply(self, address, reply):
        # Only actual paired physical reads are admitted; never seed from
        # the reference image or an unconfirmed capture-cache lookup.
        self.history[self.index(address)] = (address, self.generation, reply,
                                             self.chr[address], self.chr[address+8])

    def pump(self, now):
        if self.stopped:
            return
        start = len(self.spec)
        super().pump(now)
        for gen, address, grant, reply in self.spec[start:]:
            assert gen == self.generation and grant < reply
            self.store_reply(address, reply)

    def next_rom(self, t):
        kind, address = self.pending[0]
        if kind != 1 or address & 8:
            return super().next_rom(t)
        self.pump(t)
        hit = self.history.get(self.index(address))
        line = self.cache[str(self.owner)].get(str(address//16 % 128))
        capture = (self.lookups[str(self.owner)][str(address)] == 1 or
                   (line and line[0] == address//16 and str(address%16) in line[1]))
        if not capture and address not in self.ready_rows and self.use_history():
            t += 2  # synchronous tagged-row probe, charged on misses as well
            if hit and hit[0] == address and hit[1] != self.generation and hit[2] < t:
                self.ready_rows[address] = (t, hit[3], hit[4])
                self.hits933.append([self.generation,address,hit[1],hit[2],t])
        start = len(self.grants)
        end = super().next_rom(t)
        if len(self.grants) > start:
            self.store_reply(address, self.grants[-1][-1])
        return end

    def use_history(self):
        return True

    def exchange(self, seq, t, op, args):
        result = super().exchange(seq,t,op,args)
        if op == 'FINISH':
            (self.a.out/'history933.json').write_text(json.dumps(self.hits933)+'\n')
        return result


class SparseHead(RetainedRows):
    """Use history only for an isolated short head followed by a full contiguous pair."""
    def use_history(self):
        # Only consult the first accepted E9. Its small head would otherwise
        # block two consecutive full-tile slots in another 32-slot page.
        banks = self.phases.get(self.owner, {}).get('banks557', [])
        if not banks or banks[0]['count'] < 4:
            return False
        index = banks[0]['first']
        header, head, left, right = self.plansets[self.owner][index:index+4]
        slots = [int.from_bytes(q[2:4], 'little') for q in (head,left,right)]
        return (header[6] == 2 and head[6] == left[6] == right[6] == 1 and
                head[7] != 255 and left[7] == right[7] == 255 and
                slots[0]//32 != slots[1]//32 and slots[2] == slots[1]+1)


class DeeperHead(SparseHead):
    # One more index bit distinguishes 3072/3073 from 6264/6265 on this
    # workload. Budget and compare the doubled row store explicitly.
    buckets = 32


class PageHead(DeeperHead):
    """Use leftover grants to refill the most recently demanded immutable 256B page."""
    def __init__(self, args):
        super().__init__(args)
        self.pages = {}
        self.page_key = None
        self.page_grants = []
        self.page_hits = []

    def cancel_supply(self):
        super().cancel_supply()
        self.pages.clear()
        self.page_key = None

    def observe_page(self, key, reply):
        if key not in self.pages and len(self.pages) == 4:
            del self.pages[next(iter(self.pages))]
        page = self.pages.pop(key,None)
        if page is None:
            page = dict(cursor=0,rows={},after=reply+1)
        self.pages[key] = page
        self.page_key = key

    def unfinished(self):
        if self.page_key is not None:
            yield self.page_key

    def pump(self, now):
        super().pump(now)
        if self.stopped:
            return
        for key in self.unfinished():
            page = self.pages[key]
            while page['cursor'] < 128:
                i = page['cursor']
                address = key + 16*(i//8) + i%8
                grant, reply = self.original_select(max(self.free, page['after']))
                if grant >= now:
                    return
                page['cursor'] += 1
                page['rows'][address] = (self.generation,reply,self.chr[address],self.chr[address+8])
                self.free = reply+1
                self.page_grants.append((self.generation,address,grant,reply))

    def next_rom(self, t):
        kind, address = self.pending[0]
        key = address & ~255
        start = len(self.grants)
        if kind == 1 and not address & 8:
            self.pump(t)
            page = self.pages.get(key)
            prior = page and page['rows'].get(address)
            if prior and prior[0] != self.generation and prior[1] < t and self.use_history():
                # Parallel tag probe with the retained row store. Price a
                # separate response mux cycle on a page-assisted lookup.
                line = self.cache[str(self.owner)].get(str(address//16 % 128))
                capture = (self.lookups[str(self.owner)][str(address)] == 1 or
                           (line and line[0] == address//16 and str(address%16) in line[1]))
                if not capture and address not in self.ready_rows:
                    resident = self.history.get(self.index(address))
                    if not resident or resident[0] != address or resident[1] == self.generation:
                        t += 3
                        self.ready_rows[address] = (t,prior[2],prior[3])
                        self.page_hits.append((self.generation,address,prior[0],prior[1],t))
        end = super().next_rom(t)
        if kind == 1 and not address & 8 and len(self.grants) > start:
            self.observe_page(key,self.grants[-1][-1])
        return end

    def exchange(self, seq, t, op, args):
        result=super().exchange(seq,t,op,args)
        if op=='FINISH':
            grants=[g[3] for g in self.grants]+[g[2] for g in self.spec]+[g[2] for g in self.page_grants]
            assert len(grants)==len(set(grants))
            (self.a.out/'pages933.json').write_text(json.dumps(dict(grants=self.page_grants,hits=self.page_hits))+'\n')
        return result


class QueuedPages(PageHead):
    def store_reply(self,address,reply):
        super().store_reply(address,reply)
        # A physically completed plan prefetch is the same evidence of ROM
        # locality as a blocking read. Do not open pages from lookahead alone.
        self.observe_page(address & ~255,reply)

    def unfinished(self):
        return sorted(self.pages,key=lambda key:self.pages[key]['after'])


MODES = {
    'oam': ('oam',SlotRun), 'pair': ('pair',SlotRun), 'palette': ('palette',SlotRun),
    'rows': (None,RetainedRows), 'joint': ('oam',RetainedRows), 'early': ('palette',RetainedRows),
    'sparse': (None,SparseHead), 'dispatch': ('palette',SparseHead),
    'depth': (None,DeeperHead), 'service': ('palette',DeeperHead),
    'page': (None,PageHead), 'pagearm': ('palette',PageHead), 'fair': (None,QueuedPages),
}


def replay(temp, phase, cache, mode):
    _, producer = MODES[mode]
    with patch.object(nes_window924,'LeadingRecord',producer):
        nes_window924.replay(temp,'objheader',phase,cache=='cold',arm=image(mode),
                             edition=925,tag='933'+mode,trace_last=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','proof','guards'))
    p.add_argument('mode',choices=MODES)
    p.add_argument('temp',type=Path,nargs='?')
    p.add_argument('phase',type=int,choices=(1,2),nargs='?')
    p.add_argument('cache',choices=('warm','cold'),nargs='?')
    a = p.parse_args()
    if a.action in ('prepare','proof','guards'):
        if a.mode not in ('oam','pair','palette'):
            p.error('select the underlying ARM image to prepare')
    if a.action == 'prepare':
        prepare(a.mode)
    elif a.action == 'proof':
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',
            image(a.mode),925,short_header=True)
    elif a.action == 'guards':
        from nes_obj923 import obj_stops
        from nes_return920 import guards
        guards(a.temp,'first',tag='933'+a.mode,destination=image(a.mode)/'final-guards.json')
        obj_stops(a.temp,'first',tag='933'+a.mode,destination=image(a.mode)/'final-stops.json')
    else:
        replay(a.temp,a.phase,a.cache,a.mode)
