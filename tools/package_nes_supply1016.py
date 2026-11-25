"""Package the final instrumented board and linked MMC1012-based ARM firmware."""
import argparse
import json
import re
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace
from nes_display1010 import ROOT, QUARTUS
from analyze_nes_chr951 import board_cost
from package_nes_trial704 import decode, digest, image, sha
from package_nes_trial872 import write_verified_archive
from prepare_nes_supply1016_arm import WORK, SRC, BASE

def read(path):
    return json.loads(path.read_bytes())

def package(board):
    reference=read(ROOT/"analysis/trial1012-package.json")
    cost=board_cost(board)
    assert cost["fit"] and min(cost["slack_ns"].values())>0
    for module in ("nes_supply1016","nes_supply1016_host"):
        assert sha(board/(module+".sv"))==sha(ROOT/"tests/nes-functional"/(module+".sv"))
    for log in ("sim","source-sim"):
        assert "PASS1016" in (board/"wire"/(log+".log")).read_text()
    mif,=(board/"db").glob("board.ram*_nes_sink_bus165_*.hdl.mif")
    cells=sorted((int(i),int(v,2)) for i,v in re.findall(r"^\s*(\d+)\s*:\s*([01]{8});",mif.read_text(),re.M))
    rom=(board.parent/"nes-display1010-ppu-p1/client.sfc").read_bytes()
    assert digest(rom)==reference["client"] and [i for i,_ in cells]==list(range(5120))
    assert bytes(v for _,v in cells)==rom[:5056]+rom[-64:]==bytes.fromhex((board/"sink-program.hex").read_text())
    fw=(SRC/"obj-nes-100/firmware.stm").read_bytes()
    size,crc,inverse=struct.unpack_from("<III",fw,8)
    assert fw[:4]==b"STM3" and len(fw)==size+512<=212992
    assert zlib.crc32(fw[512:])==crc and crc^inverse==0xffffffff
    for name in (" 1016.nh1","mmc1016.nes","fpga_mmc1016.bi3","nes-frame-mmc1016.bin",
                 "nes-game-last-mmc1016.txt","nes-budget-mmc1016.txt","nes-progress-mmc1016.txt"):
        assert name.encode()+b"\0" in fw,name
    proof=WORK/"proof"
    checks={k:read(proof/(k+".json")) for k in ("timer","menu","sram","windows","wire","base-result","loader","client-faults")}
    key=digest(fw)
    assert all(checks[k]["firmware"]==key for k in ("timer","menu","loader"))
    assert checks["windows"]["firmware_SHA256"]==checks["base-result"]["firmware_sha256"]==checks["wire"]["firmware_sha256"]==key
    assert checks["timer"]["passed"] and checks["menu"]["rows"]["normal"]["released"]
    assert checks["base-result"]["safe_return"] and checks["base-result"]["base_restored"]
    assert checks["sram"]["cases"]["normal"]["checked_retire"]
    assert checks["loader"]["cases"]["original"]["program"] and not checks["loader"]["cases"]["damaged"]["program"]
    assert all(c["previous_screen_retained"] for c in checks["client-faults"].values())
    x=checks["wire"];assert len(x["rejected"])==6 and x["actual_source_counts"]["demand_ROM"]==56
    assert len(x["fast"]["tiles"])==len(x["slow"]["tiles"])==15
    out=board/"image1016"
    if not out.is_dir():
        image(SimpleNamespace(board=board,out=out,quartus=QUARTUS,number="1016"))
    info=read(out/"image.json");packed=(out/"fpga_mmc1016.bi3").read_bytes()
    assert info["SOF"]==sha(board/"output_files/board.sof")==sha(out/"board.sof")
    assert info["programmer"]["passed"] and info["BI3"]==digest(packed)==info["programmer"]["image_sha256"]
    assert info["RBF"]==digest(decode(packed))==info["programmer"]["rbf_sha256"]
    diff=x["slow"]["tiles"][3]["reads"][0]["first_grant"]-x["fast"]["tiles"][3]["reads"][0]["first_grant"]
    assert diff==2
    report=dict(edition=1016,reference="MMC1012",physical=False,firmware=key,flash_B=len(fw),
                flash_free_B=212992-len(fw),client=digest(rom),compiled_MIF=sha(mif),board=cost,image=info,
                source_classes=x["actual_source_counts"],physical_source_output_B=x["actual_output_bytes"],
                injected_prefetch_delay_NES_ticks=diff,invalid_pages_rejected=list(x["rejected"]),
                reference_boot_ROM_MIF_identical=True,linked_stop_and_base_recovery=True,
                SRAM_D0_cases=list(checks["sram"]["cases"]),STOP_checks=checks["client-faults"],
                proof_sha256={k:sha(proof/(k+".json")) for k in checks})
    write_verified_archive(WORK,reference,fw,packed,report,source=BASE/"MMC1012-ADVENTURE-60SEC-SD-ROOT.zip")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("board",type=Path)
    package(p.parse_args().board)

