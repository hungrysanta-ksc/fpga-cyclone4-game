"""Check the linked capture window, real wire classifier counters, and snapshot receipt."""
import argparse
import json
from pathlib import Path
from check_nes_longrun693 import Probe, UC_ARM_REG_R1, UC_ARM_REG_R2, sha
from read_nes_frame769 import decode
from check_nes_trial763 import timed
from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R3


class Capture(Probe):
    # The original 763 runtime requires a nonzero timed limit at initialization.
    def call(self, name, args):
        if name=="nes_runtime165_begin" and self.src.parent.name.startswith("arm770"):
            args=list(args);args[8]=6000
        return super().call(name,args)

    reply = bytes.fromhex("00 78 fe ff 00 01 5a a5")
    def hook(self, u, at, size, user):
        if at == self.syms.get("nes_rom_spi_transfer", -1) and u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0]==0x78:
            assert bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1), 8)) == bytes([0x78])+bytes(7)
            u.mem_write(u.reg_read(UC_ARM_REG_R2), self.reply)
            self.ret(u, 1)
            return
        super().hook(u, at, size, user)


def check_save(q, src, raw):
    # Execute the real report formatter/IRQ bracket and intercept FatFS only.
    q.u.mem_map(0xe000e000,0x1000)
    state=0x20012000
    q.u.mem_write(state,b"PREPARED_RESET_HELD\0")
    files={}
    current=None
    def fat(cpu, at, size, name):
        nonlocal current
        if name=="f_open":
            current=bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),96)).split(b"\0")[0].decode()
        elif name=="f_write":
            n=cpu.reg_read(UC_ARM_REG_R2)
            files[current]=bytes(cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),n))
            cpu.mem_write(cpu.reg_read(UC_ARM_REG_R3),n.to_bytes(4,"little"))
        elif name=="f_close":
            current=None
        q.ret(cpu,0)
    for name in ("f_open","f_write","f_close","printf"):
        pc=q.syms[name]
        q.u.hook_add(UC_HOOK_CODE,fat,name,begin=pc,end=pc)
    q.call("save_report",[state,0])
    assert not files
    q.call("save_report",[state,1])
    number=src.parent.name[3:6]
    assert files[f"/sd2snes/nes-frame-mmc{number}.bin"]==raw
    budget=files[f"/sd2snes/nes-budget-mmc{number}.txt"].decode()
    assert len(list(decode(raw,budget)))==2
    return sorted(files)


def run(src):
    q = Capture(src)
    def value(name, size):
        return int.from_bytes(q.u.mem_read(q.data[name], size), "little")
    q.call("nes_budget210_reset", [])
    for tick, count in ((2499, 0), (2500, 1), (2999, 2), (3000, 2)):
        q.call("begin769", [tick])
        assert value("count769", 2) == count
        assert bool(value("live769", 4)) == (2500 <= tick < 3000)
        if tick == 2500:
            q.u.mem_write(value("live769",4)+31,b"\x01")
            for i in range(9):
                q.call("poll769", [i, 1])
                q.call("poll769", [i, 0])
            assert q.call("sample769", [0x1fe])
        if tick == 2999:
            assert q.call("sample769", [0xff])
            for _ in range(256):
                q.call("poll769", [3, 0])
    raw = bytes(q.u.mem_read(q.data["ptrcache"], 72))
    rows = list(decode(raw, "frame769=1\ntick_ms=10\nrows=2\ndropped=0"))
    a,b = rows
    assert a["valid"] and a["seal_to_dma_vb"] == a["dma_to_ack_vb"] == 1
    assert (a["output_E0_quiet"],a["output_E8_ready"]) == (5,4)
    assert a["E0_drained_quiet"] == a["E8_finish_ready"] == 1
    assert not b["valid"] and b["saturated"] and b["E0_final"] == 255
    filenames=check_save(q,src,raw)
    q.call("begin769", [2999])
    q.reply = bytes.fromhex("00 78 fe 00 00 00 5a 00")
    q.call("sample769", [0xfe])
    assert not q.u.mem_read(value("live769",4)+9,1)[0]
    for _ in range(225):
        q.call("begin769", [2999])
    assert value("count769",2)==227 and value("dropped769",2)==1 and not value("live769",4)
    q.call("nes_budget210_reset", [])
    assert not value("count769",2) and not value("dropped769",2)
    # Count completed displays at the normal comparison-window boundaries.
    for tick in (499,500,3999,4000,5499,5500,6000,360000):
        q.call("nes_budget210_frame",[tick])
        q.call("nes_budget210_display",[tick,q.video])
    base=0x20012000
    size=q.call("nes_budget210_format",[base,6144])
    assert 0<size<6144
    budget=bytes(q.u.mem_read(base,size)).decode()
    assert "display_5_40_55=2,2\n" in budget and len([s for s in budget.splitlines() if s[:1]=="b"])==12
    mode={}
    if src.parent.name.startswith("arm771"):
        mode=timed(src)["cases"]
    else:
        for ticks in (5999,6000,360000):
            q=Capture(src)
            q.board=True;q.now=ticks;q.u.mem_write(q.data["ticks"],ticks.to_bytes(4,"little"))
            if src.parent.name.startswith("arm772"):
                q.put(q.rt,"nes_native_runtime165","service",q.syms["native_service165"]|1,4)
            ok=q.call("nes_runtime165_step",[q.rt])
            actual=q.get(q.rt,"nes_native_runtime165","result")
            assert bool(ok)==(actual==0)
            assert actual==(1 if src.parent.name.startswith("arm770") and ticks>=6000 else 0)
            mode[ticks]=actual
    return dict(firmware=sha(src/"obj-nes-100/firmware.stm"), passed=True, mode=mode, windows=[2,2], modeled_FatFS_files=filenames,
                cases=["tick bounds","reason counts","NMI wrap","bad generation","bad signature",
                       "counter saturation","full buffer","reset"], SPI="injected response to actual linked ARM")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("src",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a.src),indent=2)+"\n")
