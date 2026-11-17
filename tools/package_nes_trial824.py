"""Qualify and package the timed Adventure Island IV trial from its final link."""
import argparse
import json
import struct
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from analyze_nes_output822 import CLIENT, resources
from analyze_nes_output823 import analyze, qualification
from check_nes_opening818 import admission
from package_nes_opening818 import PROBES, ROOT, digest, read, sha
from prepare_nes_opening818 import ADVENTURE_SHA


def package(temp, game, edition="824"):
    assert edition in ("824","825","826")
    work = PROBES / f"nes-trial{edition}"
    links = PROBES / "nes-output823"
    src = links / f"link-{edition}/src"
    fw = (src / "obj-nes-100/firmware.stm").read_bytes()
    original = (links / "link-wire/src/obj-nes-100/firmware.stm").read_bytes()
    assert digest(original) == read(ROOT / "analysis/output823-results.json")["comparisons"]["wire"]["arm"]
    if edition=="824":
        assert original[32:].replace(b"820", b"824") == fw[32:]
    size, crc, inverse = struct.unpack_from("<III", fw, 8)
    assert fw[:4] == b"STM3" and len(fw) == size + 512 <= 212992
    assert zlib.crc32(fw[512:]) == crc and crc ^ inverse == 0xffffffff
    for name in ("nes-budget-mmc824.txt", "nes-progress-mmc824.txt", "nes-game-last-mmc824.txt",
                 "NES MMC3 824.nh1", "mmc824.nes", "fpga_mmc824.bi3"):
        assert name.replace("824",edition).encode() + b"\0" in fw

    comparison = analyze(temp, links, [edition])
    timing = qualification(comparison, temp, edition)
    assert timing["passed"]
    for phase in (1, 2):
        rows = comparison[edition]["runs"]
        assert rows[f"earlyB-p{phase}"]["interval_vblanks"][1] == 4
        assert rows[f"demoB-p{phase}"]["warm_vblanks"] == 16
    stop = read(temp / "nes-trial824-stop/result.json")
    assert stop == timing["client_guards"]
    boot = read(temp / "nes-trial824-boot/result.json")
    assert boot["passed"] and all(r["ROM"] == CLIENT and r["passed"] and
            r["kind"] == ("rejected" if r["fault"] else "restored") for r in boot["cases"])
    menu, base, timer, windows = [read(work / f) for f in (
        "menu.json", "base/result.json", "timer.json", "windows.json")]
    assert menu["firmware"] == base["firmware_sha256"] == timer["firmware"] == windows["firmware_SHA256"] == digest(fw)
    assert menu["rows"]["normal"]["released"] and base["passed"] and base["safe_return"] and base["base_restored"]
    layout = "demo" if edition=="826" else "trimmed"
    assert timer["passed"] and windows["layout"] == layout and windows["unfinished_excluded"]

    game_bytes = game.read_bytes()
    assert digest(game_bytes) == ADVENTURE_SHA
    loader = {}
    for name, data, error in (("original", game_bytes, 0),
                              ("corrupt", game_bytes[:-1] + bytes([game_bytes[-1] ^ 1]), 4)):
        result = admission(src, data, int(edition))
        assert result == dict(program=error == 0, read_B=len(data), error=error)
        loader[name] = result

    board = temp / "nes-trial816-board822held"
    fit = resources(temp, "822held")
    assert fit == read(ROOT / "analysis/output822-results.json")["board"]["822held"]
    client = (PROBES / "nes-output815/client/sink165.sfc").read_bytes()
    assert digest(client) == CLIENT and bytes.fromhex((board / "sink-program.hex").read_text()) == client[:5056] + client[-64:]
    packed = temp / "nes-trial824-packed"
    image = read(packed / "image.json")
    bi = (packed / "fpga_mmc824.bi3").read_bytes()
    assert image["number"] == "824" and image["SOF"] == sha(board / "output_files/board.sof")
    assert digest(bi) == image["BI3"] == image["programmer"]["image_sha256"] and image["programmer"]["passed"]

    parent = read(ROOT / "analysis/mask820-results.json")
    archive = PROBES / "nes-mask820/MMC820-ADVENTURE-60SEC-SD-ROOT.zip"
    assert sha(archive) == parent["ZIP_SHA256"]
    files = {"README-KO.txt": (ROOT / f"docs/nes-mmc{edition}-trial.ko.md").read_bytes()}
    with ZipFile(archive) as source:
        for name, checksum in parent["files"].items():
            if not name.startswith("MMC820-ADVENTURE-60SEC-SD-ROOT/"):
                continue
            data = source.read(name)
            assert digest(data) == checksum
            if name.endswith("/firmware.stm"):
                data = fw
            elif name.endswith("/fpga_mmc820.bi3"):
                data = bi
            elif name.endswith("/ROM-NOT-INCLUDED.txt"):
                data = data.replace(b"mmc820.nes", f"mmc{edition}.nes".encode())
            files[name.replace("820", edition)] = data
    assert len(files) == 11 and not any("restore" in n.lower() or n.lower().endswith(".nes") for n in files)
    evidence = dict(edition=int(edition), arm=digest(fw), flash_bytes=len(fw), flash_free=212992-len(fw),
                    rom=ADVENTURE_SHA, client=CLIENT, inherited_zip=sha(archive), fit=fit, image=image,
                    final_runs=comparison[edition]["runs"], qualification=timing, boot=boot, loader=loader,
                    menu=menu, base_restored=base["base_restored"], timer=timer, windows=windows, physical=False,
                    files={n:digest(data) for n,data in files.items()})
    if edition=="825":
        from check_nes_demo825 import transition
        credit=read(work/"credit.json")
        assert credit["replay"]["825"]["firmware"]==digest(fw)
        assert credit["replay"]["824"]["firmware"]==read(ROOT/"analysis/trial824-package.json")["arm"]
        evidence.update(transition=transition(temp),credit=credit)
    if edition=="826":
        from check_nes_demo825 import transition
        evidence["transition"] = transition(temp, editions=(820,825,826))
        prior = read(ROOT / "analysis/trial825-package.json")
        for clip, run in evidence["final_runs"].items():
            for metric in ("interval_vblanks","final_clock"):
                assert run[metric] == prior["final_runs"][clip][metric], (clip,metric)
        for phase in (1,2):
            assert evidence["transition"]["results"][f"826-p{phase}"]["acks"] == prior["transition"]["results"][f"825-p{phase}"]["acks"]
    files["manifest.json"] = (json.dumps(evidence, indent=2) + "\n").encode()
    out = work / f"MMC{edition}-ADVENTURE-60SEC-SD-ROOT.zip"
    with ZipFile(out, "x") as z:
        for name, data in files.items():
            z.writestr(ZipInfo(name), data, compress_type=ZIP_DEFLATED)
    with ZipFile(out) as z:
        assert z.testzip() is None and set(z.namelist()) == set(files)
        assert all(z.read(n) == data for n,data in files.items())
    evidence["ZIP_SHA256"] = sha(out)
    (ROOT / f"analysis/trial{edition}-package.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(out, sha(out))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp", type=Path)
    parser.add_argument("game", type=Path)
    parser.add_argument("--edition", choices=("824","825","826"),default="824")
    args = parser.parse_args()
    package(args.temp, args.game,args.edition)
