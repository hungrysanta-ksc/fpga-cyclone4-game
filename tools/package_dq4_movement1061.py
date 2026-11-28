"""Bind the movement firmware to its verified DQ4 board and inherit the release payload."""
import csv
import json
import struct
import zipfile
import zlib
from package_cart_state1059 import sha
from package_nes_kirby1027 import programmer, timing
from prepare_dq4_movement1061 import BASE, OUT, ROOT


def package():
    fit = OUT/"fit"
    routed = timing(fit)
    with (fit/"sram.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    corners = {r["corner"] for r in rows}
    assert len(corners) == 3
    for corner in corners:
        assert {(r["group"], r["check"]) for r in rows if r["corner"] == corner} == {
            (g,k) for g in ("input","output") for k in ("setup","hold")}
    packed, proof = programmer(fit, OUT, 1061)
    source = json.loads((ROOT/"analysis/nes-carts1060.json").read_text())["archives"]
    evidence = dict(board=routed, rbf=proof["rbf_sha256"], archives={})
    for n in ("movement", "battle-chr"):
        evidence[n] = json.loads((OUT/(n+".json")).read_text())
    for suffix, marker in (("trace","PASS1052"),("battle-128","COPIED 640"),("battle-512","COPIED 1536")):
        log = (OUT/(suffix+".log")).read_text(errors="replace")
        assert marker in log and "# Errors: 0" in log
        if suffix.startswith("battle"): assert "PASS_PAGE1058" in log
    for edition, archive in source.items():
        prev = BASE/archive["zip"]
        assert sha(prev.read_bytes()) == archive["sha256"]
        with zipfile.ZipFile(prev) as z:
            files = {n:z.read("sd2snes/"+n) for n in archive["files"]}
        assert {n:sha(v) for n,v in files.items()} == archive["files"]
        if edition == "debug":
            fw = (OUT/"debug/link/src/obj-nes-100/firmware.stm").read_bytes()
            size, crc, inv = struct.unpack_from("<III",fw,8)
            assert fw[:4] == b"STM3" and size+512 == len(fw) <= 212992
            assert zlib.crc32(fw[512:]) == crc == inv^0xffffffff
            assert all(f"nes-{n}-debug1061".encode() in fw for n in ("progress","game-last","frame","stop"))
            files.update({"firmware.stm":fw, "nes-m5.bi3":packed})
        manifest = dict(edition=1061, profile=edition, files={n:sha(v) for n,v in files.items()})
        dest = OUT/f"NES-1061-{edition.upper()}-SD-ROOT.zip"
        tmp = dest.with_suffix(".tmp")
        with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED) as z:
            for n,v in files.items(): z.writestr("sd2snes/"+n,v)
            z.writestr("manifest.json",json.dumps(manifest,indent=2))
            z.write(ROOT/"docs/nes-dq4-movement1061.ko.md","README-KO.txt")
        with zipfile.ZipFile(tmp) as z:
            assert z.testzip() is None
            assert {n:sha(z.read("sd2snes/"+n)) for n in files} == manifest["files"]
        tmp.replace(dest)
        evidence["archives"][edition] = dict(zip=dest.name, sha256=sha(dest.read_bytes()),
                                             firmware_bytes=len(files["firmware.stm"]), **manifest)
    (ROOT/"analysis/nes-dq4-movement1061.json").write_text(json.dumps(evidence,indent=2)+"\n")


if __name__ == "__main__":
    package()
