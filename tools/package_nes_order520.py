# SPDX-License-Identifier: MIT
"""Package an MMC520 SD trial only after both matched schedules and ARM recovery pass."""
import argparse
import hashlib
import json
import struct
import zipfile
import zlib
from pathlib import Path

from nes_schedule492 import funcs, sha
from package_nes_window516 import LABELS

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def labels(a):
    assert sha(a.base/"obj-nes-100/firmware.stm")==read(ROOT/"analysis/order520-verification.json")["guards"]["blobs"]["candidate"]["sha256"]
    a.out.mkdir(parents=True, exist_ok=False)
    for name in LABELS:
        source=(a.base/name).read_text()
        assert "516" in source
        (a.out/name).write_text(source.replace("516","520"),encoding="utf8",newline="\n")


def package(a):
    evidence=read(ROOT/"analysis/order520-verification.json")
    assert {r["start_clock"] for r in evidence["phases"]}=={3000000,3178684}
    for r in evidence["phases"]:
        b,c=r["builds"]["baseline"],r["builds"]["candidate"]
        assert c["warm_ms"] < b["warm_ms"] and c["dense_ms"] < b["dense_ms"]
        assert r["identical_displays"]==53 and r["canonical_tiles"]==444
        assert next(f["obj_bulk"] for f in b["heavy"] if f["generation"]==952)==9
        assert next(f["obj_bulk"] for f in c["heavy"] if f["generation"]==952)==5
    old=read(ROOT/"analysis/window516-package.json")
    assert sha(a.prior)==old["ZIP_SHA256"]
    base=a.base/"obj-nes-100"
    arm=a.arm/"obj-nes-100"
    assert sha(base/"firmware.stm")==evidence["guards"]["blobs"]["candidate"]["sha256"]
    before,after=[(folder/"firmware.stm").read_bytes() for folder in (base,arm)]
    functions=funcs(base/"sd2snes.elf")
    assert len(functions)>700 and functions==funcs(arm/"sd2snes.elf")
    assert len(before)==len(after)<=0x34000 and after[:4]==b"STM3"
    assert before[32:].replace(b"516",b"520")==after[32:]
    size,crc,inverse=struct.unpack_from("<III",after,8)
    assert size==len(after)-512 and crc==zlib.crc32(after[512:]) and inverse^crc==0xffffffff
    fw_hash=sha(arm/"firmware.stm")
    guards=read(a.checks/"label-guards01/result.json")
    assert guards["passed"] and guards["candidate_SHA256"]==fw_hash and len(guards["rows"])==40
    assert guards["baseline_SHA256"]==evidence["guards"]["blobs"]["baseline"]["sha256"]
    window=read(a.checks/"windows-label01.json")
    assert window["firmware_SHA256"]==fw_hash and [r["displays"] for r in window["accepted"]]==[2,2]
    recovery={}
    for fault in ("none","program","done","busy","token"):
        test=read(a.checks/f"recovery-{fault}/result.json")
        assert test["passed"] and test["firmware_sha256"]==fw_hash
        assert test["safe_return"]==test["base_restored"]==int(fault=="none")
        recovery[fault]=test["safe_return"]
    logs=["sd2snes/nes-"+name+"-mmc520.txt" for name in ("progress","budget","game-last")]
    for label in [*logs,"sd2snes/fpga_mmc520.bi3","sd2snes/nes/mmc520.nes","NES MMC3 520.nh1"]:
        assert (("/"+label) if label.startswith("sd2snes/") else label).encode() in after
    prefix="01-MMC520-SD-ROOT/"
    files={}
    with zipfile.ZipFile(a.prior) as z:
        for source,dest in (("fpga_base.bi3","fpga_base.bi3"),("m3nu.bin","m3nu.bin"),("fpga_mmc516.bi3","fpga_mmc520.bi3")):
            key="01-MMC516-SD-ROOT/sd2snes/"+source
            blob=z.read(key)
            assert hashlib.sha256(blob).hexdigest()==old["files"][key]
            files[prefix+"sd2snes/"+dest]=blob
    files[prefix+"sd2snes/firmware.stm"]=after
    files[prefix+"NES MMC3 520.nh1"]=b""
    files[prefix+"sd2snes/nes/ROM-NOT-INCLUDED.txt"]=b"Copy your own mmc516.nes unchanged as mmc520.nes. CRC32 5a04eed7.\n"
    files["읽어주세요.txt"]=(ROOT/"docs/nes-mmc520-trial.ko.md").read_bytes()
    assert not any(s.lower().endswith((".nes",".sav",".srm",".rtc")) or "RESTORE" in s.upper() for s in files)
    report=dict(candidate="MMC520",physical_verified=False,firmware_SHA256=fw_hash,compatible_ROM=old["required_ROM"]["SHA256"],
                BI3_SHA256=old["BI3_SHA256"],unchanged_functions=len(functions),base_return=recovery,logs=logs,
                evidence_sha256=sha(ROOT/"analysis/order520-verification.json"),
                files={k:hashlib.sha256(v).hexdigest() for k,v in files.items()})
    files["manifest.json"]=(json.dumps(report,indent=2,ensure_ascii=False)+"\n").encode()
    a.out.mkdir(parents=True,exist_ok=False)
    archive=a.out/"MMC520-TRIAL.zip"
    with zipfile.ZipFile(archive,"x") as z:
        for name,blob in files.items():
            z.writestr(zipfile.ZipInfo(name),blob,compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(files) and all(z.read(k)==v for k,v in files.items())
    report.update(ZIP_SHA256=sha(archive),ZIP_bytes=archive.stat().st_size)
    (a.out/"result.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8",newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    for action in ("labels","package"):
        cmd=sub.add_parser(action)
        names=("base","out") if action=="labels" else ("base","arm","prior","checks","out")
        for n in names:cmd.add_argument("--"+n,type=Path,required=True)
    args=p.parse_args()
    (labels if args.action=="labels" else package)(args)
