"""Execute packet routing/STOP and preserve final-display ownership in linked ARM."""
import argparse
import json
from pathlib import Path
from check_nes_supply485_arm import ARM, crc, sha, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1
from check_nes_game478 import UC_HOOK_CODE


def run(src, candidate, all_payload=False):
    rows = []
    for op, section, at, n, expanded in ((2,5,0,21,0), (5,5,21,2,1100), (2,5,1121,66,0),
                                       (2,5,1505,240,0), (2,2,1024,192,0), (3,0,0,168,0)):
        for stop in (False, True):
            m = ARM(src, 'normal')
            m.setup()
            m.put(m.s, 'nes_native_sink165', 'plan', m.p, 4)
            modes = []
            def gate(u, pc, size, unused):
                modes.append(u.reg_read(UC_ARM_REG_R1))
                # Fail SEAL here too: this unit test never fabricates a display ACK.
                u.reg_write(UC_ARM_REG_R0, int(not stop and op != 3))
                u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
            pc = m.syms['nes_plan200_progress']
            m.u.hook_add(UC_HOOK_CODE, gate, begin=pc, end=pc)
            issued = []
            original = m.endpoint.exchange
            def exchange(tx, clock):
                if tx[0] != 0xe1:
                    return original(tx, clock)
                assert crc(tx[:-2],16,0x1021,65535) == int.from_bytes(tx[-2:], 'big')
                h = tx[1:-2]
                assert (h[0],h[1],int.from_bytes(h[10:12],'little')) == (op,section,at)
                assert int.from_bytes(h[14:16],'little') == expanded
                assert h[16:] == data
                issued.append(h.hex())
                m.endpoint.sent += 1
                return bytes(len(tx))
            m.endpoint.exchange = exchange
            data = bytes(i % 251 for i in range(n))
            m.u.mem_write(m.q, data)
            ok = m.call('packet_wire', [m.s,op,section,at,m.q,n,expanded])
            expected = 1 if op==3 else 2 if section==2 else 3 if section==5 and not all_payload and (not candidate or at>=1121) else 0
            assert modes == [expected], (op,section,at,modes)
            assert bool(ok) == bool(not stop and op!=3)
            assert len(issued) == int(bool(ok))
            assert not m.get(m.s,'nes_native_sink165','displayed')
            assert not m.call('nes_plan200_retire',[m.p]) and not m.endpoint.rearmed
            rows.append(dict(op=op,section=section,offset=at,STOP=stop,mode=expected,issued=len(issued)))
    return dict(firmware=sha(src/'obj-nes-100/firmware.stm'),cases=rows,
                scope='Actual packet builder, CRC and queue admission; progress result injected for routing/STOP boundary. No fabricated final ACK.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--arm',type=Path,required=True)
    p.add_argument('--candidate',action='store_true')
    p.add_argument('--all',action='store_true')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a.arm,a.candidate,a.all),indent=2)+'\n',newline='\n')
