# SPDX-License-Identifier: MIT
"""Actual479 RTL block replay on linked476/479 M4; peer/plan completion modeled.

No host2232 encoder here. Checks old/new full state and40B tile-plan equality,
not independent game pixels, IRQ/ROM concurrency, SNES DMA or physical timing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from check_nes_game478 import Machine, sha

p = argparse.ArgumentParser(description=__doc__)
for n in ['base', 'arm', 'core', 'palette', 'out']:
    p.add_argument('--'+n, type=Path, required=True)
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=False)
capture = json.loads((a.core/'result.json').read_text())
blocks = a.core/'nrom429-blocks.txt'
assert capture['passed'] and sha(blocks) == capture['blocks_sha256']
packets = []
for line in blocks.read_text().splitlines():
    token, n, wire = line.split()
    data = bytes.fromhex(wire)
    assert int(token) == len(packets) and int(n) == len(data)
    packets.append(data)


def run(src):
    m = Machine(src, a.palette.read_bytes())
    m.packets, m.index, m.prepared, m.start_token, m.spi_calls = packets, 0, False, 0, 0
    before = m.instructions
    while m.index < len(packets):
        if m.state_value() == 2:
            assert m.call('nes_native165_prepare', [m.state, 1, m.spi|1, 0]) == 1
        else:
            assert m.call('nes_native165_poll', [m.state, m.spi|1, 0]) == 1
    receive = m.instructions-before
    assert m.state_value() == 4
    layout = m.layout['nes_native165']
    gen = int.from_bytes(m.u.mem_read(m.state+layout['generation'], 2), 'little')
    counts = struct.unpack('<6H', m.u.mem_read(m.state+layout['counts'], 12))
    assert m.call('nes_resident211_begin', [m.resident, 1, 1, gen, m.writer|1, 0]) == 1
    before = m.instructions
    assert m.call('nes_native_video211_plan', [m.state, m.lut, m.video, m.resident]) == 1
    planner = m.instructions-before
    bank = m.u.mem_read(m.resident+m.layout['nes_resident211']['target'], 1)[0]
    assert m.call('nes_resident211_commit', [m.resident, 1, gen, bank, 1]) == 1
    states = b''.join(bytes(m.u.mem_read(ptr, m.layout[name]['size'])) for ptr, name in [(m.state, 'nes_native165'), (m.video, 'nes_native_video165'), (m.resident, 'nes_resident211')])
    return {'firmware_SHA256': sha(src/'obj-nes-100/firmware.stm'), 'generation': gen, 'counts': counts, 'receive_instructions': receive, 'planner_instructions': planner, 'plans': m.plans, 'plan_record_bytes': m.layout['nes_plan191']['size'], 'state_SHA256': hashlib.sha256(states).hexdigest(), 'SPI_calls': m.spi_calls}


old, new = run(a.base), run(a.arm)
assert old['state_SHA256'] == new['state_SHA256'] and old['plans'] == new['plans']
assert old['receive_instructions'] == new['receive_instructions'] and old['planner_instructions'] == new['planner_instructions']
assert new['plan_record_bytes'] == 40
(a.out/'private-plans.json').write_text(json.dumps(new['plans']))
for x in [old, new]:
    x['plan_count'] = len(x.pop('plans'))
result = {'passed': True, 'scope': __doc__, 'actual_RTL_blocks_SHA256': sha(blocks), 'payload_bytes': sum(map(len, packets)), 'packets': len(packets), 'palette_SHA256': sha(a.palette), 'baseline476': old, 'candidate479': new, 'independent_pixel_or_actual_IRQ_DMA_proof': False, 'physical_FPS': None}
(a.out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
