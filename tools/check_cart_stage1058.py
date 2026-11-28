"""Drive the linked retail ARM resident table with stage-frame CHR addresses."""
import json
import re
import struct
from pathlib import Path
from statistics import median
from check_ff3_backdrop1046 import layouts
from check_ff3_sd1043 import Machine, fat16, UC_HOOK_CODE, UC_ARM_REG_SP
from prepare_cart_stage1058 import BASE, OUT


def replay(tags, dirty):
    src = BASE / "release/link/src"
    machine = Machine(src, fat16())
    u = machine.u
    rx, resident = layouts(src, ("nes_native165", "nes_resident211"))
    scratch = 0x21000000
    u.mem_map(scratch, 0x20000)
    u.mem_map(machine.sym["__stack"], 4096)
    receiver, header, state = scratch, scratch + 0x4000, scratch + 0x8000
    u.mem_write(machine.sym["nes_board_id"], b"\x82")
    machine.call("nes_native165_reset", receiver)
    flags = ((255 ^ dirty) << 1) | (dirty == 0)
    word = (0x2234 << 48) | (1 << 42) | (1 << 36) | (224 << 28) | (flags << 3)
    u.mem_write(header, struct.pack(">HHQ", 0xe000, 1, word))
    assert machine.call("nes_native165_packet", receiver, 0, header, 12)
    received, = struct.unpack("<H", u.mem_read(receiver + rx["dirty_chr"], 2))
    assert received == dirty

    machine.call("nes_resident211_reset", state)
    def put(name, data):
        u.mem_write(state + resident[name], data)
    put("bg", struct.pack("<" + "H"*len(tags), *tags))
    put("bg_slots", struct.pack("<H", len(tags)))
    put("resident", bytes([255])*288)
    put("epoch", struct.pack("<I", 1))
    def caller(cpu, pc, size, unused):
        cpu.mem_write(cpu.reg_read(UC_ARM_REG_SP), struct.pack("<II", header | 1, 0))
    pc = machine.sym["nes_resident211_begin"] & ~1
    u.hook_add(UC_HOOK_CODE, caller, None, pc, pc)
    assert machine.call("nes_resident211_begin", state, 1, 1+received, 1)
    for bank in range(2):
        bits = u.mem_read(state + resident["resident"] + bank*144, 144)
        valid = [bool(bits[i//8] & 1<<(i%8)) for i in range(len(tags))]
        assert valid == [not (dirty & 1<<(t//64)) for t in tags]
    return sum(valid)


def main():
    stage = (BASE / "stage-7.txt").read_text().split("FRAME 2100 ",1)[1].split("FRAME ",1)[0]
    pages = {int(g)//8 for g in re.findall(r"CHR group=(\d+)", stage)}
    assert pages == {0,5,6}
    tags = sorted({int(line.split()[0],16)//16 for line in (BASE/"pattern-7.txt").read_text().splitlines()})
    snapshots = {str(mask): replay(tags, mask) for mask in (255, sum(1<<p for p in pages))}
    assert list(snapshots.values()) == [0,76]
    physical = {}
    for file in (Path.home()/"Downloads").glob("nes-frame-debug1057-*.bin"):
        b = file.read_bytes()
        magic,version,mode,count,_,_,size,_=struct.unpack_from("<8H",b)
        assert magic==0x9001 and version==1057 and size==60 and count<=80
        rows=[struct.unpack_from("<6H4B",b,16+i*size) for i in range(count)]
        tail=[r for r in rows if r[0]>=5500 and r[8]&3==3]
        if tail:
            physical=dict(samples=len(tail),unchanged_map=sum(r[7]==0 for r in tail),
                          input_to_valid_ack_ms_median=median((r[3]-r[4])*512/84000 for r in tail),
                          displayed55=struct.unpack_from("<H",b,4816)[0])
    report=dict(reference_frame=2100,read_tags=len(tags),written_pages=sorted(pages),
                warm_bank_retained=snapshots,physical_1057=physical)
    (OUT/"stage-arm.json").write_text(json.dumps(report,indent=2))
    print(report)

if __name__=="__main__":
    main()
