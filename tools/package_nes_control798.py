"""Verify the physical control pair, SD-only diagnostic endpoints and shared loader before packaging."""
import argparse
import json
import re
import struct
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from check_nes_game478 import Machine
from check_nes_reset796 import replay
from check_nes_shared794 import check, check_cartridge_dispatch
from package_nes_reset796 import GBC, PROBES, ROOT
from package_nes_trial704 import digest, read, save, sha
from replay_nes_output768 import CONTROL_ELF

WORK = PROBES/"nes-control798"


def log_evidence(path):
    data = path.read_bytes()
    assert len(data)%512 == 0
    rows = [re.fullmatch(rb"MMC796 seq=(\d+) stage=(\w+) bytes=(\d+) total=(\d+) elapsed_ms=(\d+) .*",
                         data[i:i+512].splitlines()[0]) for i in range(0,len(data),512)]
    assert all(m and int(m[1])==i for i,m in enumerate(rows))
    last = rows[-1]
    return dict(hash=sha(path), records=len(rows), last=last[2].decode(), ms=int(last[5]),
                total=int(last[4]), display_stopped=any(m[2]==b"DISPLAY_STOPPED" for m in rows))


def verify(n, firmware, renderer, temp, prior, *, work=WORK, parent=None):
    src = work/f"link{n}/src"
    fw = digest(firmware)
    size,crc,inv = struct.unpack_from("<III",firmware,8)
    assert firmware[:4]==b"STM3" and size+512==len(firmware)<=212992
    assert crc==zlib.crc32(firmware[512:]) and inv^crc==0xffffffff
    assert sha(src/"obj-nes-100/sd2snes.elf")==CONTROL_ELF[str(n)]
    for name in ("progress","budget","game-last"):
        assert f"/sd2snes/nes-{name}-mmc{n}.txt\0".encode() in firmware
    for name in (f"nes/mmc{n}.nes",f"fpga_mmc{n}.bi3"):
        assert f"/sd2snes/{name}\0".encode() in firmware
    cpu = Machine(src,bytes(128))
    for marker, expected in ((f"NES MMC3 {n}.nh1",384),(f"NES-DIAG/NES START {n}.nh1",385),
                             (f"NES-DIAG/NES BOOT {n}.nh1",386),("NES BOOT 796.nh1",0)):
        addr=0x20012000
        cpu.u.mem_write(addr,marker.encode()+b"\0")
        assert cpu.call("marker_geometry",[addr])==expected
    cases=[]
    for probe, scenarios in enumerate((
            [(1,None),(20,None),(21,None),(2,"copy"),(2,"defer"),(2,"timer"),(2,"done"),(2,"start"),(2,"stop")],
            [(2,None),(2,"start"),(2,"stop")],
            [(2,None),(2,"copy"),(21,None),(2,"defer"),(2,"done"),(2,"stop")])):
        for delay,fault in scenarios:
            row=replay(src,delay,fault,probe=probe)
            cases.append(dict(probe=probe, delay_ms=delay, fault=fault, frames=row["frame_entry"],
                              terminal=row["terminal"], records=row["records"]))
    checks=work/f"check{n}"
    menu=read(checks/"menu.json")
    assert menu["firmware"]==fw and menu["marker_cases"]==4
    for fault in ("none","program","done","busy","token"):
        base=read(checks/f"base-{fault}/result.json")
        assert base["passed"] and base["firmware_sha256"]==fw
        assert base["base_restored"]==base["safe_return"]==int(fault=="none")
    mode=read(checks/"mode.json")
    if n in (798,802):
        assert mode["firmware_SHA256"]==fw and mode["unfinished_excluded"]
        assert [(w["start_s"],w["end_s"]) for w in mode["accepted"]]==[(5,40),(40,55)]
    else:
        assert mode["firmware"]==fw and mode["passed"]
    phases=[]
    for phase in (1,2):
        folder=temp/f"{work.name}-{n}-p{phase}"
        joint=read(folder/"joint.json")
        assert joint["passed"] and joint["last_status"]==1 and joint["commits"]==2
        assert joint["firmware_SHA256"]==fw and joint["client_SHA256"]==prior["ROM_SHA256"]
        assert [r["generation"] for r in joint["frames"]]==[905,906]
        assert joint["frames"][0]["release_masterclock"]==(7288416,7467100)[phase-1]
        pixels=[sha(folder/f"frame-{g}.rgb") for g in (905,906)]
        reference = f"nes-reset796b-{n-2}" if parent is None else f"nes-control798-{parent}"
        assert pixels==[sha(temp/f"{reference}-p{phase}/frame-{g}.rgb") for g in (905,906)]
        phases.append(dict(frames=joint["frames"],pixels=pixels))
    good,bad=(check(src,renderer,damaged) for damaged in (False,True))
    assert good["accepted"] and not bad["accepted"] and good["firmware"]==bad["firmware"]==fw
    return dict(firmware=fw,ELF=CONTROL_ELF[str(n)],free_flash_B=212992-len(firmware),
                control=n-35 if parent is None else parent,client=prior["ROM_SHA256"],phases=phases,boot=cases,
                checks={p.relative_to(checks).as_posix():sha(p) for p in sorted(checks.rglob("*.json"))},
                GBC_loader=[good,bad],dispatch=check_cartridge_dispatch(src))


def package(temp,log):
    evidence=log_evidence(log)
    prior=read(ROOT/"analysis/trial763-package.json")
    old=PROBES/"nes-trial763/trial01/MMC763-766-707D-AB.zip"
    assert sha(old)==prior["ZIP_SHA256"]
    files={"README-KO.txt":(ROOT/"docs/nes-mmc798-799-trial.ko.md").read_bytes()}
    variants={}
    with ZipFile(PROBES/"gbc-rgb774/GBC774-RGB555-SD-ROOT.zip") as gbc:
        shared={k:gbc.read(k) for k in GBC}
    assert {k:digest(v) for k,v in shared.items()}==GBC
    with ZipFile(old) as control:
        for n, mode in ((798,"60SEC"),(799,"LONG")):
            parent=f"0{n-797}-MMC{n-35}-A-{mode}-SD-ROOT/"
            prefix=f"0{n-797}-MMC{n}-{mode}-SD-ROOT/"
            fw=(WORK/f"link{n}/src/obj-nes-100/firmware.stm").read_bytes()
            assets=dict(shared)
            for name in ("sd2snes/fpga_base.bi3","sd2snes/m3nu.bin",f"sd2snes/fpga_mmc{n-35}.bi3"):
                key=parent+name
                data=control.read(key)
                assert digest(data)==prior["files"][key]
                assets[name.replace(str(n-35),str(n))]=data
            variants[n]=verify(n,fw,shared["sd2snes/gbc_snes.bin"],temp,prior["variants"][str(n-35)])
            assets["sd2snes/firmware.stm"]=fw
            for name in ("NES MMC3","NES-DIAG/NES BOOT","NES-DIAG/NES START"):
                assets[f"{name} {n}.nh1"]=b""
            assets["sd2snes/nes/ROM-NOT-INCLUDED.txt"]=f"Copy your SMB3(J) ROM here as mmc{n}.nes.\n".encode()
            files.update({prefix+k:v for k,v in assets.items()})
    manifest=dict(variants=variants,reported796=evidence,physical_trial798_799=False,
                  files={k:digest(v) for k,v in files.items()})
    files["manifest.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
    archive=WORK/"MMC798-60SEC-MMC799-LONG.zip"
    with ZipFile(archive,"x",ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k,v)
    with ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(files) and all(z.read(k)==v for k,v in files.items())
    save(ROOT/"analysis/control798-package.json",dict(**manifest,ZIP_SHA256=sha(archive)))
    print(archive,sha(archive))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("temp","log"):
        parser.add_argument(name,type=Path)
    a=parser.parse_args()
    package(a.temp,a.log)
