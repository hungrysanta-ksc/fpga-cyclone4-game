"""Compare 909 input state and timings on the four linked ARM candidates."""
import argparse
import json
from pathlib import Path

from check_nes_game478 import Machine, sha


def check(sender, probes):
    names = ('nes-oam882-direct', 'nes-packed883', 'nes-packed883-wire', 'nes-packed883-shared')
    sources = [probes / n / 'link-credit/src' for n in names]
    machines = [Machine(src, bytes(128)) for src in sources]
    layout = machines[0].layout['nes_native165']
    assert all(m.layout['nes_native165'] == layout for m in machines)
    blocks = [bytes.fromhex(r['wire']) for r in json.loads(sender.read_bytes())['909']]

    def snapshot(cpu):
        return bytes(cpu.u.mem_read(cpu.state, layout['size']))

    def send(token, block, accepted):
        results, states, costs = [], [], []
        for m in machines:
            m.u.mem_write(m.lut+256, block)
            before = m.instructions
            results.append(bool(m.call('nes_native165_packet', [m.state, token, m.lut+256, len(block)])))
            costs.append(m.instructions-before)
            states.append(snapshot(m))
        assert results == [accepted]*len(machines)
        assert all(s == states[0] for s in states), (token, accepted)
        return costs

    normal, invalid = [], []
    for token, block in enumerate(blocks[:-1]):
        saved = snapshot(machines[0])
        tag = int.from_bytes(block[:2], 'big')
        if tag in (0xf907, 0xfd07):
            # Every lane including the last must reject an out-of-range value.
            for lane in range(8):
                bad = bytearray(block)
                bad[4+lane] = 255
                for m in machines:
                    m.u.mem_write(m.state, saved)
                send(token, bytes(bad), False)
                invalid.append([token, lane])
            for m in machines:
                m.u.mem_write(m.state, saved)
        normal.append(send(token, block, True))
    assert machines[0].state_value() == 2 and invalid
    for m in machines:
        m.call('nes_native165_reset', [m.state])
    assert [send(i,b,True) for i,b in enumerate(blocks[:-1])] == normal
    # Split the real final palette packet immediately before META_END. These
    # guards verify the full bitmap including the high lane of its last word.
    meta_token = next(i for i,b in enumerate(blocks) if b[-12:-10]==bytes.fromhex('e004'))
    for m in machines:
        m.call('nes_native165_reset',[m.state])
    for i,b in enumerate(blocks[:meta_token]):
        send(i,b,True)
    send(meta_token, blocks[meta_token][:-12], True)
    base = snapshot(machines[0])
    bitmap_cases = [('edges',[(0,1),(15,2),(16,3),(8191,2)],4,True),
                    ('512',[(i,1+i%3) for i in range(512)],512,True),
                    ('extra_bit',[(15,1),(8191,2)],1,False),
                    ('missing_bit',[(16,1)],2,False),
                    ('513',[(i,1) for i in range(513)],513,False)]
    for _, tags, count, ok in bitmap_cases:
        bm=bytearray(2048)
        for t,k in tags:
            bm[t//4] |= k << (2*(t%4))
        for m in machines:
            m.u.mem_write(m.state,base)
            m.u.mem_write(m.state+layout['required'],bytes(bm))
            m.u.mem_write(m.state+layout['missing'],count.to_bytes(2,'little'))
        send(meta_token+1,blocks[meta_token][-12:],ok)
    return dict(names=names, firmware=[sha(src/'obj-nes-100/firmware.stm') for src in sources],
                valid_packet_instructions=normal, malformed_lanes=invalid, bitmap_cases={r[0]:r[3] for r in bitmap_cases}, cold_replay=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('sender','probes','out'):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    args.out.write_text(json.dumps(check(args.sender,args.probes),indent=2)+'\n')
