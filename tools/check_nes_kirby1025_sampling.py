"""Exercise the full half-minute sampler on the packaged ARM link."""
import struct

from check_nes_frame862_arm import TimedProbe, UC_HOOK_CODE, UC_ARM_REG_R2, UC_ARM_REG_R3
from package_nes_trial704 import save, sha
from prepare_nes_kirby1025 import WORK
from read_nes_tail1012 import SIZE, decode


def check():
    src = WORK / 'link/src'
    q = TimedProbe(src)
    q.call('nes_budget210_reset', [])
    calls = []
    def reply(cpu, pc, size, data):
        assert cpu.reg_read(UC_ARM_REG_R3) == 32
        calls.append(tick)
        h = struct.pack('<BBHBB3HI5H', 0, 0xa1, tick, 0, 0, 20, 93, 22, 0, 10, 40, 90, 91, 91)
        cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2), h + bytes(4) + bytes((15, 165)))
        q.ret(cpu, 1)

    pc = q.syms['nes_native165_bulk']
    q.u.hook_add(UC_HOOK_CODE, reply, None, begin=pc, end=pc)
    ticks = [2999, *(t for begin in range(3000, 6000, 40) for t in (begin+1, begin+3)), 6000]
    for tick in ticks:
        dirty = (tick // 40) % 33
        q.u.mem_write(q.video + q.layout['nes_native_video165']['map_dirty'],
                      ((1 << dirty)-1).to_bytes(8, 'little'))
        q.put(q.video, 'nes_native_video165', 'generation', tick, 2)
        q.call('input900', [tick])
        q.call('e0900', [tick, tick % 2])
        q.call('nes_budget210_frame', [tick])
        q.call('nes_budget210_display', [tick, q.video])
        q.call('finish_header950', [])
    result = decode(bytes(q.u.mem_read(q.data['ptrcache'], SIZE)), 1025)
    expected = list(range(3001,6000,40))
    assert calls == expected == [r['tick'] for r in result['rows']]
    assert not any('invalid' in r for r in result['rows'])
    assert [r['map'] for r in result['rows']] == [(t // 40) % 33 for t in expected]
    assert result['dropped'] == [0,0]
    assert result['displayed55'] == sum(5500 <= t < 6000 for t in ticks)
    return dict(windows=len(expected), wire_reads=len(calls), bytes_per_read=32,
                sample_frame_starts=[expected[0],expected[-1]], map_rows_tested=[0,32],
                firmware=sha(src/'obj-nes-100/firmware.stm'))


if __name__ == '__main__':
    save(WORK/'proof/sampling.json', check())
