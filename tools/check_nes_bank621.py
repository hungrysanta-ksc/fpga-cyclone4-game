# SPDX-License-Identifier: MIT
"""Exercise the actual ARM resident ownership transitions and plan flush boundaries."""
import argparse
import json
from pathlib import Path

from check_nes_bg620 import ARM, drain_stop, edge, sha


def ownership(src, failure):
    m = ARM(src, 'normal')
    r = m.resident
    typ = 'nes_resident211'
    flags = r + m.layout[typ]['resident']
    stride = (m.layout[typ]['used'] - m.layout[typ]['resident']) // 2
    assert stride == 144
    def bits():
        return [m.u.mem_read(flags + i*stride, 1)[0] & 1 for i in (0, 1)]

    m.call('nes_resident211_reset', [r])
    for i in range(3):
        epoch = 2 if i == 2 and failure == 'epoch' else 1
        assert m.call('nes_resident211_begin', [r, epoch, 1, 907+i, m.spi|1, 0])
        bank = m.get(r, typ, 'target')
        assert bank == i % 2
        if i == 2:
            assert bits() == ([0, 0] if failure == 'epoch' else [1, 1])
            if failure == 'abort':
                m.call('nes_resident211_abort', [r])
                assert bits() == [0, 0] and not m.call('nes_resident211_begin', [r, epoch, 1, 910, m.spi|1, 0])
            return
        assert not bits()[bank]
        m.put(r, typ, 'dirty', 1, 1)
        m.put(r, typ, 'prepared', 1, 1)
        assert not bits()[bank]  # staging a write cannot grant history
        good = i == 0 or failure not in ('wrong_bank', 'no_display')
        ok = m.call('nes_resident211_commit', [r, i+1, 907+i,
                    bank ^ int(i == 1 and failure == 'wrong_bank'), int(i == 0 or failure != 'no_display')])
        assert bool(ok) == good
        if not good:
            assert bits() == [0, 0]
            return
        assert bits()[bank]


def first_fill(src):
    m = ARM(src, 'normal')
    m.setup()
    m.put(m.p, 'nes_plan200', 'bank_history', 1, 1)
    for i in range(11):
        assert m.emit(0, 100+i, 1000+i)
        assert m.endpoint.accepted == int(i >= 3)
    assert m.get(m.p, 'nes_plan200', 'count') == 7


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('src', type=Path)
    p.add_argument('out', type=Path)
    a = p.parse_args()
    transitions = ['reuse', 'epoch', 'wrong_bank', 'no_display', 'abort']
    for test in transitions:
        ownership(a.src, test)
    first_fill(a.src)
    guards = [edge(a.src, 7, mode, history_field='bank_history', history_value=2)
              for mode in ('normal', 'bad_reply', 'STOP_before_E9', 'STOP_after_E9')]
    a.out.write_text(json.dumps(dict(arm=sha(a.src/'obj-nes-100/firmware.stm'), transitions=transitions,
                          first_fill_after_11_BG=dict(issued_BG=4, pending_BG=7),
                          reuse=guards, map_STOP=drain_stop(a.src)), indent=2)+'\n')
