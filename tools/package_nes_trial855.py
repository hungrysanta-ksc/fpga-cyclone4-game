"""Qualify the renamed release link against 854E and verify the SD archive."""
import argparse
import json
import re
import struct
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from analyze_nes_output822 import resources
from analyze_nes_output852 import measure
from check_nes_opening818 import admission
from package_nes_trial704 import digest, read, save, sha
from prepare_nes_trial855 import ARM, CLIENT, PROBES, ROOT, WORK

SRC = WORK / "link/src"
FW = SRC / "obj-nes-100/firmware.stm"


def reset_policy():
    from check_nes_game478 import ELFFile, Machine
    from check_nes_hardware494_termination import member_offset

    with (SRC / "obj-nes-100/sd2snes.elf").open("rb") as stream:
        offsets = {member_offset(m) for cu in ELFFile(stream).get_dwarf_info().iter_CUs()
                   for d in cu.iter_DIEs() if d.tag == "DW_TAG_structure_type"
                   and "DW_AT_name" in d.attributes
                   and d.attributes["DW_AT_name"].value == b"nes_native_sink165"
                   for m in d.iter_children() if m.tag == "DW_TAG_member"
                   and m.attributes["DW_AT_name"].value == b"disable_column"}
    offset, = offsets
    cpu = Machine(SRC, bytes(128))
    sink = 0x20012000
    cpu.u.mem_write(sink + offset, bytes([255]))
    cpu.call("nes_sink165_reset", [sink, 0, 0])
    assert bytes(cpu.u.mem_read(sink + offset, 1)) == bytes(1)
    return dict(disable_before=255, disable_after=0, offset=offset)


def loader(game):
    parent = read(ROOT / "analysis/trial826-package.json")
    raw = game.read_bytes()
    assert digest(raw) == parent["rom"]
    rows = {}
    for name, data, error in (("original", raw, 0),
                              ("damaged", raw[:-1] + bytes([raw[-1] ^ 1]), 4)):
        result = admission(SRC, data, 855)
        assert result == dict(program=error == 0, read_B=len(data), error=error)
        rows[name] = result
    save(WORK / "loader.json", dict(firmware=sha(FW), rom=digest(raw), cases=rows))


def board_proof(temp, parent):
    board = temp / "nes-trial816-board855"
    fit = resources(temp, "855")
    assert "Fitter Status : Successful" in (board / "output_files/board.fit.summary").read_text()
    assert all(v >= 0 for v in fit["min_slack_ns"].values())
    mif, = (board / "db").glob("board.ram*_nes_sink_bus165_*.hdl.mif")
    rows = sorted((int(a), int(b, 2)) for a, b in re.findall(
        r"^\s*(\d+)\s*:\s*([01]{8});", mif.read_text(), re.M))
    assert [i for i, _ in rows] == list(range(5120))
    client = bytes.fromhex((CLIENT / "sink-program.hex").read_text())
    assert bytes(v for _, v in rows) == client
    packed = temp / "nes-trial855-packed"
    image = read(packed / "image.json")
    bi = (packed / "fpga_mmc855.bi3").read_bytes()
    assert image["number"] == "855" and image["SOF"] == sha(board / "output_files/board.sof")
    assert image["BI3"] == digest(bi) == image["programmer"]["image_sha256"]
    assert image["RBF"] == sha(packed / "board.rbf") == image["programmer"]["rbf_sha256"]
    assert image["programmer"]["passed"]
    target_slacks = {}
    for name in ("io612", "paths612", "paths801", "phase801", "reader661", "word660"):
        lines = (board / f"{name}.tsv").read_text().splitlines()
        index = 3 if name == "phase801" else 2
        values = [float(line.split("\t")[index]) for line in (lines if name == "phase801" else lines[1:])]
        assert min(values) >= 0
        target_slacks[name] = dict(paths=len(values), worst_ns=min(values))
    def unconstrained(path):
        text = path.read_text(errors="replace")
        return {name: [int(setup), int(hold)] for name, setup, hold in re.findall(
            r"^; (Unconstrained [\w ]+?)\s*;\s*(\d+)\s*;\s*(\d+)\s*;", text, re.M)}
    sta = board / "output_files/board.sta.rpt"
    io = unconstrained(sta)
    assert io and io == unconstrained(temp / "nes-trial816-board822held/output_files/board.sta.rpt")
    return dict(fit=fit, prior_fit=parent["fit"], constrained_paths=target_slacks, unconstrained=io,
                image=image, ROM_bus=digest(client),
                STA_report=sha(board / "output_files/board.sta.rpt")), bi


def guards(temp):
    from analyze_nes_column853 import verify_partial_stop
    from guard_nes_output852 import run

    trial = temp / "nes-tile821-demo-jointmirror-p1-855-on"
    results = {case: run(temp, trial, case, column_client=CLIENT)
               for case in ("damage", "stop", "late-stop")}
    results["partial"] = verify_partial_stop(trial)
    results["restart"] = run(temp, trial, "restart", trial / "guard-stop/canceled.bin", CLIENT)
    save(WORK / "guards.json", results)


def qualification(temp, proof):
    result = {}
    for clip in ("opening", "transition", "demo"):
        for phase in (1, 2):
            metrics, _, _ = measure(temp, clip, phase, "on", "855", column=True)
            old = proof[clip][str(phase)]["runs"]["on"]
            assert metrics["arm"] == sha(FW) and metrics["client"] == sha(CLIENT / "sink165.sfc")
            keys = ("client", "verified_pictures", "held_blank_VBlanks", "measured_intervals",
                    "display_VBlanks", "final_ACK", "final_EA", "gaps", "map")
            assert all(metrics[k] == old[k] for k in keys), (clip, phase)
            result[f"{clip}-{phase}"] = {k: metrics[k] for k in keys if k != "client"}
    return result


def package(temp):
    parent = read(ROOT / "analysis/trial826-package.json")
    proof = read(ROOT / "analysis/column854-results.json")
    fw = FW.read_bytes()
    old = (ARM / "obj-nes-100/firmware.stm").read_bytes()
    assert digest(old) == proof["demo"]["1"]["runs"]["on"]["arm"]
    assert fw[32:] == old[32:].replace(b"826", b"855")
    size, crc, inverse = struct.unpack_from("<III", fw, 8)
    assert fw[:4] == b"STM3" and len(fw) == size + 512 <= 212992
    assert zlib.crc32(fw[512:]) == crc and crc ^ inverse == 0xffffffff
    for name in ("fpga_mmc855.bi3", "mmc855.nes", "NES MMC3 855.nh1", "nes-budget-mmc855.txt",
                 "nes-game-last-mmc855.txt", "nes-progress-mmc855.txt"):
        assert name.encode() + bytes(1) in fw
    board, bi = board_proof(temp, parent)
    board["default_column_policy"] = reset_policy()
    checks = {k: read(WORK / f"{k}.json") for k in ("loader", "menu", "timer", "windows", "guards")}
    guards = checks["guards"]
    assert guards["damage"]["status"] == 224 and guards["stop"]["status"] == guards["late-stop"]["status"] == 228
    assert guards["partial"]["active_bank_preserved"] and guards["restart"] == {"commits": 2, "status": 1}
    base = read(WORK / "base/result.json")
    assert all(checks[k]["firmware"] == digest(fw) for k in ("loader", "menu", "timer"))
    assert checks["menu"]["rows"]["normal"]["released"] and checks["timer"]["passed"]
    assert checks["windows"]["firmware_SHA256"] == base["firmware_sha256"] == digest(fw)
    assert checks["windows"]["layout"] == "demo" and checks["windows"]["unfinished_excluded"]
    assert base["passed"] and base["base_restored"] and base["safe_return"]
    boot = read(temp / "nes-trial855-boot/result.json")
    cases = [c for c in boot["cases"] if c["ROM"] == sha(CLIENT / "sink165.sfc")]
    assert sorted((c["fault"], c["kind"]) for c in cases) == [(False, "restored"), (True, "rejected")]
    runs = qualification(temp, proof)
    archive = PROBES / "nes-trial826/MMC826-ADVENTURE-60SEC-SD-ROOT.zip"
    assert sha(archive) == parent["ZIP_SHA256"]
    files = {}
    with ZipFile(archive) as src:
        for name, checksum in parent["files"].items():
            data = src.read(name)
            assert digest(data) == checksum
            if name == "README-KO.txt":
                data = (ROOT / "docs/nes-mmc855-trial.ko.md").read_bytes()
            elif name.endswith("/firmware.stm"):
                data = fw
            elif name.endswith("/fpga_mmc826.bi3"):
                data = bi
            elif name.endswith("/ROM-NOT-INCLUDED.txt"):
                data = data.replace(b"mmc826.nes", b"mmc855.nes")
            files[name.replace("826", "855")] = data
    assert len(files) == 11 and not any("restore" in n.lower() or n.lower().endswith(".nes") for n in files)
    report = dict(edition=855, physical=False, parent_zip=sha(archive), ARM=digest(fw), flash_B=len(fw),
                  client=sha(CLIENT / "sink165.sfc"), board=board, checks=checks,
                  boot=cases, base=base, final_link_runs=runs, files={n: digest(b) for n,b in files.items()})
    files["manifest.json"] = (json.dumps(report, indent=2) + "\n").encode()
    out = WORK / "MMC855-ADVENTURE-60SEC-SD-ROOT.zip"
    tmp = out.with_suffix(".partial")
    with ZipFile(tmp, "w") as z:
        for name, data in files.items():
            z.writestr(ZipInfo(name), data, compress_type=ZIP_DEFLATED)
    with ZipFile(tmp) as z:
        assert z.testzip() is None and z.namelist() == list(files)
        assert all(z.read(n) == b for n,b in files.items())
    tmp.replace(out)
    report.update(ZIP_SHA256=sha(out), ZIP_B=out.stat().st_size)
    save(ROOT / "analysis/trial855-package.json", report)
    print(out, report["ZIP_SHA256"])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("loader").add_argument("game", type=Path)
    sub.add_parser("guards").add_argument("temp", type=Path)
    sub.add_parser("pack").add_argument("temp", type=Path)
    a = p.parse_args()
    if a.action == "loader":
        loader(a.game)
    elif a.action == "guards":
        guards(a.temp)
    else:
        package(a.temp)
