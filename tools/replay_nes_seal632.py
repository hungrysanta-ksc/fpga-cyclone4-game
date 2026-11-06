# SPDX-License-Identifier: MIT
"""Replay accepted 625 packets with independent checks moved to immutable inputs."""
import argparse
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from replay_nes_map630 import WIRE_CLOCKS, bound_observer
from analyze_nes_map628 import csv_groups, ms, one, read, sha
from analyze_nes_tail627 import deadlines
from nes_raw506 import once


def specialize(rows, flags):
    seal = rows[-1][1]
    assert seal[:2] == bytes((3, 0)) and len(seal) == 184
    out = []
    seen = False
    for clock, h, tile in rows:
        if h[:2] == bytes((2, 3)) and h[10:12] == bytes(2):
            assert len(h) == 48 and not seen
            seen = True
            if flags:
                body = h[16:]
                if flags & 1:
                    body += seal[40:]
                if flags & 2:
                    body += seal[26:28] + seal[34:36] + seal[38:40]
                h = bytes((9, 3)) + h[2:12] + len(body).to_bytes(2, 'little') + flags.to_bytes(2, 'little') + body
        elif h[0] == 3 and flags & 1:
            h = h[:12] + bytes((24, 0)) + h[14:40]
        elif seen:
            assert h[0] != 7 and h[1] != 2
        out.append((clock, h, tile))
    assert seen
    return out


def pace(rows, transformed, spi):
    # Each recorded ARM launch is an earliest issue time. Carry wire conflicts
    # across all commands; never offer a modified E1 before its last byte.
    end = 0
    offers = []
    for e in spi:
        elapsed = e['clock'] - e['start']
        push = e['opcode'] == '0xe1'
        if push:
            i = len(offers)
            original, before, _ = rows[i]
            _, after, bulk = transformed[i]
            assert abs(original - e['clock']) <= 1 and len(before) + 3 == e['bytes']
            elapsed += (len(after) - len(before)) * WIRE_CLOCKS
        end = max(end, e['start']) + elapsed
        if push:
            offers.append((round(end), after, bulk))
    assert len(offers) == len(rows)
    return offers


def run(a):
    a.frames = 47
    ev = [e for e in read(a.trace/'events.json') if e['generation'] == 951 and e['event'] == 'SPI']
    cutoff = deadlines(a.trace)[951]['previous_cutoff']

    def observe(_, args, unused):
        s, labels = bound_observer(a, args)
        hooks = ''
        for label in ('walk632', 'earlyhdma632', 'return632', 'validated632'):
            hooks += f"checkedMem527(function()if packet and pw(8)==951 then sample516('{label}') end end,emu.callbackType.exec,{labels[label]})\n"
        return once(s, "checkedMem527(function()sample516('seal')", hooks + "checkedMem527(function()sample516('seal')")

    def edit(s):
        path = a.out/'arrivals.tsv'
        prefix, rows = [], []
        for line in path.read_text().splitlines()[:-1]:
            clock, data, bulk = line.split('\t')
            h = bytes.fromhex(data)
            if int.from_bytes(h[8:10], 'little') == 951:
                rows.append((int(clock), h, bulk))
            else:
                prefix.append(line)
        offers = pace(rows, specialize(rows, a.flags), ev)
        prefix.extend(f'{clock}\t{h.hex()}\t{bulk}' for clock, h, bulk in offers)
        prefix.append(f'{offers[-1][0]+1}\tFINISH\t')
        path.write_text('\n'.join(prefix) + '\n', newline='\n')
        return once(s, "assert(sent-retired<4,'queue overflow')", "if sent-retired>=4 then return end")

    def compare(_, actual):
        w = csv_groups(a.out/'window.csv')
        seal = [r for r in w[951] if r['op'] == 3]
        prior = [r for r in w[950] if r['op'] == 3]
        heads = {}
        for e in w[951]:
            if e['event'] in ('load','ack'):
                heads.setdefault(e['index'], {})[e['event']] = e['clock']
        return dict(flags=a.flags, interval=one(seal,'reveal')['frame']-one(prior,'reveal')['frame'],
                    seal_ms=ms(one(seal,'load')['clock']-cutoff),
                    upload_ms=ms(one(seal,'upload165_entry')['clock']-cutoff),
                    dma_ms=ms(min(e['clock'] for e in seal if e['event']=='ppu_dma')-cutoff),
                    ack=one(seal,'ack')['clock'], heads=list(heads.values()), cutoff=cutoff,
                    offers=sha(a.out/'arrivals.tsv'), client=sha(a.client/'sink165.sfc'))

    with patch.object(replay, 'observe', observe):
        replay.run(a, edit_script=edit, compare_trace=compare, source_client=a.base_client)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for k in ('trace','base-client','client','mesen','out'):
        p.add_argument('--'+k, type=Path, required=True)
    p.add_argument('--flags', type=int, choices=range(4), required=True)
    run(p.parse_args())
