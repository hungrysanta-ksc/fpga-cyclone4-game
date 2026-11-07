"""Read-only M4 packet/credit observations with the MMC662 board-bound replay."""
import runpy
from unittest.mock import patch
import test_nes_raw506_joint as joint
from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3


def observe(original):
    def init(cpu, args, link):
        original(cpu, args, link)
        args.trace_credit = True
        window = cpu.rt + cpu.layout['nes_native_runtime165']['transport']
        counters = window + cpu.layout['nes_sink_window184']['sent']
        def stamp(u, event, **fields):
            if 951 <= cpu.generation <= 957:
                sent, retired = (int.from_bytes(u.mem_read(counters + k, 2), 'little') for k in (0, 2))
                cpu.events.append(dict(event=event, clock=cpu.clock, generation=cpu.generation,
                                       sent=sent, retired=retired, **fields))
        def ready(u, pc, size, unused):
            op, section, offset = (u.reg_read(r) for r in (UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
            stamp(u, 'ready664', op=op, section=section, offset=offset)
        def wire(u, pc, size, unused):
            h = bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1), 16))
            stamp(u, 'wire664', op=h[0], section=h[1], offset=int.from_bytes(h[10:12], 'little'),
                  sequence=int.from_bytes(h[2:4], 'little'))
        for sym, fn in (('packet_wire', ready), ('nes_window184_enqueue', wire), ('nes_window184_barrier', wire)):
            pc = cpu.syms[sym]
            cpu.u.hook_add(UC_HOOK_CODE, fn, begin=pc, end=pc)
    return init


if __name__ == '__main__':
    with patch.object(joint.Runtime, '__init__', observe(joint.Runtime.__init__)):
        runpy.run_module('test_nes_word660', run_name='__main__')
