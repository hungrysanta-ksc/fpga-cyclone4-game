"""Qualify the final MMC1014 map-only ARM on the MMC1012 hardware configuration."""
import argparse
import json
import shutil
import struct
import zlib
from pathlib import Path
from zipfile import ZipFile

from guard_nes_tail1013 import client_faults
from check_nes_tail1012 import run as check_arm
from check_nes_tail1013 import collect, run_dir
from nes_tail1013 import BASE, ROOT, WORK as EXPERIMENT
from package_nes_trial704 import digest, read
from package_nes_trial872 import write_verified_archive
from replay_nes_tail1013 import run as replay

EDITION=1014
WORK=BASE.with_name("nes-trial1014")
SRC=WORK/"link/src"


def prepare():
    source=EXPERIMENT/"map/link"
    measurements=read(ROOT/"analysis/tail1013-results.json")
    assert digest((source/"src/obj-nes-100/firmware.stm").read_bytes())==measurements["guards"]["map"]["firmware"]
    shutil.copytree(source,WORK/"link",ignore=shutil.ignore_patterns("*.log"))
    for name in ("VERSION","nes_menu_diagnostic.c","nes_checkpoint112.c","nes_budget210.c"):
        f=SRC/name
        old=f.read_bytes()
        if name=="nes_budget210.c":
            new=old.replace(b"edition=1012",b"edition=1014").replace(b"mmc1012",b"mmc1014")
        else:
            new=old.replace(b"1012",b"1014")
        assert new!=old,name
        f.write_bytes(new)


def package(temp):
    prior=read(ROOT/"analysis/trial1012-package.json")
    source=BASE/"MMC1012-ADVENTURE-60SEC-SD-ROOT.zip"
    fw=(SRC/"obj-nes-100/firmware.stm").read_bytes()
    checksum=digest(fw)
    size,crc,inv=struct.unpack_from("<III",fw,8)
    assert fw[:4]==b"STM3" and size+512==len(fw)<=212992 and zlib.crc32(fw[512:])==crc==inv^0xffffffff
    for name in (" 1014.nh1","mmc1014.nes","fpga_mmc1014.bi3","nes-frame-mmc1014.bin",
                 "nes-game-last-mmc1014.txt","nes-progress-mmc1014.txt","nes-budget-mmc1014.txt"):
        assert name.encode()+b"\0" in fw and name.replace("1014","1012").encode()+b"\0" not in fw,name
    proof=WORK/"proof"
    checks={n:read(proof/(n+".json")) for n in ("windows","timer","loader","sram","menu","base-result","trace")}
    assert checks["windows"]["firmware_SHA256"]==checks["base-result"]["firmware_sha256"]==checksum
    assert all(checks[k]["firmware"]==checksum for k in ("loader","timer","menu"))
    assert checks["base-result"]["safe_return"] and checks["timer"]["passed"] and checks["trace"]["grouped_credit"]
    assert checks["menu"]["rows"]["normal"]["released"] and checks["sram"]["cases"]["normal"]["checked_retire"]
    assert all((proof/f"mode{i}.bin").stat().st_size==prior["log_B"] for i in range(4))
    selected_firmware=read(ROOT/"analysis/tail1013-results.json")["guards"]["map"]["firmware"]
    phases={}
    for phase in (1,2):
        rows,run=collect(temp/f"nes-tile821-late-jointmirror-p{phase}-1014-final")
        selected,old=collect(run_dir(temp,phase,"map"))
        control,baseline=collect(run_dir(temp,phase,"control"))
        assert baseline["firmware_SHA256"]==prior["firmware"] and run["firmware_SHA256"]==checksum
        assert old["firmware_SHA256"]==selected_firmware
        assert run["client_SHA256"]==old["client_SHA256"]==baseline["client_SHA256"]==prior["client"]
        assert rows==selected and run["wire_B"]==old["wire_B"]
        assert all(rows[g][k]==control[g][k] for g in rows for k in ("rgb","map","packet_digest","work"))
        total=rows[912]["show"][1]-rows[906]["show"][1]
        baseline_total=control[912]["show"][1]-control[906]["show"][1]
        gain=control[912]["ack"][0]-rows[912]["ack"][0]
        assert (baseline_total,total)==(13,12) and gain>0
        assert [entry[0] for entry in rows[908]["dma_preseal"]]==[1472]
        assert rows[909]["show"][1]-rows[908]["show"][1]==2
        assert control[909]["show"][1]-control[908]["show"][1]==3
        assert rows[908]["input_last_D2"]<13222616<control[908]["input_last_D2"]
        phases[phase]=dict(reference_intervals=baseline_total,intervals=total,ACK_advance_ms=gain/21477.272,
                           advance_DMA_908=rows[908]["dma_preseal"],all_eight_equal_selected=True)
    checks["client_faults"]=read(proof/"client-faults.json")
    for name,status in (("bad_seal",224),("stop_decode",228)):
        assert checks["client_faults"][name]==dict(commits=3,status=status,previous_screen_retained=True)
    with ZipFile(source) as z:
        board=z.read(next(n for n in z.namelist() if n.endswith("/fpga_mmc1012.bi3")))
    assert digest(board)==prior["board_BI3"]
    report=dict(edition=EDITION,firmware=checksum,client=prior["client"],board_BI3=prior["board_BI3"],
                board_edition=prior["board_edition"],physical=False,flash_B=len(fw),flash_free_B=212992-len(fw),
                log_B=prior["log_B"],checks=checks,phases=phases)
    write_verified_archive(WORK,prior,fw,board,report,source=source)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("prepare","arm","phase1","phase2","faults","pack"))
    p.add_argument("path",type=Path,nargs="?")
    args=p.parse_args()
    if args.action=="prepare":
        prepare()
    elif args.path is None:
        p.error("provide the game ROM for arm, or replay root for phase1/phase2/pack")
    elif args.action=="arm":
        check_arm(args.path,work=WORK,edition=EDITION)
    elif args.action=="faults":
        result=client_faults(args.path,args.path/"nes-tile821-late-jointmirror-p1-1014-final","nes-trial1014-guard")
        (WORK/"proof/client-faults.json").write_text(json.dumps(result))
    elif args.action=="pack":
        package(args.path)
    else:
        replay(args.path,int(args.action[-1]),"map",firmware=SRC,tag="1014-final")
