"""Qualify the ARM-only MMC807/808 handoff against the physical MMC805/806 ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from prepare_nes_trial802 import PROBES

ROOT=Path(__file__).resolve().parents[1]
WORK=PROBES/"nes-obj807"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def package(temp):
    baseline=read(ROOT/"analysis/trial805-package.json")
    parent_zip=PROBES/"nes-trial805/MMC805-60SEC-MMC806-LONG.zip"
    assert digest(parent_zip.read_bytes())==baseline["ZIP_SHA256"]
    files={"README-KO.txt":(ROOT/"docs/nes-mmc807-808-trial.ko.md").read_bytes()}
    evidence={}
    assert "# OBJ807_EXPORT_LEASE_PASS" in (WORK/"lease-local.log").read_text(encoding="utf8")
    with ZipFile(parent_zip) as z:
        for n in (807,808):
            old=n-2
            prefix=f"01-MMC{old}-" if n==807 else f"02-MMC{old}-"
            src=WORK/f"link{n}/src"
            out=WORK/f"check{n}"
            fw=(src/"obj-nes-100/firmware.stm").read_bytes()
            guards=read(out/"independent.json")
            runtime=read(out/"runtime.json")
            assert len(fw)<=212992 and digest(fw)==guards["firmware"]==runtime["firmware"]
            assert runtime["service_stop_pending"] and runtime["runtime_consecutive_skips"]==2
            assert guards["ACK"]["corrupt_bits"]==152
            assert read(out/"menu.json")==guards["menu"]
            assert read(out/"stopped.json")==read(PROBES/f"nes-trial805/check{old}/stopped.json")
            modes=read(out/"mode.json")
            report=read(out/"report.json")
            assert report["file"]==f"/sd2snes/nes-game-last-mmc{n}.txt"
            for name in ("progress","game-last","budget"):
                assert f"nes-{name}-mmc{n}.txt".encode() in fw
            assert f"mmc{n}.nes".encode() in fw and f"fpga_mmc{n}.bi3".encode() in fw
            phases={}
            for phase in (1,2):
                current=read(temp/f"nes-obj807-{n}-p{phase}/result.json")
                previous=read(temp/f"nes-trial805-{old}-p{phase}/result.json")
                assert current["passed"] and current["commits"]==2 and current["vram_DMA_B"]==16384
                assert [f["generation"] for f in current["frames"]]==[905,906]
                phases[phase]=dict(ack=[f["ACK_masterclock"] for f in current["frames"]],
                                   previous_ack=[f["ACK_masterclock"] for f in previous["frames"]])
            for path in z.namelist():
                if not path.startswith(prefix):
                    continue
                data=z.read(path)
                assert digest(data)==baseline["files"][path]
                if path.endswith("firmware.stm"):
                    data=fw
                elif path.endswith("ROM-NOT-INCLUDED.txt"):
                    data=data.replace(str(old).encode(),str(n).encode())
                files[path.replace(str(old),str(n))]=data
            evidence[n]=dict(arm=runtime,ack_checks=guards["ACK"],mode=modes,report=report,phases=phases)
    assert len(files)==21 and not any("restore" in name.lower() for name in files)
    proof=dict(previous_zip=baseline["ZIP_SHA256"],files={name:digest(data) for name,data in files.items()},
               variants=evidence,physical_test=False,export_lease_test="OBJ807_EXPORT_LEASE_PASS")
    files["manifest.json"]=(json.dumps(proof,indent=2)+"\n").encode()
    zip_path=WORK/"MMC807-60SEC-MMC808-LONG.zip"
    with ZipFile(zip_path,"x",ZIP_DEFLATED) as z:
        for name,data in files.items():
            z.writestr(name,data)
    with ZipFile(zip_path) as z:
        assert z.testzip() is None and set(z.namelist())==set(files)
        assert all(z.read(name)==data for name,data in files.items())
    proof["ZIP_SHA256"]=digest(zip_path.read_bytes())
    (ROOT/"analysis/obj807-results.json").write_text(json.dumps(proof,indent=2)+"\n",newline="\n")
    print(zip_path,proof["ZIP_SHA256"])


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    package(p.parse_args().temp)
