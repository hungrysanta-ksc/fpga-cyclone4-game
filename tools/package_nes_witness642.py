"""Package the selected image only after real E8 replay, full fit/timing and recovery gates."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile
import zlib
from analyze_nes_export636 import board as board_result
from check_nes_fault641 import ROOT, digest, evidence
from check_nes_fault641_arm import replay
from nes_cf68_pair_preflight import decode, encode
from nes_schedule492 import funcs


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base_arm", "arm", "board", "checks", "sim", "rom", "programmer", "prior", "out"):
        parser.add_argument("--" + name.replace("_", "-"), required=True, type=Path)
    a = parser.parse_args()
    base = evidence("trial639-package.json")
    old, new = [p / "obj-nes-100" for p in (a.base_arm, a.arm)]
    fw = (new / "firmware.stm").read_bytes()
    fw_sha = digest(new / "firmware.stm")
    assert digest(old / "firmware.stm") == base["firmware_SHA256"] and digest(old / "sd2snes.elf") == base["ELF"]
    functions = funcs(new / "sd2snes.elf")
    assert len(functions) == base["identical_functions"] and functions == funcs(old / "sd2snes.elf")
    assert (old / "firmware.stm").read_bytes()[32:].replace(b"639", b"642") == fw[32:]
    size, crc, inv = struct.unpack_from("<III", fw, 8)
    assert fw.startswith(b"STM3") and size + 512 == len(fw) <= 212992
    assert zlib.crc32(fw[512:]) == crc and crc ^ inv == 0xffffffff
    image = "sd2snes/fpga_mmc642.bi3"
    marker = "NES MMC3 642.nh1"
    logs = [s.replace("639", "642") for s in base["logs"]]
    rom_name = base["required_ROM"]["path"].replace("639", "642")
    for name in [marker, *("/" + s for s in [image, rom_name, *logs])]:
        assert name.encode() + b"\0" in fw

    board = board_result(a.board)
    assert all(n >= 0 for n in board["minimum_slack_ns"].values())
    assert all(n > 0 for n in board["ROM_pin_min_setup_ns"].values())
    assert board["M9K"] == 56
    for p in (a.sim / "reference").rglob("*"):
        if p.is_file():
            assert digest(p) == digest(a.board / p.relative_to(a.sim / "reference"))
    fault_log = (a.sim / "fault641_tb.log").read_text(errors="replace")
    boot_log = (a.sim / "boot641_tb.log").read_text(errors="replace")
    assert "PASS642 FINISH" in fault_log and "PASS641 SPI73" in boot_log
    masks = [(8, 0), (0, 1), (64, 0), (0, 128), (3, 0), (0, 128)]
    replies = []
    for i, mask in enumerate(masks, start=1):
        raw = bytes.fromhex(re.search(rf"E8 case={i} reply=([0-9a-f]{{40}})", fault_log)[1])
        assert raw[14:16] == bytes(mask)
        replay(a.arm, evidence("hardware640-mmc639.json")["runs"][0]["fields"], raw)
        replies.append(raw.hex())
    assert re.findall(r"stage=0 accumulated=\w+ order=(\w+)", boot_log) == ["00", "15", "0f"]
    menu, windows = (read(a.checks / n) for n in ("menu.json", "windows.json"))
    assert menu["firmware"] == windows["firmware_SHA256"] == fw_sha and menu["marker_cases"] == 4
    assert [(v["start_s"], v["end_s"]) for v in windows["accepted"]] == [(5, 40), (40, 55)]
    recover = {}
    for fault in ("none", "program", "done", "busy", "token"):
        r = read(a.checks / ("base-" + fault) / "result.json")
        assert r["passed"] and r["firmware_sha256"] == fw_sha
        assert r["config_paths"] == ["/" + image, "/sd2snes/fpga_base.bi3"]
        assert r["safe_return"] == r["base_restored"] == int(fault == "none")
        recover[fault] = r["safe_return"]
    client = read(a.rom / "result.json")
    assert client["bytes"] == 5120 and client["client"] == base["ROM_read"]["client"]
    assert client["program"] == digest(a.board / "sink-program.hex") == base["ROM_read"]["program"]
    assert client["bus"] == base["ROM_read"]["bus"] and client["log"] == digest(a.rom / "vsim.log")
    programmer = read(a.programmer / "result.json")
    raw = (a.board / "board.rbf").read_bytes()
    bi3 = (a.board / Path(image).name).read_bytes()
    assert programmer["passed"] and programmer["image_sha256"] == hashlib.sha256(bi3).hexdigest()
    assert programmer["rbf_sha256"] == hashlib.sha256(raw).hexdigest() and encode(raw) == bi3 and decode(bi3) == raw
    assert "was successful" in (a.board / "cpf642.log").read_text()
    prefix = "01-MMC642-SD-ROOT/"
    files = {prefix + marker: b"", prefix + image: bi3, prefix + "sd2snes/firmware.stm": fw,
             "README-KO.txt": (ROOT / "docs/nes-mmc642-trial.ko.md").read_bytes(),
             prefix + "sd2snes/nes/ROM-NOT-INCLUDED.txt": b"Copy your own mmc639.nes to mmc642.nes. CRC32 5a04eed7.\n"}
    assert digest(a.prior) == base["ZIP_SHA256"]
    with zipfile.ZipFile(a.prior) as archive:
        for name in ("sd2snes/fpga_base.bi3", "sd2snes/m3nu.bin"):
            key = "01-MMC639-SD-ROOT/" + name
            data = archive.read(key)
            assert hashlib.sha256(data).hexdigest() == base["files"][key]
            files[prefix + name] = data
    result = dict(candidate="MMC642", baseline="MMC639", physical_verified=False, board=board,
                  firmware_SHA256=fw_sha, ELF=digest(new / "sd2snes.elf"), identical_functions=len(functions),
                  Flash_B=len(fw), Flash_free_B=212992-len(fw), recovery= recover, programmer=programmer,
                  E8_replies=replies, boot_stage0_order=["00","15","0f"], ROM_read=client,
                  log_SHA256={f:digest(a.sim / f) for f in ("vlog.log","fault641_tb.log","boot641_tb.log")},
                  required_ROM={**base["required_ROM"], "path":rom_name}, logs=logs, RESTORE_included=False,
                  files={k:hashlib.sha256(v).hexdigest() for k,v in files.items()})
    files["manifest.json"] = (json.dumps(result, indent=2) + "\n").encode()
    a.out.mkdir(exist_ok=False, parents=True)
    path = a.out / "MMC642-TRIAL.zip"
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None and sorted(archive.namelist()) == sorted(files)
        assert all(archive.read(k) == v for k, v in files.items())
    result.update(ZIP_SHA256=digest(path), ZIP_bytes=path.stat().st_size)
    (a.out / "result.json").write_text(json.dumps(result, indent=2) + "\n", newline="\n")


if __name__ == "__main__":
    main()
