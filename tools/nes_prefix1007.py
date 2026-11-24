"""Trace committed plan bytes and isolate one earlier E9 on the linked 978 ARM."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from unicorn.arm_const import UC_ARM_REG_APSR, UC_ARM_REG_R3, UC_ARM_REG_R4
from nes_capture978 import work
from nes_plan975 import simulate
from replay_nes_supply905 import joint, UC_HOOK_CODE


def run(temp, phase, count, preserve=False):
    tag = f"1007c{count}" + ("ordered" if preserve else "")
    assert not preserve or count==12
    marks = []
    init = joint.Runtime.__init__

    def instrument(cpu, *args):
        init(cpu, *args)
        # Resolve append through the linked caller; ELF local names may collide.
        call = cpu.syms['nes_plan200_emit'] + 0x4a
        raw = cpu.u.mem_read(call, 4)
        hi = int.from_bytes(raw[:2], 'little')
        lo = int.from_bytes(raw[2:], 'little')
        assert hi & 0xf800 == 0xf000 and lo & 0xd000 == 0xd000
        sign = hi >> 10 & 1
        offset = ((sign << 24) | ((1 ^ (lo >> 13 & 1) ^ sign) << 23) |
                  ((1 ^ (lo >> 11 & 1) ^ sign) << 22) | ((hi & 1023) << 12) | ((lo & 2047) << 1))
        append = call + 4 + offset - (sign << 25)
        pc = append + 0x260
        assert bytes(cpu.u.mem_read(pc-2, 6)).hex() == '0e2ba37618d9'
        fired = False
        suffix_branch = False

        def committed(u, addr, size, ctx):
            nonlocal fired, suffix_branch
            if cpu.generation != 912:
                return
            p = u.reg_read(UC_ARM_REG_R4)
            header = u.mem_read(p+20, 16)
            sent = int.from_bytes(header[:2], 'little')
            size = int.from_bytes(header[2:4], 'little')
            n = u.reg_read(UC_ARM_REG_R3)
            assert int.from_bytes(header[4:6],'little') == 912 and n == header[6]+1
            image = bytes(u.mem_read(p+64,size))
            cut = bool(count and n==count and not sent and not fired and header[13]==3
                       and image.startswith(bytes.fromhex('829003')))
            suffix_branch = preserve and fired and sent==1 and n==3
            marks.append(dict(clock=cpu.clock,sent=sent,count=n,body=image.hex(),cut=cut,suffix=suffix_branch))
            if cut or suffix_branch:
                # Only change the outcome of count<15 at the existing branch.
                # The real count and payload, flush/credit checks and SPI stay live.
                flags = u.reg_read(UC_ARM_REG_APSR)
                u.reg_write(UC_ARM_REG_APSR,(flags | (1<<29)) & ~(1<<30))
                fired = True

        def keep_boundary(u, addr, size, ctx):
            nonlocal suffix_branch
            if suffix_branch:
                # r3 here is a dead copy of obj_start used only by cbz.
                # Preserve source bytes/lengths while taking the real flush tail.
                assert cpu.generation==912 and u.reg_read(UC_ARM_REG_R3)==0
                u.reg_write(UC_ARM_REG_R3,1)
                suffix_branch=False

        assert bytes(cpu.u.mem_read(pc+8,2)).hex()=='abb1'
        cpu.u.hook_add(UC_HOOK_CODE,keep_boundary,begin=pc+8,end=pc+8)
        cpu.u.hook_add(UC_HOOK_CODE,committed,begin=pc,end=pc)

    with patch.object(joint.Runtime,'__init__',instrument):
        simulate(temp,phase,'cold',True,work('returned'),True,tag=tag,edition=966)
    assert marks and sum(r['cut'] for r in marks)==int(bool(count))
    assert sum(r['suffix'] for r in marks)==int(preserve)
    (temp/f"nes-prefix1007-c{count}{'ordered' if preserve else ''}-p{phase}.json").write_text(json.dumps(marks))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('count',type=int,choices=(0,1,2,12))
    p.add_argument('--ordered',action='store_true')
    p.add_argument('--guards',action='store_true')
    args=p.parse_args()
    if args.guards:
        from check_nes_plan975 import directory, packet_path, replay
        key = str(args.count)+('ordered' if args.ordered else '')
        trace = directory(args.temp,args.phase,f'1007c{key}','cold')
        tiles = [json.loads(x) for x in (trace/'producer.jsonl').read_text().splitlines()]
        n = sum(j['generation']==912 for j in tiles)
        packets,_ = packet_path(trace,912,expected_shape=(13+n,n))
        for fault in ('stop_decode','bad_seal'):
            out = args.temp/f'nes-prefix1007-c{key}-p{args.phase}-{fault}'
            replay(args.temp,trace,out,'control',packets,912,fault)
    else:
        run(args.temp,args.phase,args.count,args.ordered)
