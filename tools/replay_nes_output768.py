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


ROW_SCHEDULE_ELF = {
    "783": "ea3b037c91e6ab5d8682ecba45a08806867dda1b4f6250f2155b9734c480b883",
    "783B": "50fcc312a80f9cf926d685f83b9879c6a493c0644a5030d62f766186b16a92ba",
    "783C": "313fb97e14f96d48abd8badb362fb74c5cd57226212fa2923941e5683e0c3e8a",
    "783D": "edb1764fdc31778b36e00db86b1070ffee0d9f5393b898d2624cbf834bb3333a",
    "783E": "86ea95dcabbe2644a130fca6fbe9d19b38c26f12067c74340903fc149bcc3f9d",
    "783F": "4b821d9a7457375c48ec9ab136f9d7c711210c50ec436939a8bb36349b1cf84c",
    "783G": "e39c66995900e635da42b87567e84d51f73ba00cd0f1203b79447e72c315093f",
    "783H": "79ae5e0ffa23a9cbf7d0b5904440f6f3c0862d1ab3c8dca67ec3e9953ce7141a",
    "783I": "7962b52cfd74bc74989650e02729db24f0ee6b073150b222878bfa2c198287ab",
    "784A": "2d5c27ccf173815901bed0d04bfdbea2ac710ecc7c67c6a2fbf70e0fbcf6f6f5",
    "784B": "10a58880d65752936650a1e904c009bbed22421111cbc69c1cf4e91a5e1dfa5b",
    "784C": "206e807366fc4a5bd5902e7bb91760527712372325a65e18c46d18fd81ecd342",
    "784D": "c3190eee6125be5dd2c5e5196c0e3b172239573d457522dafc8ab27162a5d796",
    "785A": "eda26447e99225ecc79297c303df8002cc595b70da0816fec49306a5e53666c2",
    "785I": "62265e2b240feecd9562216577617ea30e3a93abfe9f71b90887bf19339da6aa",
    "785J": "4e3ac65800c2c8f3568d8dce1b3ebaeb3ffefc79b3181a4b924c93bc11d98406",
    "785K": "a4caba65dcc2af9a3a268d4323aa430b37a3d409eed9c2988f2fb8e92c972929",
    "785L": "a563183c2a3a404c6eef9aaf9b8c958850f35df4430e406fdfcac8bb7b80c5a6",
    "785N": "4b0ac5a29c1c799d489a57ed7618b472f33ee63c289b684d2914e3df43aa4b5c",
    "785O": "43756cb3ad9f3fe6fbc201654f5dd7816e82f1ea6de563b7ebea8d9288cf2a5b",
    "785P": "684b07c06af0286d97acb81e79637b100f093cd8e0d175678001a8dff02d7e40",
    "785V": "7411614234c3e3c59f6defdec2a8776f286b037590be65c1ebe69b8d92afd1f4",
    "788E": "b2e797bb764833f716de773fc9272d1120a99bfa787f8dab5165177a0cd0a7f2",
    "788F": "88e7d9ca54a95660562f76ab66e3cb2b42b0b5006b6db495fe751f4b7c89ea3f",
    "788I": "d9f5d520ebde4b1136ef394dfb68d2414a6581e9a3e0257a125d0c03a87cb17b",
    "788K": "ab126a8b76c0d01d9a602be3a833e63baa07798c1e134798fd2c2ae236a97425",
    "788N": "0328949d9af6cbedff549dbaeacc6d19f78fb735e7b955b5497abbfeb110d583",
    "788P": "a873640f2a5f781abf40fff99d5befcda004925579300a42679008d7e804e735",
    "788Q": "99325fb07e9d3d0f1385eee328f34acfcbd73a6da9391744904d8ff1b4766266",
    "787A": "efb989aded75377eae8f43b22990f86acbca3322ee19d8aa412f74068a093a95",
    "787B": "11d3428e34745ba7b4464843a7ee8a50337e42486b44ea3991c22b1d502712c6",
    "787C": "269a099b44297257d569762b5dee650226bd819aadce7f4272dbbaca3b584872",
    "787G": "680ac8ee1fcd8d2a9bb14dc473e4d2a540bad8aa06eedfd12308d47707e4f660",
    "787H": "9297c1447f3658435afd734f766b483bb9d85cf63feea2712f9ce9767b7847ee",
    "787I": "d7389b0d6ac0ee671afa4221583c46a590e920dd3c754e637e6e0e33fcc27094",
    "787J": "dacb6726767375fafd914f01fdf146dc1fe5dfe2d9ef58743ff39af218368d2e",
    "787K": "f23f8bbe70ccef1c8ce51db5dfb910a2d2cd3667d0b362467db67012a1771927",
    "787L": "32ac8cd54671e45ba354d936f15a7b7b234fd7d88562db0ab3e7da8aa02bdb48",
    "787M": "adf719ce9e19af8c07b85d443d82e60fbec044d438a59f122fa0ccf9bafa1d9c",
    "787N": "0cdee9d733b73f89abe23e67fc611c4e95aff7783e20c44d90b5c52f1e4e84d8",
    "787Q": "0b0d9c3907488f2cc94e888e5d7678af77f76fabe4d839f2dfbcea79454ccdeb",
    "787R": "1162c999b39beaef1d6abc2bee8c6ba6f95fa14b7e98d985118cdd00660a0299",
    "786A": "1e9e6c57596bd0a1de7332c1db961bc51a736d28bcb4a02c9f22cd81b2d1dafa",
    "786D": "8e3c74b44bd2740760c0d561957b7da74c20e2690069cd44ac63fef5f63a6881",
    "786E": "0f442b9e1c39a843621755c98ff27cb3477d73a7ee85f0be85a2952d0788a8f2",
    "786H": "66c6bb41b7412cabbeb3203754fb1dc6fb73c414eea774bc0a623603df021788",
    "786I": "f254ce8afc1a02bac53482b64b0cc186c6c7b6e48ffaaf512a027abe670ecf0d",
    "786J": "4f9266d4da6652b0cbb171349b5c7e75dc703e1be6a9f121a696e5bb086db61b",
    "786K": "3fa9b87a658854c35d9de1e6f9191d0826c21128cf27108bb8b4d7133cfeb8ee",
    "786M": "ca8107c7724637af422211e72032399c039a1767a45c1f65c9ee18a03f035a0d",
}

def replay(variant, extras, remaining, omit_wait, receipt969=False, watch969=False, map969=False, right969=False):
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
        if variant in ("781B","781C","782","782B","782C","782D","782E",*ROW_SCHEDULE_ELF):
            # Warm banks run the original rank-ordered object builder after
            # slot zero, before normal BG. The oracle still independently
            # compares every encoded byte, tile payload and END against 763.
            original_link = link
            class ObjectFirst(original_link):
                def __init__(self, options):
                    super().__init__(options)
                    for g in range(907, LAST+1):
                        if variant in ("782","782B","782C","782D","782E",*ROW_SCHEDULE_ELF):
                            geometry=(options.data/f"frame{g}.geometry").read_bytes()
                            if int.from_bytes(geometry[5732:5734],"little")>24:
                                continue
                        plans=self.plansets[g]
                        assert plans[0][6]==2 and all(q[6]<2 for q in plans[1:])
                        self.plansets[g]=[plans[0]]+[q for q in plans if q[6]==1]+[q for q in plans if q[6]==0]
            link=ObjectFirst
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
    if variant in ROW_SCHEDULE_ELF:
        expected=ROW_SCHEDULE_ELF[variant]
    if variant == "782C":
        expected="8bf256d955da327c8359a78823b8e2d542f5bbbb6db09fd561622114579b4b08"
    if variant == "782D":
        expected="7193456ca235672c4f116bd30581a1a3b81fadf7f822e95ad9b092ad52ff0a87"
    if variant == "782E":
        expected="e4e80459428edaedbc48b129e448ca85632e7790c8cdf03623c82caebde59e42"
    if variant == "782B":
        expected="feb6530402c23d07cdcc5aecc6293754b34252db3643da1ea0c0876f47a2da2b"
    if variant == "782":
        expected="e5e1a8f4ccef3bff3ea7d0c4dcef46b1c9e46f10b7934caf0fc464fabf0753de"
    if variant == "781C":
        expected = "a60455581ca6488fe8ba268d8c0693fd5ac83842f1e47861b43583502fb5fcbc"
    if variant == "781B":
        expected = "1ae609dc37e1384e8a5321cea961ce624bde53bb04453ca9d4b61b82392be7e8"
    if variant == "781":
        expected = "4343596585c1407dbb68f9cfef814805775d98091548f36d07922461652540b2"
    if variant == "780":
        expected = "74069c77d65b569e831d344b77e53f0a7c02287792bc4fa31123a7686d662d8f"
    if variant == "779C":
        expected = "5f99912fbab534eca552affad778b300cac0274bbeb27c1aff5a0697bb6bead9"
    if variant == "779B":
        expected = "70ce148d04c005532e93683ec37d5f231718b7b07410d573a10451956c8ddc5d"
    if variant == "779":
        expected = "27f1877c3f0adebcf5594a9be51328cbebb635a9dfa55a4d98c6c29ba4dec87b"
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
        if variant in ("781B","781C","782","782B","782C","782D","782E",*ROW_SCHEDULE_ELF):
            # Tile END precedes CGRAM and raw writes. Sample the original
            # complete set of observer fields at the checked planner exit.
            from functools import partial
            import test_nes_tail646 as observer
            stack.enter_context(patch.object(observer,"watch",partial(observer.watch,complete="nes_resident211_prepare")))
        if map969 or right969:
            from test_nes_rows757 import observe
            stack.enter_context(patch.object(Runtime, "__init__", observe(Runtime.__init__, 969, 1024, 2559 if right969 else 1407)))
        if watch969:
            from trace_nes_prefix777 import observe
            stack.enter_context(patch.object(Runtime, "__init__", observe(Runtime.__init__)))
        if receipt969:
            assert variant == "767" and not omit_wait
            stack.enter_context(patch.object(Runtime, "__init__", immediate969))
        if omit_wait:
            stack.enter_context(patch.object(Runtime, "__init__", hook))
        runpy.run_module("test_nes_status689" if variant in ("763","770","779C","780","781","781B","781C","782","782B","782C","782D","782E",*ROW_SCHEDULE_ELF) else "test_nes_static751",run_name="__main__")


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
    p.add_argument("variant", choices=("763","767","769","770","771","776","776B","777","777B","778","778B","779","779B","779C","780","781","781B","781C","782","782B","782C","782D","782E",*ROW_SCHEDULE_ELF))
    p.add_argument("extras", type=Path)
    p.add_argument("--omit-wait969", action="store_true")
    p.add_argument("--right969", action="store_true",help="also observe both right-page map ranges")
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
        replay(a.variant,a.extras,rest,a.omit_wait969,a.receipt969,a.watch969,a.map969,a.right969)
