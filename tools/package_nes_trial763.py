"""Package the four checked PR158 installations with a pinned 707D RTL baseline."""
import argparse
import json
import struct
import zipfile
import zlib
from pathlib import Path

from analyze_nes_static751 import phase
from analyze_nes_status689 import cost
from package_nes_trial704 import decode, digest, funcs, read, save, sha
from prepare_nes_trial763 import PROBES, ROOT, VARIANTS


def compare_schedule(temp, work, src, client, baseline):
    result = {}
    for n in (1, 2):
        folder = work / f"timed{n}"
        trace = read(folder / "joint.json")
        assert trace["passed"] and trace["commits"] == 53 and trace["last_status"] == 1
        firmware = sha(src / "obj-nes-100/firmware.stm")
        assert trace["firmware_SHA256"] == firmware and trace["client_SHA256"] == sha(client / "sink165.sfc")
        ref = temp / f"nes-credit753-prefix{n}"
        for pattern in ("map-{}.bin", "expected-{}.bin", "frame-{}.rgb"):
            assert all((folder / pattern.format(g)).read_bytes() == (ref / pattern.format(g)).read_bytes()
                       for g in range(905, 958))
        v = phase(temp, "sharedfast", n, client=client, folder=folder, firmware=firmware)
        assert v["guarded_schedule"] and v["order"] and all(v["long_map"].values())
        assert v["E8_delta_clocks"] <= 0 and v["OBJ"]["line"] <= 257
        result[n] = {k: v[k] for k in ("intervals", "long_map", "line951", "final_wait957", "OBJ", "E8_delta_us", "ACK", "dense_ms")}
        result[n]["delta_753_ACK_clocks"] = v["ACK"] - baseline["variants"]["prefix"][str(n)]["timing"]["ACK"]
        result[n]["joint_SHA256"] = sha(folder / "joint.json")
    return result


def run(work, archive, report):
    prior = read(ROOT / "analysis/trial704-package.json")
    board_proof = read(ROOT / "analysis/bg707-verification.json")
    speed = read(ROOT / "analysis/credit753-verification.json")
    base_zip = PROBES / "nes-trial704/trial01/MMC704-60SEC-MMC705-LONG.zip"
    assert sha(base_zip) == prior["ZIP_SHA256"]
    common = {}
    with zipfile.ZipFile(base_zip) as z:
        for name in ("sd2snes/fpga_base.bi3", "sd2snes/m3nu.bin"):
            old = "01-MMC704-60SEC-SD-ROOT/" + name
            common[name] = z.read(old)
            assert digest(common[name]) == prior["files"][old]
    receipt = {}
    files = {}
    capture = read(work / "empty2/result.json")
    assert len(set(capture["cases"])) == 24
    pins = {**board_proof["inputs"]["base"], **board_proof["inputs"]["changed"]}
    for index, (number, (source, old, client_path)) in enumerate(VARIANTS.items(), 1):
        candidate = number >= 765
        timed = number % 2 == 1
        root = PROBES / "nes-trial763"
        src = root / ("timed765" if number == 765 else f"linked{number}") / "src"
        obj = src / "obj-nes-100"
        old_obj = PROBES / source / "src/obj-nes-100"
        old_hash = speed["variants"]["prefix"]["1"]["firmware"] if candidate else prior["variants"][old]["firmware"]
        assert sha(old_obj / "firmware.stm") == old_hash
        fw = (obj / "firmware.stm").read_bytes()
        size, crc, inverse = struct.unpack_from("<III", fw, 8)
        assert fw[:4] == b"STM3" and size + 512 == len(fw) <= 212992
        assert zlib.crc32(fw[512:]) == crc and crc ^ inverse == 0xffffffff
        if number != 765:
            assert funcs(obj / "sd2snes.elf") == funcs(old_obj / "sd2snes.elf")
            assert fw[32:] == (old_obj / "firmware.stm").read_bytes()[32:].replace(old.encode(), str(number).encode())
        client = PROBES / client_path
        client_hash = sha(client / "sink165.sfc")
        wanted = speed["ROM_SHA256"] if candidate else prior["variants"][old]["ROM_read"]["client"]
        assert client_hash == wanted
        board_num = min(number, 765)
        board = work.parent / "nes-bg707-board04" if number == 764 else work / f"board{board_num}"
        for name, h in pins.items():
            assert sha(board / name) == (sha(client / name) if name == "sink-program.hex" else h)
        assert all(sha(board / name) == h for name, h in capture["files"].items())
        c = cost(board)
        assert c["SOF"] and c["STA"] and not c["LAB_error"] and c["LAB"] <= 963 and c["M9K"][0] <= 56
        assert c["unconstrained"] == board_proof["boards"]["D"]["unconstrained"] and min(c["slack_ns"].values()) > 0
        for name in ("word660.tsv", "reader661.tsv", "io612.tsv"):
            assert c[name] and all(float(row["slack"]) > 0 for row in c[name])
        bus = read(work / f"rom{board_num}/result.json")
        assert bus["bytes"] == 5120 and bus["program"] == sha(board / "sink-program.hex")
        assert bus["client"] == client_hash and bus["bus"] == sha(board / "nes_sink_bus165.sv")
        image = work / f"packed{board_num}"
        im = read(image / "image.json")
        bi = (image / f"fpga_mmc{board_num}.bi3").read_bytes()
        assert im["SOF"] == sha(board / "output_files/board.sof") and digest(bi) == im["BI3"]
        assert digest(decode(bi)) == im["RBF"] and im["programmer"]["passed"]
        check = work / ("selected765" if number == 765 else f"checks{number}")
        menu = read(check / "menu.json")
        assert menu["firmware"] == digest(fw) and menu["marker_cases"] == 4
        assert all(v["prepared"] == v["released"] == int(k == "normal") for k,v in menu["rows"].items())
        mark = f"NES MMC3 {number}.nh1"
        cfg = f"sd2snes/fpga_mmc{number}.bi3"
        game = f"sd2snes/nes/mmc{number}.nes"
        logs = [f"sd2snes/nes-{s}-mmc{number}.txt" for s in ("progress", "budget", "game-last")]
        for label in [mark, *("/" + n for n in [cfg, game, *logs])]:
            assert label.encode() + b"\0" in fw and label.replace(str(number), old).encode() + b"\0" not in fw
        for fault in ("none", "program", "done", "busy", "token"):
            r = read(check / f"base-{fault}/result.json")
            assert r["firmware_sha256"] == digest(fw) and r["passed"]
            assert r["safe_return"] == r["base_restored"] == int(fault == "none")
            assert r["config_paths"] == ["/" + cfg, "/sd2snes/fpga_base.bi3"]
        mode = read(check / "mode.json")
        if timed:
            assert mode["firmware_SHA256"] == digest(fw) and mode["unfinished_excluded"]
            assert [(r["start_s"], r["end_s"]) for r in mode["accepted"]] == [(5,40),(40,55)]
        else:
            assert mode["firmware"] == digest(fw) and mode["passed"] and mode["first_windows"] == [2,2]
        if candidate:
            checks = read(check / "credit.json")
            assert checks["firmware"] == digest(fw) and checks["seal_receipts"]["corrupt_bits"] == 152
            assert len(checks["receipt"]) == 9 and len(checks["deadline"]) == 17
        if number == 765:
            timer = read(check / "timer.json")
            assert timer["firmware"] == digest(fw) and len(timer["cases"]) == 8
        prefix = f"{index:02}-MMC{number}-{'B' if candidate else 'A'}-{'60SEC' if timed else 'LONG'}-SD-ROOT/"
        for n, data in {mark:b"", cfg:bi, "sd2snes/firmware.stm":fw, **common}.items():
            files[prefix+n] = data
        files[prefix+"sd2snes/nes/ROM-NOT-INCLUDED.txt"] = f"Copy the unchanged ROM used for MMC704/705 to {game}.\n".encode()
        receipt[number] = dict(board="707D", source=source, client=client_path, firmware=digest(fw), ELF=sha(obj/"sd2snes.elf"),
                               Flash_B=len(fw), Flash_free_B=212992-len(fw), BSS_B=int((src.parent/"size.log").read_text().splitlines()[-1].split()[2]),
                               ROM_SHA256=client_hash, ROM_bus=bus, BI3=im["BI3"], RBF=im["RBF"], board_reports=c["reports"],
                               LE=c["LE"], LAB=c["LAB"], M9K=c["M9K"], slack_ns=c["slack_ns"], logs=logs,
                               guards={str(p.relative_to(check)):sha(p) for p in check.rglob("*.json")})
        if number == 765:
            receipt[number]["two_phases"] = compare_schedule(work.parent,work,src,client,speed)
    files["README-KO.txt"] = (ROOT/"docs/nes-mmc763-766-trial.ko.md").read_bytes()
    result = dict(variants=receipt, empty_capture=capture, files={n:digest(b) for n,b in files.items()}, physical=False)
    files["manifest.json"] = (json.dumps(result,indent=2) + "\n").encode()
    assert not any("restore" in n.lower() or n.lower().endswith((".nes",".sav",".srm",".rtc")) for n in files)
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,"x",zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():
            z.writestr(n,data)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist()) == set(files)
        assert all(z.read(n)==data for n,data in files.items())
    result.update(ZIP_bytes=archive.stat().st_size, ZIP_SHA256=sha(archive))
    save(report,result)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("work","archive","report"):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    run(a.work,a.archive,a.report)
