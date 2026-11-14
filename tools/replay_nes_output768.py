# SPDX-License-Identifier: MIT
"""Extend the linked 763/767 schedule through the workload-matched capture 969."""
import argparse
import json
import runpy
import shutil
import sys
from contextlib import ExitStack
from itertools import groupby
from pathlib import Path
from unittest.mock import patch

from analyze_nes_scroll229 import FETCH, records
from check_nes_record657 import bench, encode, prepare as sender
from check_nes_snoop601 import pin, read, samples, sha
from prepare_nes_dense519 import ROM_SHA, tiles
from test_nes_schedule496 import prepare

LAST = 970
ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT.parent / "probes"


def inputs(out, game):
    pin(game, ROM_SHA)
    out.mkdir(parents=True, exist_ok=False)
    original = PROBES / "nes-output489/audit01"
    fixture = out / "fixture"
    fixture.mkdir()
    prepare(argparse.Namespace(rom=game, frames=LAST-904, compact=original, row_counts=None), fixture, True)
    assert tiles(fixture, 957) == tiles(PROBES / "nes-dense519/fixture02", 957)
    for g in range(905, LAST+1):
        prior = PROBES / "nes-seal538/plans01" if g <= 957 else original
        dst = out / "plans" / f"frame{g}"
        dst.mkdir(parents=True)
        shutil.copyfile(prior / dst.name / "plans.json", dst / "plans.json")
        assert (original / dst.name / "expected-hdma.bin").read_bytes() == (fixture / f"expected-{g}.bin").read_bytes()
    geometry = PROBES / "nes-geometry230"
    fetch = geometry / "capture02/ppu-fetch.bin"
    stim = geometry / "stim05"
    pins = read(stim / "result.json")
    pin(stim / "result.json", read(ROOT / "analysis/geometry230-verification.json")["stimulus_result_sha256"])
    pin(fetch, pins["inputs"][fetch.name])
    by_frame = {r["frame"]: r for r in pins["frames"]}
    chr_rom = game.read_bytes()[0x40010:]
    cache = {}
    for gen, rows in groupby(records(fetch, FETCH), key=lambda r:r[0]):
        if not 958 <= gen <= LAST:
            continue
        raw = stim / f"frame{gen}.hex"
        pin(raw, by_frame[gen]["stimulus_sha256"])
        writes, _ = samples(rows, raw, chr_rom)
        lines = {}
        for kind, addr, value in writes:
            if kind:
                tag = addr // 16
                key = tag % 128
                if key not in lines or lines[key][0] != tag:
                    lines[key] = [tag, {}]
                lines[key][1][addr % 16] = value
        cache[gen] = lines
    assert list(cache) == list(range(958, LAST+1))
    (out / "obj-cache.json").write_text(json.dumps(cache), encoding="utf8")


def replay(variant, extras, remaining, omit_wait, receipt969=False, watch969=False, map969=False):
    import test_nes_obj609 as obj
    import test_nes_tile532 as tile

    original_capture = obj.capture
    original_schedule = tile.run_schedule
    def capture(path):
        frames = original_capture(path)
        for g, lines in read(extras / "obj-cache.json").items():
            frames[int(g)] = {int(k):(tag, {int(addr):v for addr,v in data.items()}) for k,(tag,data) in lines.items()}
        return frames
    def schedule(args, instrument, link, frames):
        assert frames == 53
        def extended_oracle(source, options):
            source = instrument(source, options)
            for gen in range(958, LAST+1):
                directory = args.capture / f"frame{gen}"
                expected = (directory / "expected-cgram.bin").read_bytes() + (directory / "expected-oam.bin").read_bytes()
                assert len(expected) == 1056
                (args.out / f"colors636-{gen}.bin").write_bytes(expected)
            if variant in ("770", "771"):
                # Observe actual cartridge timestamp writes in the same callback
                # domain as the independently logged PPU DMA and final ACK.
                marker = "local function loaded()"
                assert source.count(marker)==1
                source = source.replace(marker, """local marks769=assert(io.open(ROOT..'/marks769.csv','w'))
checkedMem527(function(a,v)
 local st=emu.getState()
 marks769:write(string.format('%d,%d,%d,%d,%d,%d\\n',pw(8),a,v,st.frameCount,st['ppu.scanline'],st.masterClock))
 marks769:flush()
end,emu.callbackType.write,0x7004,0x7007)
""" + marker)
            return source
        return original_schedule(args, extended_oracle, link, frames=LAST-904)
    # Counterfactual only on 969. Execute the existing no-wait branch without
    # modifying the linked code, E0 validation, packet admission or final ACK.
    from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_PC
    from test_nes_raw506_joint import Runtime
    base_init = Runtime.__init__
    def hook(cpu, args, link):
        base_init(cpu, args, link)
        assert variant == "767"
        pc, resume = 0x0801eb08, 0x0801eb26
        assert bytes(cpu.u.mem_read(pc, 2)) == bytes.fromhex("2368")
        def omit(u, address, size, unused):
            if cpu.generation == 969 and not cpu.irq:
                cpu.events.append(dict(event="omit_optional_wait768", generation=969, clock=cpu.clock))
                u.reg_write(UC_ARM_REG_PC, resume | 1)
        cpu.u.hook_add(UC_HOOK_CODE, omit, begin=pc, end=pc)

    def immediate969(cpu, args, link):
        # Isolate the branch on the original image after 968 ACK. The normal
        # receipt, bounded loop increment and next poll's STOP guard still run.
        from unicorn.arm_const import UC_ARM_REG_R4
        from check_nes_game478 import UC_ARM_REG_R0
        base_init(cpu,args,link)
        pc=0x0801f94e
        assert bytes(cpu.u.mem_read(pc,12))==bytes.fromhex("2046fff710fb002881d00135")
        def checked(u, address, size, unused):
            if cpu.generation!=969 or cpu.irq:
                return
            plan=u.reg_read(UC_ARM_REG_R4)
            layout=cpu.layout['nes_plan200']
            window=int.from_bytes(u.mem_read(plan+layout['window'],4),'little')
            last=bytes(u.mem_read(window+cpu.layout['nes_sink_window184']['last'],2))
            descriptor=bytes(u.mem_read(plan+layout['bulk'],12))
            if last!=bytes([9,4]) or int.from_bytes(descriptor[8:12],'little')!=160:
                return
            assert not u.mem_read(plan+layout['bulk_pending'],1)[0] and u.reg_read(UC_ARM_REG_R0)==1
            assert descriptor[0:8]==bytes.fromhex("010140008000c903")
            cpu.events.append(dict(event="checked_receipt776",generation=969,clock=cpu.clock))
            u.reg_write(UC_ARM_REG_PC,0x0801f959)
        cpu.u.hook_add(UC_HOOK_CODE,checked,begin=pc,end=pc)

    def diagnostic(cpu, args, link):
        from check_nes_game478 import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR
        from test_nes_raw506_joint import MASTER
        base_init(cpu,args,link)
        def window(u, address, size, unused):
            # Exercise the actual logger in this 66-frame fixture. Change only
            # the argument to its elapsed-time filter, never the system tick.
            u.reg_write(UC_ARM_REG_R0,2500+cpu.generation-905)
        def mailbox(u, address, size, unused):
            assert bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),8))==bytes([0x78])+bytes(7)
            cpu.clock=link.rpc(cpu.clock)
            writes=(args.out/"marks769.csv").read_text().splitlines()
            # EA already advanced the input generation. The page still holds
            # the most recent SNES ACK, until the next SEAL.
            g=int(writes[-1].split(",",1)[0])
            rows=[list(map(int,x.split(","))) for x in writes if x.split(",",1)[0]==str(g)]
            assert [r[1] for r in rows]==[0x7004,0x7005,0x7006,0x7006,0x7007]
            rx=bytes([0,0x78,rows[0][2],rows[1][2],rows[3][2],rows[4][2],0x5a,0xa5])
            cpu.clock+=cpu.observer_cost.get("screen146",64*MASTER/2625000)
            cpu.clock=link.rpc(cpu.clock)
            u.mem_write(u.reg_read(UC_ARM_REG_R2),rx)
            u.reg_write(UC_ARM_REG_R0,1)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        def record(u, address, size, unused):
            # Input prefetch also calls consumed() while output is still live.
            if int.from_bytes(u.mem_read(cpu.data_symbols["live769"],4),"little"):
                return
            count=int.from_bytes(u.mem_read(cpu.data_symbols["count769"],2),"little")
            assert 1<=count<=66
            data=bytes(u.mem_read(cpu.data_symbols["ptrcache"],36*count))
            (args.out/"registered769.bin").write_bytes(data)
            assert data[-27]&1,(cpu.generation,data[-36:].hex())
        for name,callback in (("begin769",window),("nes_rom_spi_transfer",mailbox),("nes_native165_consumed",record)):
            pc=cpu.syms[name]
            cpu.u.hook_add(UC_HOOK_CODE,callback,begin=pc,end=pc)
    pin_path = Path(remaining[remaining.index("--arm")+1]) / "obj-nes-100/sd2snes.elf"
    manifest = read(ROOT / f"analysis/trial{763 if variant == '763' else 767}-package.json")
    expected = manifest["variants"]["763"]["ELF"] if variant == "763" else manifest["ELF"]
    if variant == "778B":
        expected = "b875e3a9aefb359f0e5192f066c8d3cf932fc5b2905153bdf08e90ad99ece4ff"
    if variant == "778":
        expected = "f2167762b618b3fda45eb629a693fb8915adf818dd8212b66c97ec73af716507"
    if variant == "777B":
        expected = "31d63bf16abba708dc8527ab1c156ba5468cf6a65c442b8d6028d0bf78110418"
    if variant == "777":
        expected = "7942d92ea7dcb9383c2fd7d094962a812b23f43edb29690cabc7e0a83bec818a"
    if variant == "776":
        expected = "4cbfd9734d380a6831f839593d38df69a84ad13a7a708af6f14f57eb32b93d71"
    if variant == "776B":
        expected = "a840292b38bc742b148da653f1c91127a6b85cdfe966db81b5faca4a952cbb8e"
    if variant == "769":
        expected = "bf7eb6f4904f5d22b50f919e8ec175e256e938e653406ddf24ba2ad13e3f8aa9"
    if variant in ("770","771"):
        expected = {"770":"0dc7ab4ef1df47f5325f39930eaeae06418c83890a37e9c1e2ab7f38435d185e",
                    "771":"e8500e87ccb247bf573ba35ee7156c09d9a8c0ee0681207cd5b5fd16aed1073f"}[variant]
    pin(pin_path, expected)
    sys.argv[1:] = remaining
    with ExitStack() as stack:
        stack.enter_context(patch.object(obj, "capture", capture))
        stack.enter_context(patch.object(tile, "run_schedule", schedule))
        if variant in ("770","771"):
            stack.enter_context(patch.object(Runtime,"__init__",diagnostic))
        if map969:
            from test_nes_rows757 import observe
            stack.enter_context(patch.object(Runtime, "__init__", observe(Runtime.__init__, 969, 1024, 1407)))
        if watch969:
            from trace_nes_prefix777 import observe
            stack.enter_context(patch.object(Runtime, "__init__", observe(Runtime.__init__)))
        if receipt969:
            assert variant == "767" and not omit_wait
            stack.enter_context(patch.object(Runtime, "__init__", immediate969))
        if omit_wait:
            stack.enter_context(patch.object(Runtime, "__init__", hook))
        runpy.run_module("test_nes_status689" if variant in ("763","770") else "test_nes_static751",run_name="__main__")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("inputs")
    p.add_argument("out", type=Path)
    p.add_argument("game", type=Path)
    p = sub.add_parser("sender")
    for arg in ("out", "board", "bin", "prefix"):
        p.add_argument(arg, type=Path)
    p = sub.add_parser("run", add_help=False)
    p.add_argument("variant", choices=("763","767","769","770","771","776","776B","777","777B","778","778B"))
    p.add_argument("extras", type=Path)
    p.add_argument("--omit-wait969", action="store_true")
    p.add_argument("--map969", action="store_true")
    p.add_argument("--watch969", action="store_true")
    p.add_argument("--receipt969", action="store_true")
    a, rest = parser.parse_known_args()
    if a.action == "inputs":
        assert not rest
        inputs(a.out,a.game)
    elif a.action == "sender":
        assert not rest
        a.data = PROBES / "nes-delta231/test07"
        a.guards = False
        sender(a, encoder=encode, codec="nes_geometry_sender653.sv",
               bench=lambda s:bench(s,False,False,True,False,False), generations=range(957,LAST+1))
        prefix, tail = read(a.prefix), read(a.out / "sender.json")
        assert [r["wire"] for r in tail["957"]] == [r["wire"] for r in prefix["957"]]
        (a.out / "joint-sender.json").write_text(json.dumps({**tail,**prefix}),encoding="utf8")
    else:
        replay(a.variant,a.extras,rest,a.omit_wait969,a.receipt969,a.watch969,a.map969)
