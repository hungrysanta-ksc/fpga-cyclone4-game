"""Preserve 1056's other board files and verify the two closed replacements."""
import csv
import json
import re
import struct
import zipfile
import zlib
from package_nes_carts1056 import digest
from package_nes_kirby1027 import timing,programmer
from prepare_cart_stage1057 import BASE,OUT
from prepare_nes_carts1056 import ROOT


def package():
    run=(OUT/"stage-vsim.log").read_text()
    replay=re.search(r"PASS_WAIWAI_STAGE PPU reads=(\d+) PSRAM grants=(\d+)",run)
    battle=re.search(r"PASS_BATTLE_STAGE PPU reads=(\d+)",run)
    assert replay and battle and "PASS1057 " in run
    proof=json.loads((OUT/"guards.json").read_text())
    handoff=json.loads((OUT/"handoff.json").read_text())
    assert len(handoff)==6 and all(r["commands"]==[96,98,99,100] and r["menu_released"] for r in handoff.values())
    assert proof["battery_roundtrip_bytes"]==8192
    old=json.loads((ROOT/"analysis/nes-carts1056.json").read_text())["archives"]
    images={}
    boards={}
    for m,folder in [(7,"final-7"),(21,"closed-21")]:
        route=OUT/folder
        report=timing(route)
        if m==7:
            with (route/"sram.tsv").open() as f:pins=list(csv.DictReader(f,delimiter="\t"))
            corners={p["corner"] for p in pins}
            assert len(corners)==3 and all({(p["group"],p["check"]) for p in pins if p["corner"]==c}==
                {("input","setup"),("input","hold"),("output","setup"),("output","hold")} for c in corners)
            report["sram_pin_paths"]=len(pins)
        images[f"nes-m{m}.bi3"],program=programmer(route,route,1057)
        boards[m]=dict(report,rbf_sha256=program["rbf_sha256"])
    archives={}
    for profile,prior in old.items():
        base=BASE/prior["zip"]
        assert digest(base.read_bytes())==prior["sha256"]
        firmware=(OUT/profile/"link/src/obj-nes-100/firmware.stm").read_bytes()
        assert proof[profile]==dict(checked=20,sha256=digest(firmware))
        size,crc,inv=struct.unpack_from("<III",firmware,8)
        assert firmware[:4]==b'STM3' and size+512==len(firmware)<=212992 and crc==zlib.crc32(firmware[512:])==inv^0xffffffff
        for stem in ["progress","game-last","frame","stop"]:
            assert (f"nes-{stem}-debug1057".encode() in firmware)==(profile=="debug")
        assert b'debug1056' not in firmware
        with zipfile.ZipFile(base) as archive:
            contents={n:archive.read("sd2snes/"+n) for n in prior["files"]}
        assert {n:digest(d) for n,d in contents.items()}==prior["files"]
        contents.update(images)
        contents["firmware.stm"]=firmware
        hashes={n:digest(d) for n,d in contents.items()}
        manifest=dict(edition=1057,profile=profile,files=hashes,firmware_bytes=len(firmware))
        target=OUT/f"NES-1057-{profile.upper()}-SD-ROOT.zip"
        temp=target.with_suffix(".tmp")
        with zipfile.ZipFile(temp,"w",zipfile.ZIP_DEFLATED) as z:
            for n,d in contents.items():z.writestr("sd2snes/"+n,d)
            z.writestr("manifest.json",json.dumps(manifest,indent=2))
            z.write(ROOT/"docs/nes-carts1057.ko.md","README-KO.txt")
        with zipfile.ZipFile(temp) as z:
            assert z.testzip() is None and all(digest(z.read("sd2snes/"+n))==h for n,h in hashes.items())
        temp.replace(target)
        archives[profile]=dict(manifest,zip=target.name,sha256=digest(target.read_bytes()))
    result=dict(boards=boards,archives=archives,guards=proof,menu=handoff,physical_1057=False,
                stage_chr_reads=int(replay[1]),stage_psram_grants=int(replay[2]),battle_chr_reads=int(battle[1]))
    (ROOT/"analysis/nes-carts1057.json").write_text(json.dumps(result,indent=2)+"\n")

if __name__=="__main__":package()
