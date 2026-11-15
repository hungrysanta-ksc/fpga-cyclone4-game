"""Build the two NES SD overlays from the tested ARM links and pinned NES and GBC assets."""
import argparse
import json
import struct
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from check_nes_shared794 import PROBES, check, check_cartridge_dispatch
from package_nes_trial704 import digest, read, save, sha
from replay_nes_output768 import ROW_SCHEDULE_ELF

ROOT = Path(__file__).resolve().parents[1]
WORK = PROBES / "nes-reset796"
GBC = {"sd2snes/gbc_snes.bin": "730564d2b2efe60d73ff3aa2bd55b0639fd951480227023303909c8bf448af1c",
       "sd2snes/fpga_egbc.bi3": "cd98e5b6a0db18d931dcc9ba72f1d39f513842f5eb3405dc8539a3bb8542a69c"}


def verify(n, payload, renderer, temp, client_sha):
    src = WORK / f"final{n}/src"
    size, crc, inv = struct.unpack_from("<III", payload, 8)
    assert payload[:4] == b"STM3" and size+512 == len(payload) <= 212992
    assert crc == zlib.crc32(payload[512:]) and crc ^ inv == 0xffffffff
    markers = [f"NES MMC3 {n}.nh1", f"/sd2snes/fpga_mmc{n}.bi3", f"/sd2snes/nes/mmc{n}.nes"]
    markers.extend(f"/sd2snes/nes-{name}-mmc{n}.txt" for name in ("progress", "budget", "game-last"))
    assert all(s.encode()+b"\0" in payload for s in markers)
    fw = digest(payload)
    elf = sha(src / "obj-nes-100/sd2snes.elf")
    assert elf == ROW_SCHEDULE_ELF[str(n)]
    reset = read(WORK/"handoff.json")[str(n)]
    assert reset["firmware"] == fw and len(reset["cases"]) == 11
    suite = WORK / f"check{n}"
    menu = read(suite/"menu.json")
    assert menu["firmware"] == fw and menu["marker_cases"] == 4
    for fault in ("none","program","done","busy","token"):
        base = read(suite/f"base-{fault}/result.json")
        assert base["firmware_sha256"] == fw and base["passed"]
        assert base["base_restored"] == base["safe_return"] == int(fault=="none")
    mode = read(suite/"mode.json")
    if n == 796:
        assert mode["firmware_SHA256"] == fw and mode["unfinished_excluded"]
        assert [(w["start_s"],w["end_s"]) for w in mode["accepted"]] == [(5,40),(40,55)]
    else:
        assert mode["passed"] and mode["firmware"] == fw
    guard = read(WORK/f"guards{n}.json")
    assert guard["firmware"] == fw and len(guard["retire"]) == 9 and guard["ACK"]["corrupt_bits"] == 152
    phases = []
    for phase in (1,2):
        folder = temp/f"nes-reset796b-{n}-p{phase}"
        joint = read(folder/"joint.json")
        assert joint["passed"] and joint["commits"] == 2 and joint["last_status"] == 1
        assert joint["firmware_SHA256"] == fw and joint["client_SHA256"] == client_sha
        frames = joint["frames"]
        assert [row["generation"] for row in frames] == [905,906]
        assert frames[0]["release_masterclock"] == (7288416,7467100)[phase-1]
        phases.append(dict(frames=frames, pixels=[sha(folder/f"frame-{g}.rgb") for g in (905,906)]))
    good, bad = (check(src, renderer, corrupt) for corrupt in (False,True))
    assert good["accepted"] and not bad["accepted"] and good["firmware"] == bad["firmware"] == fw
    return dict(firmware=fw, ELF=elf, Flash_B=len(payload), free_B=212992-len(payload), phases=phases,
                reset_STOP=reset["cases"], dispatch=check_cartridge_dispatch(src),
                eGBC=dict(original=good, damaged=bad), guard_digest=sha(WORK/f"guards{n}.json"),
                checks={q.relative_to(suite).as_posix():sha(q) for q in sorted(suite.rglob("*.json"))})


def package(temp):
    previous = PROBES / "nes-trial792/final/MMC792-60SEC-MMC793-LONG.zip"
    prior = read(ROOT/"analysis/trial792-package.json")
    assert sha(previous) == prior["ZIP_SHA256"]
    with ZipFile(PROBES/"gbc-rgb774/GBC774-RGB555-SD-ROOT.zip") as gbc:
        common = {k:gbc.read(k) for k in GBC}
    assert {k:digest(v) for k,v in common.items()} == GBC
    files = {"README-KO.txt":(ROOT/"docs/nes-mmc796-797-trial.ko.md").read_bytes()}
    editions = {}
    with ZipFile(previous) as old:
        for n, prefix in ((796,"01-MMC796-60SEC-SD-ROOT/"),(797,"02-MMC797-LONG-SD-ROOT/")):
            prev = str(n-4)
            payload = (WORK/f"final{n}/src/obj-nes-100/firmware.stm").read_bytes()
            editions[n] = verify(n, payload, common["sd2snes/gbc_snes.bin"], temp, prior["variants"][prev]["ROM"]["client"])
            assets = dict(common)
            for name in ("sd2snes/fpga_base.bi3","sd2snes/m3nu.bin",f"sd2snes/fpga_mmc{n}.bi3"):
                key = (prefix+name).replace(str(n),prev)
                assets[name] = old.read(key)
                assert digest(assets[name]) == prior["files"][key]
            assets["sd2snes/firmware.stm"] = payload
            assets[f"NES MMC3 {n}.nh1"] = b""
            assets["sd2snes/nes/ROM-NOT-INCLUDED.txt"] = f"Copy your SMB3(J) ROM here as mmc{n}.nes.\n".encode()
            files.update({prefix+k:v for k,v in assets.items()})
    manifest = dict(editions=editions, files={k:digest(v) for k,v in files.items()}, physical=False)
    files["manifest.json"] = (json.dumps(manifest,indent=2)+"\n").encode()
    archive = WORK/"MMC796-60SEC-MMC797-LONG.zip"
    with ZipFile(archive,"x",ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name,data)
    with ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist()) == set(files) and all(z.read(k)==v for k,v in files.items())
    save(ROOT/"analysis/reset796-package.json",dict(**manifest, ZIP_SHA256=sha(archive), ZIP_bytes=archive.stat().st_size))
    print(archive, sha(archive))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp",type=Path)
    package(parser.parse_args().temp)
