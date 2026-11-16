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


CONTROL_ELF = {
    "811": "5d45693e95da069641cadd7601cb09ac0cf5de047f0f22dfeff770fa03ecfbae",
    "812": "d8e2f9a0d980d7bd34aaf2c07093ae0f36abdb3078f597df6c84f5f38c067fc5",
    "812B": "9e397034dd445a349adfe824682e5ef5bf6a427ef8fb656a98248e1b0035d60d",
    "813": "573d336a9fb05687cde57eb134a12c77dd5b41a4b5576d8a0d42af37daa6f67c",
    "814": "cb70cc3aad7bff2a0d1e8df45575be2e42695a513b447b0d180ca71abfca4488",
    "812C": "cf5e930a5486c984976c5091bfe248fa6974ae6cbec6c1dfd0f118db19114bcb",
    "810I": "735361910caa57f08c1df5102e2634d2d577c8834f7b100ea871d61149eeea5f",
    "810H": "4df559b222da210336d8b03386f225278121707ff4315b4fb9e1d257d85c4b13",
    "810G": "4d603853de584e8394d30ec1cede35f8bf6c71b123d2e859587b3e0ec1a15e04",
    "810F": "5c2506f6505e4e164ffa5d0b924ced76223e898bd9ea4b354c217c55295c5c9b",
    "810E": "353d53f76af909d0ab9ce40ccd0f12f77abdb3eb1304ba4514133489ac4e2bb4",
    "810D": "2cd1bc3e461f306d2a6af66ad161c046d65c58b75cae0ab749a92f83a7799846",
    "810C": "947c8f69829c3648997a7f229f3316024fa006289ddd1cd7a81961233bcc995f",
    "810B": "0ce288b79ebfe860194b1f45bb8a156af799dcd9451c3fc5e7703b8c561467da",
    "810": "5276828d5694e22601495a8fae78b54d5ea04aad0f6c78d7ffa7c8bbe6bc6ddb",
    "809": "ea8b94b709277b7f0cb00b5673be6f9a739d825592c1324a85096f6490c564ad",
    "807": "d235e48351629ed83856964959d5af25493331389cf364f28abceedd376e0a0b",
    "808": "d91a41acbd7fea2bcedbcdf97c0bc671df1fbbedb509649b6444376ca75a3632",
    "805": "e7963092a753198a2c126fe0060531756063fd0477885abbed4c793bacb006c2",
    "806": "0a903f9cf0df8587430fe3e34f8666c62e4d1aa15969a1625a681c4b0c21615e",
    "804T": "e35b752b40bc984da5acf16de22702415faea95a4afc8d045b0cb4d91dc24f01",
    "804L": "4992ec7f821811c71e21fe8f10c5c8b77c599464d7dadbda3e45b5de76a4783d",
    "802": "7d9009a60ed920b8224c1772a8759011a9723b109988ec2fb9a0c32868ac709b",
    "803": "1d82054c91c608e6c3ba81f63200f0fdd7f051f47cdf9c42dfcc7022536bea77",
    "798": "24439b9438fd1099863947d2005349ef873660d30032e3e988a8a87a912dc39d",
    "799": "145106e7d2b2cfd21e18b434156daa4dcae3bcb2701b17d867e71f6cbeea644e",
}
ROW_SCHEDULE_ELF = {
    "796": "ffeacc6ceb1a8294f61705daae7c8fab4a111cfa9a3ff26c4ca965905c1a5c3f",
    "797": "b15086991d1927dde200938d34f36911cedc59ab423d529e2bc176f302dc2df5",
    "793": "1ab6a50a7651ec7b1f1672b9f6649c4a6cdf34b572b7d9a6fead071100ff719a",
    "792": "2a9c76a026cde2247f9075c2d16f58be1c35555b71911ce5d73ad9ed3d1c9d69",
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
    "791A": "7bd790564133d173277753fe14ece2896f38c0db8326bcedefb8ed930ef4c552",
    "791B": "02db26b9b371c0401b8737068f32a9c6adee697cf62738de7e32eae613bc7464",
    "791C": "252cf950523901c052d22c56a14109cc15e38d749222b0e10a4fd29b059cdb3a",
    "791I": "7b0aa54ec41659288893e7e4e085224a79f686dcd07522d8b1588676b95611c8",
    "791J": "10ca9049aeec66f4124f493bb9f9739fab8eefff968a19455d3722cddbcaaddf",
    "791P": "6f9e000a5e2810d7e2d5ea4e6b2d889bc8df5702002a376b40099eada2f78981",
    "791Q": "2fe5bce9888a22527d184fa8446680c608cebc8ea661ac1064b47b77e800d69a",
    "791R": "a76263cb9fef1f6ab1d9434bc591b00dd9de4311f4b31f3ea120b8ed587fd5fa",
    "790A": "9401c016bb4492fa95159a22d64c66c7c499519e07918231472988ad9a66f2a6",
    "790B": "939f5b887bb1acc27faf0f4bd9ab74e2b9e049f750f2507f103a418d2736fd7f",
    "790C": "698635c3b374b760236d4926395c3d75b24a62146a8c808495faad18166b2838",
    "790G": "6356ea3398d96db6781d33070494eaec0dde633d506e940658c1361d5f55f322",
    "790H": "ff4458fafe0fc93821dc85a3d13f773b8013f3e16e5a098cbbeea9c3ff35cb6b",
    "790I": "a46ee17aed9ff230bedebadfced8f6c2b6f73432550318b7f0c9cdd19f40ab6b",
    "790J": "7c1f4a7686043fd8750f2dd5a51123bc274d53a06eecac14856da9c65df02dc9",
    "789A": "cd2885359a74648d51cb1a48944b71f5e3af442edeb40abeeda2b2a969dcda24",
    "789E": "0a657903bf8c48dcc3cafd801115884ed88e16889e81cef97655f6082a1d579f",
    "789F": "87d146b8bf481e3026274c4e64a773492c2bf4ce4635240302ed6cd3c2242a3a",
    "789G": "adf21b0a655ed6a806b56857cbb8b3ab53c2ab6ead2911aa70a99da1cedee219",
    "789H": "433e58a8345d959291d3a3b05cccec8bb692c6798be23c9bb982f7da4e3563ef",
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

def replay(variant, extras, remaining, omit_wait, receipt969=False, watch969=False, map969=False, right969=False, last=LAST):
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
            for gen in range(958, last+1):
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
                    for g in range(907, last+1):
                        if variant in ("782","782B","782C","782D","782E",*ROW_SCHEDULE_ELF):
                            geometry=(options.data/f"frame{g}.geometry").read_bytes()
                            if int.from_bytes(geometry[5732:5734],"little")>24:
                                continue
                        plans=self.plansets[g]
                        assert plans[0][6]==2 and all(q[6]<2 for q in plans[1:])
                        self.plansets[g]=[plans[0]]+[q for q in plans if q[6]==1]+[q for q in plans if q[6]==0]
            link=ObjectFirst
        return original_schedule(args, extended_oracle, link, frames=last-904)
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
    if variant in CONTROL_ELF:
        expected=CONTROL_ELF[variant]
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
        runpy.run_module("test_nes_longrun694" if variant in ("793","797","799","803","804L","806","808","812","812B","812C","814") else "test_nes_status689" if variant in ("763","770","779C","780","781","781B","781C","782","782B","782C","782D","782E",*ROW_SCHEDULE_ELF,*CONTROL_ELF) else "test_nes_static751",run_name="__main__")


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
    p.add_argument("variant", choices=("763","767","769","770","771","776","776B","777","777B","778","778B","779","779B","779C","780","781","781B","781C","782","782B","782C","782D","782E",*ROW_SCHEDULE_ELF,*CONTROL_ELF))
    p.add_argument("extras", type=Path)
    p.add_argument("--boot-pair", action="store_true", help="stop after the first two displayed generations")
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
        replay(a.variant,a.extras,rest,a.omit_wait969,a.receipt969,a.watch969,a.map969,a.right969,906 if a.boot_pair else LAST)
