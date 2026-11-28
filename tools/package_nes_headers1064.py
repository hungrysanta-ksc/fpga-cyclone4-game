"""Package the linked MMC1 firmware and the tested Quartus board with the 1062 board set."""
import csv
import json
import re
import struct
import zipfile
import zlib
from package_cart_state1059 import sha
from package_nes_kirby1027 import programmer, timing
from prepare_nes_headers1064 import ROOT, OUT, BASE


def checked_sim(log, expected):
    text = log.read_text(errors="replace")
    assert re.search(r"^# Errors: 0,", text, re.M) and expected in text, log
    return text


def package():
    previous = json.loads((ROOT/"analysis/nes-compat1062.json").read_text())["archives"]
    verified = json.loads((ROOT/"analysis/nes-headers1064.json").read_text())
    route = OUT/"fit-2"
    report = dict(timing=timing(route), cpu_mapper_writes={}, archives={})
    with (route/"sram.tsv").open() as fp:
        rows = list(csv.DictReader(fp, delimiter="\t"))
    corners = {row["corner"] for row in rows}
    assert len(corners) == 3
    for corner in corners:
        assert {(r["group"], r["check"]) for r in rows if r["corner"] == corner} == {
            ("input","setup"), ("input","hold"), ("output","setup"), ("output","hold")}
    checked_sim(OUT/"loader.log", "PASS FF3 loader 262144 accepted bytes, START and retained STOP length")
    for n in (1, 2):
        log = checked_sim(OUT/f"zelda{n}/resume-1-vsim.log", "PASS cartridge CPU resume 64 fetches and 2658 words")
        writes = int(re.search(r"^# MMC1 WRITES (\d+)", log, re.M)[1])
        assert writes >= 12
        report["cpu_mapper_writes"][str(n)] = writes
        assert verified["release_fatfs_launches"][f"zelda_{n}"]["menu_released"]
    board, proof = programmer(route, route, 1064)
    report["rbf_sha256"] = proof["rbf_sha256"]
    for mode, source in previous.items():
        old = BASE/source["zip"]
        assert sha(old.read_bytes()) == source["sha256"]
        with zipfile.ZipFile(old) as z:
            files = {n:z.read("sd2snes/"+n) for n in source["files"]}
        assert {n:sha(v) for n,v in files.items()} == source["files"]
        fw = (OUT/mode/"link/src/obj-nes-100/firmware.stm").read_bytes()
        assert sha(fw) == verified["firmware_sha256"][mode]
        length, crc, inv = struct.unpack_from("<III", fw, 8)
        assert fw[:4] == b"STM3" and length+512 == len(fw) <= 212992
        assert zlib.crc32(fw[512:]) == crc == inv^0xffffffff
        for kind in ("progress", "game-last", "frame", "stop"):
            assert (f"nes-{kind}-debug1064".encode() in fw) == (mode == "debug")
        assert b"/sd2snes/nes-m1.bi3" in fw
        files.update({"nes-m1.bi3":board, "firmware.stm":fw})
        manifest = dict(edition=1064, profile=mode, files={n:sha(v) for n,v in files.items()})
        target = OUT/f"NES-1064-{mode.upper()}-SD-ROOT.zip"
        tmp = target.with_suffix(".tmp")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for n,v in files.items():
                z.writestr("sd2snes/"+n, v)
            z.write(ROOT/"docs/nes-mmc1-1064.ko.md", "README-KO.txt")
            z.writestr("manifest.json", json.dumps(manifest, indent=2))
        with zipfile.ZipFile(tmp) as z:
            assert z.testzip() is None
            assert {n:sha(z.read("sd2snes/"+n)) for n in files} == manifest["files"]
        tmp.replace(target)
        report["archives"][mode] = dict(zip=target.name, sha256=sha(target.read_bytes()), **manifest)
    (ROOT/"analysis/nes-mmc1-board1064.json").write_bytes((json.dumps(report, indent=2)+"\n").encode())


if __name__ == "__main__":
    package()
