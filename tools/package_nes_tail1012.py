"""Package the qualified MMC1012 ARM with the byte-identical MMC1010 board and PPU client."""
import json
import struct
import zlib
from zipfile import ZipFile

from nes_display1010 import ROOT
from package_nes_trial872 import write_verified_archive
from package_nes_trial704 import digest, read
from prepare_nes_display1010_arm import PROBE
from prepare_nes_tail1012 import WORK
from read_nes_tail1012 import SIZE


def package():
    ref=read(ROOT/"analysis/trial1010-package.json")
    source=PROBE.parent/"MMC1010-ADVENTURE-60SEC-SD-ROOT.zip"
    proof=WORK/"proof"
    firmware=(WORK/"link/src/obj-nes-100/firmware.stm").read_bytes()
    h=digest(firmware)
    size,crc,inverse=struct.unpack_from("<III",firmware,8)
    assert firmware[:4]==b"STM3" and size+512==len(firmware)<=212992
    assert zlib.crc32(firmware[512:])==crc==inverse^0xffffffff
    for suffix in (" 1012.nh1","mmc1012.nes","fpga_mmc1012.bi3","nes-frame-mmc1012.bin",
                   "nes-game-last-mmc1012.txt","nes-progress-mmc1012.txt","nes-budget-mmc1012.txt"):
        assert suffix.encode()+b"\0" in firmware
    checks={name:read(proof/(name+".json")) for name in ("windows","loader","timer","menu","sram","base-result","trace")}
    assert checks["windows"]["firmware_SHA256"]==checks["base-result"]["firmware_sha256"]==h
    assert all(checks[n]["firmware"]==h for n in ("menu","loader","timer"))
    assert checks["base-result"]["safe_return"] and checks["timer"]["passed"] and checks["trace"]["grouped_credit"]
    assert checks["menu"]["rows"]["normal"]["released"] and checks["sram"]["cases"]["normal"]["checked_retire"]
    assert all((proof/f"mode{i}.bin").stat().st_size==SIZE for i in range(4))
    with ZipFile(source) as z:
        board=z.read(next(n for n in z.namelist() if n.endswith("/fpga_mmc1010.bi3")))
    assert digest(board)==ref["image"]["BI3"] and ref["evidence"]["positive_STA"]
    report=dict(edition=1012,physical=False,firmware=h,client=ref["client"],board_BI3=digest(board),
        board_edition=1010,flash_B=len(firmware),flash_free_B=212992-len(firmware),
        log_B=SIZE,checks=checks)
    write_verified_archive(WORK,ref,firmware,board,report,source=source)


if __name__=="__main__":
    package()
