"""Build first-stage retest editions from the measured ARM links and the MMC811/812 SD bundle."""
import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from analyze_nes_order810 import compare
from package_nes_obj807 import ROOT, digest, read
from package_nes_trial811 import LONG_CLIENT, TIMED_CLIENT
from prepare_nes_prefix813 import PARENTS, PROBES, WORK


def package(temp):
    parent = read(ROOT/"analysis/trial811-package.json")
    hardware = read(ROOT/"analysis/hardware812-results.json")["sessions"]
    archive = PROBES/"nes-trial811/MMC811-60SEC-MMC812-LONG.zip"
    assert digest(archive.read_bytes()) == parent["ZIP_SHA256"]
    clients = {"mmc813":TIMED_CLIENT, "mmc814":LONG_CLIENT}
    phases = compare(temp, list(clients), clients=clients)
    files = {"README-KO.txt":(ROOT/"docs/nes-mmc813-814-trial.ko.md").read_bytes()}
    builds = {}
    with ZipFile(archive) as z:
        for n,(old,_) in PARENTS.items():
            fw = (WORK/f"link{n}/src/obj-nes-100/firmware.stm").read_bytes()
            image = digest(fw)
            checks = WORK/f"check{n}"
            guards = read(checks/"guards.json")
            assert len(fw)<=212992 and guards["candidate"]==dict(firmware=image,bytes=len(fw))
            assert guards["guards"]["ACK"]["corrupt_bits"]==152
            assert guards["object_recovery"]["service_stop_pending"] and guards["object_recovery"]["runtime_consecutive_skips"]==2
            assert guards["guards"]["menu"]["rows"]["normal"]["released"]==1
            prefix=read(checks/"prefix.json")
            assert prefix["planar"]["verified_bytes"]==2048 and not any(x["committed"] for x in prefix["map_grant"] if x["case"]!="under_threshold")
            assert read(checks/"stopped.json")==read(PROBES/f"nes-trial811/check{PARENTS[n][1]}/stopped.json")
            assert read(checks/"report.json")["file"]==f"/sd2snes/nes-game-last-mmc{n}.txt"
            for fault in ("none","program","done","busy","token"):
                r=read(checks/f"base-{fault}/result.json")
                assert r["passed"] and r["firmware_sha256"]==image
                assert r["safe_return"]==r["base_restored"]==int(fault=="none")
            mode=read(checks/"mode.json")
            if n==813:
                assert mode["firmware_SHA256"]==image and mode["layout"]=="trimmed"
                deadline=read(checks/"deadline.json")
                assert deadline["passed"] and deadline["firmware"]==image
            else:
                assert mode["firmware"]==image and mode["passed"]
                exit_test=read(temp/"nes-mmc814-exit/result.json")
                assert exit_test["passed"] and exit_test["CPU"]==LONG_CLIENT
                assert {r["mode"] for r in exit_test["cases"] if r["passed"]}=={"packet","dma"}
            for tag in ("game-last","budget","progress"):
                assert f"nes-{tag}-mmc{n}.txt".encode() in fw
            for name in (f"fpga_mmc{n}.bi3",f"mmc{n}.nes"):
                assert name.encode() in fw
            original, fixed = (read(WORK/f"repro{i}.json") for i in (old,n))
            assert original["firmware"]==parent["variants"][str(old)]["firmware"] and fixed["firmware"]==image
            counters=hardware[str(old)]["game"]
            pre=original["cases"]["end_"+counters["sink_window_sent"]]
            post=fixed["cases"]["end_"+counters["sink_window_sent"]]
            assert pre["retired"]==int(counters["sink_window_retired"]) and pre["window_error"]==pre["plan_error"]==5
            assert post["plan_sent"]==4 and post["window_error"]==post["plan_error"]==0
            assert fixed["cases"]["bad_status"]["window_error"]==5
            timed={}
            for phase,rows in phases.items():
                r=rows[f"mmc{n}"]
                assert r["firmware"]==image and r["commits"]==r["rgb_map_checked"]==66
                assert r["restored951"] and r["line951"]<=246 and r["display959"]==2
                assert r["vs807_last_ACK_ms"]<0
                timed[phase]={k:r[k] for k in ("restored951","line951","early951","display959","dense_vblank",
                               "interval_changes_vs807","last_ACK","vs807_last_ACK_ms","vs807_dense_ms","hashes")}
            folder="01-MMC811-" if n==813 else "02-MMC812-"
            names=[k for k in z.namelist() if k.startswith(folder)]
            assert len(names)==10
            for name in names:
                data=z.read(name)
                assert digest(data)==parent["files"][name]
                if name.endswith("/firmware.stm"):
                    data=fw
                elif name.endswith("ROM-NOT-INCLUDED.txt"):
                    data=data.replace(str(old).encode(),str(n).encode())
                files[name.replace(str(old),str(n))]=data
            builds[n]=dict(firmware=image,bytes=len(fw),flash_free=212992-len(fw),phases=timed,
                           pre=original,post=fixed,guards_sha256=digest((checks/"guards.json").read_bytes()))
    proof=dict(parent_sha256=parent["ZIP_SHA256"],builds=builds,physical_first_stage_retest=False,
               files={k:digest(v) for k,v in files.items()})
    files["manifest.json"]=(json.dumps(proof,indent=2)+"\n").encode()
    assert len(files)==22 and not any("restore" in k.lower() or k.endswith(".nes") for k in files)
    path=WORK/"MMC813-60SEC-MMC814-LONG.zip"
    with ZipFile(path,"x",ZIP_DEFLATED) as z:
        for name,data in files.items():
            entry=ZipInfo(name)
            entry.create_system=0
            entry.external_attr=0x20
            z.writestr(entry,data,compress_type=ZIP_DEFLATED)
    with ZipFile(path) as z:
        assert z.testzip() is None and set(z.namelist())==set(files)
        assert all(z.read(k)==v for k,v in files.items())
    proof["ZIP_SHA256"]=digest(path.read_bytes())
    (ROOT/"analysis/prefix813-results.json").write_text(json.dumps(proof,indent=2)+"\n",newline="\n")
    print(path,proof["ZIP_SHA256"])


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    package(p.parse_args().temp)
