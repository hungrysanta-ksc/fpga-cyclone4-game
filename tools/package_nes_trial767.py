"""Build the corrected 60-second comparison with the verified 765 FPGA bytes."""
import argparse
import json
import struct
import zlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from analyze_nes_static751 import phase
from package_nes_trial704 import digest, read, save, sha
from prepare_nes_trial763 import PROBES, ROOT


def run(temp, out):
    base = read(ROOT / "analysis/trial763-package.json")
    prior = PROBES / "nes-trial763/trial01/MMC763-766-707D-AB.zip"
    assert sha(prior) == base["ZIP_SHA256"]
    root = PROBES / "nes-timer767"
    src = root / "arm/src/obj-nes-100"
    fw = (src / "firmware.stm").read_bytes()
    size, crc, inv = struct.unpack_from("<III",fw,8)
    assert fw[:4]==b"STM3" and size+512==len(fw)<=212992 and zlib.crc32(fw[512:])==crc and crc^inv==0xffffffff
    mark="NES MMC3 767.nh1"
    for name in (mark,"/sd2snes/fpga_mmc767.bi3","/sd2snes/nes/mmc767.nes",
                 *("/sd2snes/nes-"+k+"-mmc767.txt" for k in ("progress","budget","game-last"))):
        assert name.encode()+b"\0" in fw and name.replace("767","765").encode()+b"\0" not in fw
    h=digest(fw)
    guards=read(root/"linked-guards.json")
    assert guards["run"]["firmware"]==h and guards["hardware_fault_blocked"]
    credit=read(root/"credit.json")
    assert credit["firmware"]==credit["menu"]["firmware"]==h and credit["seal_receipts"]["corrupt_bits"]==152
    assert read(root/"window.json")["firmware_SHA256"]==h
    for fault in ("none","program","done","busy","token"):
        r=read(root/f"base-{fault}/result.json")
        assert r["passed"] and r["firmware_sha256"]==h and r["config_paths"]==["/sd2snes/fpga_mmc767.bi3","/sd2snes/fpga_base.bi3"]
        assert r["safe_return"]==r["base_restored"]==int(fault=="none")
    files={}
    with ZipFile(prior) as z:
        for name,expected in base["files"].items():
            if name.startswith("04-MMC766-"):
                data=z.read(name)
                assert digest(data)==expected
                files[name.replace("04-MMC","02-MMC",1)]=data
            elif name.startswith("03-MMC765-"):
                data=z.read(name)
                assert digest(data)==expected
                if name.endswith("/firmware.stm"):
                    data=fw
                elif name.endswith("/ROM-NOT-INCLUDED.txt"):
                    data=data.replace(b"765",b"767")
                files[name.replace("03-MMC765","01-MMC767").replace("765","767")]=data
    files["README-KO.txt"]=(ROOT/"docs/nes-mmc767-trial.ko.md").read_bytes()
    timelines={}
    for n in (1,2):
        folder=temp/f"nes-timer767-phase{n}"
        client=PROBES/"nes-static751/sharedfast"
        j=read(folder/"joint.json")
        assert j["passed"] and j["commits"]==53 and j["firmware_SHA256"]==h and j["client_SHA256"]==sha(client/"sink165.sfc")
        ref=temp/f"nes-credit753-prefix{n}"
        for g in range(905,958):
            for name in (f"map-{g}.bin",f"expected-{g}.bin",f"frame-{g}.rgb"):
                assert (folder/name).read_bytes()==(ref/name).read_bytes()
        v=phase(temp,"sharedfast",n,client=client,folder=folder,firmware=h)
        assert v["guarded_schedule"] and v["final_wait957"] == 0
        timelines[n]={k:v[k] for k in ("long_map","guarded_schedule","line951","final_wait957","OBJ","intervals","dense_ms","ACK","order","E8_delta_us")}
    result=dict(firmware=h,ELF=sha(src/"sd2snes.elf"),Flash_free=212992-len(fw),boot_guards=guards,
                schedule=timelines,board_and_long_source=base["ZIP_SHA256"],
                files={k:digest(v) for k,v in files.items()},physical=False)
    files["manifest.json"]=(json.dumps(result,indent=2)+"\n").encode()
    assert not any("restore" in k.lower() or k.lower().endswith((".nes",".sav",".srm")) for k in files)
    with ZipFile(out,"x",ZIP_DEFLATED) as z:
        for k,v in files.items():
            z.writestr(k,v)
    with ZipFile(out) as z:
        assert not z.testzip() and set(z.namelist())==set(files) and all(z.read(k)==v for k,v in files.items())
    result.update(ZIP_SHA256=sha(out),ZIP_bytes=out.stat().st_size)
    save(ROOT/"analysis/trial767-package.json",result)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace_root",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    run(a.trace_root,a.out)
