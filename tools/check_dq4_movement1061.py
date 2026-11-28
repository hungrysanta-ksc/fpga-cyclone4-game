"""Replay the supplied journal pair through the linked ARM and sector-backed FatFS."""
import json
import struct
import zlib
from pathlib import Path
from analyze_dq4_movement1061 import decode, WINDOW_MS
from check_cart_debug1060 import Card, fat16
from check_ff3_airship1051 import layouts
from check_ff3_sd1043 import (UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                              UC_ARM_REG_R3, UC_ARM_REG_PC, UC_ARM_REG_LR)
from prepare_dq4_movement1061 import OUT


def run():
    src = OUT / "debug/link/src"
    m = Card(src, fat16())
    u = m.u
    u.mem_map(0x20010000, 0x10000)
    u.mem_map(0xe000e000, 0x1000)
    u.mem_map(0x40013000, 0x1000)
    def peripheral(cpu, pc, size, value):
        cpu.reg_write(UC_ARM_REG_R0, value)
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
    for fn, val in (("nes_diag_observe.constprop.0", 0), ("get_snes_reset", 1), ("nes_diag_ticks", 10), ("delay_us", 0)):
        if fn in m.sym:
            pc = m.sym[fn] & ~1
            u.hook_add(UC_HOOK_CODE, peripheral, val, pc, pc)
    path, fil, buf, count = 0x20010000, 0x20010200, 0x20011000, 0x20010100
    def name(s):
        u.mem_write(path, s.encode() + b"\0")
        return path
    m.fixture = True
    for directory in ("/sd2snes", "/sd2snes/nesstate"):
        assert m.call("f_mkdir", name(directory)) == 0
    rom = 0x9ac62bb9
    for suffix, local in (("a", "a (1)"), ("b", "b")):
        raw = (Path.home() / "Downloads" / f"9ac62bb9-100000-1{local}.nsv").read_bytes()
        h = struct.unpack_from("<9I", raw)
        assert h[:6] == (0x5353454e, 1, rom, 0x100000, 1, 22280)
        assert h[7:] == (zlib.crc32(raw[36:]), zlib.crc32(raw[:32]))
        assert len(raw) == 36 + h[5]
        u.mem_write(buf, raw)
        assert m.call("f_open", fil, name(f"/sd2snes/nesstate/9ac62bb9-100000-1{suffix}.nsv"), 10) == 0
        assert m.call("f_write", fil, buf, len(raw), count) == 0
        assert int.from_bytes(u.mem_read(count, 4), "little") == len(raw)
        assert m.call("f_close", fil) == 0
    m.fixture = False
    m.rom(rom)
    u.mem_write(m.sym["nes_board_id"], b"\x84")
    u.mem_write(m.sym["nes_cart_bytes"], struct.pack("<I", 0x100000))
    u.mem_write(m.sym["ff3_next_slot"], b"\1")
    m.state = bytearray(22280)
    assert m.call("nes_restore_boot_battery", instructions=180000000) == 1
    assert m.state == raw[36:] and not m.flags and m.writes == 0
    assert tuple(struct.unpack("<3I", u.mem_read(m.sym["movement_save"], 12))) == (rom,4,0xcaa52cd8)
    _, v = layouts(src, ("nes_native165","nes_native_video165"))
    video = 0x21000000
    u.mem_map(video, 0x10000)
    queries = 0
    def event(cpu, pc, size, key):
        nonlocal queries
        val = clock
        if key == "nes_native165_bulk":
            _, tx, dst, length = [cpu.reg_read(k) for k in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            assert length == 16 and cpu.mem_read(tx,1) == b"\x78"
            queries += 1
            p = bytearray(16)
            p[1] = 0xd2
            struct.pack_into("<H", p, 2, gen)
            p[4] = 0x31 if gen >= 3 else 0
            stamps = [(clock//65536 - n) % 4096 for n in (6, 3, 1, 0)]
            p[5:9] = bytes(s & 255 for s in stamps)
            p[9] = (stamps[0] >> 8) | ((stamps[1] >> 8) << 4)
            p[10] = (stamps[2] >> 8) | ((stamps[3] >> 8) << 4)
            move = (3*4200000//65536 - 12) % 4096
            p[11], p[12], p[15] = move & 255, move >> 8, 0 if torn else 0x5a
            cpu.mem_write(dst, bytes(p))
            val = 1
        cpu.reg_write(UC_ARM_REG_R0, val)
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
    for key in ("nes_native165_bulk", "nes_cost471_now"):
        pc = m.sym[key] & ~1
        u.hook_add(UC_HOOK_CODE,event,key,pc,pc)
    for torn in (False, True):
        m.call("nes_budget210_reset")
        for gen in range(1, 119):
            clock = gen*4200000
            u.mem_write(video+v["generation"], struct.pack("<H", gen))
            m.call("e0900", gen, 0)
            m.call("nes_budget210_display", gen*5, video)
        recording = u.mem_read(m.sym["ptrcache"], 7512)
        if torn:
            try:
                decode(recording)
            except ValueError:
                pass
            else:
                raise AssertionError("torn trace accepted")
        else:
            identity, rows = decode(recording)
            assert identity == (rom,1,4,0xcaa52cd8) and len(rows) == 110
            assert rows[0]["gen"] == 3 and rows[-1]["gen"] == 112
            assert rows[-1]["at_ms"] < WINDOW_MS
    return dict(slot=1, selected_serial=4, body_crc="caa52cd8", restored_bytes=len(m.state),
                synthetic_publications=110, window_ms=WINDOW_MS, torn_rejected=True)


if __name__ == "__main__":
    result=run()
    (OUT/"movement.json").write_text(json.dumps(result, indent=2))
    print(result)
