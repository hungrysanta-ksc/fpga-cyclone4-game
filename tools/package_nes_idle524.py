# SPDX-License-Identifier: MIT
"""Package the 524 CPU image and labeled MMC520 firmware after both complete schedules."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zipfile
import zlib

from nes_cf68_pair_preflight import encode, decode
from nes_schedule492 import sha
from analyze_nes_prefix523 import firmware_checks
from package_nes_window516 import LABELS

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    return json.loads(p.read_text(encoding="utf8"))


def labels(a):
    assert sha(a.base / "obj-nes-100/firmware.stm") == read(ROOT/"analysis/order520-package.json")["firmware_SHA256"]
    a.out.mkdir(parents=True,exist_ok=False)
    for name in LABELS:
        s = (a.base/name).read_text()
        assert "520" in s
        (a.out/name).write_text(s.replace("520","524"),encoding="utf8",newline="\n")


def package(a):
    evidence = read(ROOT/"analysis/idle524-verification.json")
    assert evidence["targets_met"] and len(evidence["priority"])==15
    assert evidence["paced_maximum_DMA"]["size"]==2048
    for phase in evidence["phases"]:
        assert phase["RGB_frames"]==53 and phase["tiles"]==444
        assert phase["issued_in_952_and_954"]
    board=evidence["whole_board"]
    assert all(board[f"{view}_{check}_ns"] >= 0 for view in ("implementation","nominal") for check in ("setup","hold"))
    prior = read(ROOT/"analysis/order520-package.json")
    assert sha(a.prior) == prior["ZIP_SHA256"]
    a.out.mkdir(parents=True,exist_ok=False)
    sof=a.board/"output_files/board.sof"
    assert sha(sof) == board["SOF_SHA256"]
    rbf = a.out/"board.rbf"
    with (a.out/"cpf.log").open("wb") as f:
        subprocess.run([str(a.quartus/"quartus_cpf.exe"),"-c",str(sof),str(rbf)],stdout=f,stderr=subprocess.STDOUT,timeout=300,check=True)
    raw = rbf.read_bytes()
    image = encode(raw)
    assert decode(image)==raw
    verified=firmware_checks(a.base,a.arm,a.checks,label=b"524")
    assert verified==evidence["labeled_firmware"] and verified["baseline"]==prior["firmware_SHA256"]
    assert verified["response_cases"]==40 and verified["identical_functions"]==785
    after=(a.arm/"obj-nes-100/firmware.stm").read_bytes()
    size,crc,inverse=struct.unpack_from("<III",after,8)
    assert after[:4]==b"STM3" and size==len(after)-512 and crc==zlib.crc32(after[512:]) and inverse^crc==0xffffffff
    prefix="01-MMC524-SD-ROOT/"
    logs=["sd2snes/nes-"+name+"-mmc524.txt" for name in ("progress","budget","game-last")]
    for label in [*logs,"sd2snes/fpga_mmc524.bi3","sd2snes/nes/mmc524.nes","NES MMC3 524.nh1"]:
        assert (("/"+label) if label.startswith("sd2snes/") else label).encode() in after
    files={prefix+"sd2snes/firmware.stm":after,prefix+"sd2snes/fpga_mmc524.bi3":image,prefix+"NES MMC3 524.nh1":b"",
           prefix+"sd2snes/nes/ROM-NOT-INCLUDED.txt":b"Copy your original mmc520.nes unchanged as mmc524.nes. CRC32 5a04eed7.\n",
           "읽어주세요.txt":(ROOT/"docs/nes-mmc524-trial.ko.md").read_bytes()}
    with zipfile.ZipFile(a.prior) as z:
        for name in ("sd2snes/fpga_base.bi3","sd2snes/m3nu.bin"):
            path="01-MMC520-SD-ROOT/"+name
            data=z.read(path)
            assert hashlib.sha256(data).hexdigest()==prior["files"][path]
            files[prefix+name]=data
    report=dict(candidate="MMC524",physical_verified=False,firmware_SHA256=verified["candidate"],SOF_SHA256=sha(sof),RBF_SHA256=sha(rbf),
                BI3_SHA256=hashlib.sha256(image).hexdigest(),unchanged_functions=verified["identical_functions"],base_return=verified["base_return"],
                evidence_SHA256=sha(ROOT/"analysis/idle524-verification.json"),
                compatible_ROM=prior["compatible_ROM"],logs=logs,files={k:hashlib.sha256(v).hexdigest() for k,v in files.items()})
    files["manifest.json"]=(json.dumps(report,indent=2,ensure_ascii=False)+"\n").encode("utf8")
    archive=a.out/"MMC524-TRIAL.zip"
    with zipfile.ZipFile(archive,"x") as z:
        for name,data in files.items():
            z.writestr(zipfile.ZipInfo(name),data,compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(files) and all(z.read(n)==d for n,d in files.items())
    report.update(ZIP_SHA256=sha(archive),ZIP_bytes=archive.stat().st_size)
    (a.out/"result.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8",newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    for name,args in (("labels",("base","out")),("package",("base","arm","prior","board","checks","out","quartus"))):
        parser=sub.add_parser(name)
        for arg in args:
            parser.add_argument("--"+arg,type=Path,required=True)
    a=p.parse_args()
    (labels if a.command=="labels" else package)(a)
