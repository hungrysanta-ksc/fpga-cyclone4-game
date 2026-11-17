"""Qualify fresh full-board builds and both final ARM/65816 pairs before writing the SD kit."""
import argparse
import csv
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from analyze_nes_order810 import ms
from analyze_nes_output815 import replay
from analyze_nes_status689 import cost
from package_nes_trial704 import digest, read, sha
from package_nes_trial805 import board_evidence
from nes_schedule492 import funcs
from prepare_nes_trial816 import LONG, PROBES, ROOT, TIMED, WORK


def signoff(temp, edition, client):
    base = temp/"nes-fortress804-board"
    board_evidence(base, read(ROOT/"analysis/fortress804.json"))
    board = temp/f"nes-trial816-board{edition}"
    for f in board.rglob("*"):
        rel = f.relative_to(board)
        if len(rel.parts)>1 and rel.parts[0] not in ("sys","rtl"):
            continue
        if f.suffix.lower() in (".vhd",".sv",".v",".qsf",".sdc",".hex",".qpf") and rel.as_posix()!="sink-program.hex":
            assert sha(f)==sha(base/rel),rel
    mif, = (board/"db").glob("board.ram*_nes_sink_bus165_*.hdl.mif")
    init = sorted((int(i),int(v,2)) for i,v in re.findall(r"^\s*(\d+)\s*:\s*([01]{8});",mif.read_text(),re.M))
    assert [i for i,_ in init]==list(range(5120))
    rom=(client/"sink165.sfc").read_bytes()
    assert bytes(v for _,v in init)==bytes.fromhex((board/"sink-program.hex").read_text())==rom[:5056]+rom[-64:]
    c = cost(board)
    summary=(board/"output_files/board.sta.summary").read_text()
    checks=re.findall(r"^Type\s+: (.+)\nSlack\s+: ([-.\d]+)\nTNS\s+: ([-.\d]+)",summary,re.M)
    assert len(checks)==summary.count("Type  :")>=40
    assert all(float(s)>=0 and float(t)==0 for _,s,t in checks)
    assert c["SOF"] and c["STA"] and c["LAB"]<=963 and c["M9K"][0]<=56
    assert c["unconstrained"]==cost(base)["unconstrained"]
    fit=(board/"output_files/board.fit.summary").read_text()
    assert "Fitter Status : Successful" in fit and "Lite Edition" in fit
    paths={}
    for name,key in (("paths801","slack_ns"),("io612","slack"),("reader661","slack"),("word660","slack")):
        with (board/f"{name}.tsv").open() as f:
            rows=list(csv.DictReader(f,delimiter="\t"))
        assert len({r["corner"] for r in rows})==3
        paths[name]=min(float(r[key]) for r in rows)
        assert paths[name]>=0
    phase=[line.split("\t") for line in (board/"phase801.tsv").read_text().splitlines()]
    assert {r[0] for r in phase}=={r[0] for r in (line.split("\t") for line in (base/"phase801.tsv").read_text().splitlines())}
    assert {r[2] for r in phase}=={"setup","hold"} and min(float(r[-1]) for r in phase)>=0
    packed=temp/f"nes-trial816-packed{edition}"
    im=read(packed/"image.json")
    bi=(packed/f"fpga_mmc{edition}.bi3").read_bytes()
    assert im["SOF"]==c["reports"]["board.sof"] and im["BI3"]==digest(bi)
    assert im["programmer"]["passed"] and im["programmer"]["image_sha256"]==digest(bi)
    return bi,dict(**{k:c[k] for k in ("LE","M9K","LAB","slack_ns","unconstrained","reports")},
                   MIF=sha(mif),programmer=im["programmer"]["passed"],RBF=im["RBF"],BI3=im["BI3"],
                   constraints=sha(board/"board.sdc"),checks=len(checks),path_minimum_ns=paths,phase801=phase)


def qualification(temp,n,client,fw):
    arm=digest(fw)
    checks=WORK/f"check{n}"
    guards=read(checks/"guards.json")
    assert guards["candidate"]==dict(bytes=len(fw),firmware=arm) and len(fw)<=212992
    assert guards["guards"]["ACK"]["corrupt_bits"]==152
    assert guards["guards"]["menu"]["rows"]["normal"]["released"]==1
    assert guards["object_recovery"]["service_stop_pending"] and guards["object_recovery"]["runtime_consecutive_skips"]==2
    mode=read(checks/"mode.json")
    if n==816:
        assert mode["firmware_SHA256"]==arm and mode["unfinished_excluded"]
        timeout=read(checks/"deadline.json")
        assert timeout["firmware"]==arm and timeout["passed"]
    else:
        assert mode["passed"] and mode["firmware"]==arm and all(r["passed"] for r in mode["cases"])
        manual=read(temp/"nes-trial816-exit817/result.json")
        assert manual["CPU"]==sha(client/"sink165.sfc") and manual["passed"]
        assert {r["mode"] for r in manual["cases"] if r["passed"]}=={"packet","dma"}
    prefix=read(checks/"prefix.json")
    assert prefix["firmware"]==arm and prefix["cases"]["bad_status"]["window_error"]==5
    for fault in ("none","program","done","busy","token"):
        r=read(checks/f"base-{fault}/result.json")
        assert r["passed"] and r["firmware_sha256"]==arm
        assert r["safe_return"]==r["base_restored"]==int(fault=="none")
    stop=read(temp/f"nes-trial816-stop{n}/result.json")
    assert stop["passed"] and stop["client"]==sha(client/"sink165.sfc") and len(stop["cases"])==11
    assert all(c["status"]==0xe4 and c["commits"]==c["generation"]-905 for c in stop["cases"])
    assert {(v["case"],v["generation"]) for v in stop["receipts"]}=={
        (tag,g) for tag in ("cold","bad_manifest","late_stop") for g in (906,907)}
    return dict(ARM_files={p.relative_to(checks).as_posix():sha(p) for p in sorted(checks.rglob("*.json"))},
                row_STOP=sha(temp/f"nes-trial816-stop{n}/result.json"),manual_exit=manual if n==817 else None)


def timings(temp,n,client,fw):
    measured={}
    old=read(ROOT/"analysis/output815-results.json")["phases"]
    for phase in (1,2):
        base=temp/f"nes-output809-mmc813-p{phase}"
        prior=old[str(phase)]["mmc813"]
        assert sha(base/"joint.json")==prior["hashes"]["joint.json"]
        r=replay(temp,f"mmc{n}",phase,read(base/"joint.json"),base,client)
        assert r["firmware"]==digest(fw) and r["commits"]==r["rgb_map_checked"]==66
        delta=r["dense_ms"]-prior["dense_ms"]
        ack=ms(r["last_ACK"]-prior["last_ACK"])
        assert delta<0 and ack<0,(n,phase,delta,ack)
        assert r["restored951"] and r["line951"]<=246 and r["display959"]==2
        parent=read(ROOT/"analysis/prefix813-results.json")["builds"][str(n-3)]["phases"][str(phase)]
        measured[phase]=dict(**{k:r[k] for k in ("client","dense_ms","dense_vblank","last_ACK","early951",
                             "line951","display959","intervals","raw_payload_DMA_checked","hashes")},
                             delta_dense_ms=delta,delta_ack_ms=ack,
                             delta_ack_vs_same_mode_ms=ms(r["last_ACK"]-parent["last_ACK"]))
    return measured


def package(temp):
    old=read(ROOT/"analysis/prefix813-results.json")
    archive=PROBES/"nes-prefix813/MMC813-60SEC-MMC814-LONG.zip"
    assert sha(archive)==old["ZIP_SHA256"]
    boot=read(temp/"nes-trial816-boot/result.json")
    assert boot["passed"] and len(boot["cases"])==4
    assert {(r["ROM"],r["kind"]) for r in boot["cases"]}=={
        (sha(c/"sink165.sfc"),k) for c in (TIMED,LONG) for k in ("restored","rejected")}
    files={"README-KO.txt":(ROOT/"docs/nes-mmc816-817-trial.ko.md").read_bytes()}
    proof=dict(parent_zip=sha(archive),physical=False,boot=boot,editions={})
    with ZipFile(archive) as z:
        for n,client in ((816,TIMED),(817,LONG)):
            fw=(WORK/f"link{n}/src/obj-nes-100/firmware.stm").read_bytes()
            before=PROBES/f"nes-prefix813/link{n-3}/src/obj-nes-100"
            parent_fw=(before/"firmware.stm").read_bytes()
            assert digest(parent_fw)==old["builds"][str(n-3)]["firmware"]
            assert parent_fw[32:].replace(str(n-3).encode(),str(n).encode())==fw[32:]
            assert funcs(before/"sd2snes.elf")==funcs(WORK/f"link{n}/src/obj-nes-100/sd2snes.elf")
            bi,board=signoff(temp,n,client)
            checks=qualification(temp,n,client,fw)
            phase=timings(temp,n,client,fw)
            marker=f"NES MMC3 {n}.nh1"
            names=[marker,f"/sd2snes/fpga_mmc{n}.bi3",f"/sd2snes/nes/mmc{n}.nes"]
            names.extend(f"/sd2snes/nes-{t}-mmc{n}.txt" for t in ("budget","game-last","progress"))
            assert all(name.encode()+b"\0" in fw for name in names)
            parent=str(n-3)
            prefix=("01-MMC" if n==816 else "02-MMC")+parent+"-"
            members=[k for k in z.namelist() if k.startswith(prefix)]
            assert len(members)==10
            for name in members:
                data=z.read(name)
                assert digest(data)==old["files"][name]
                if name.endswith("/firmware.stm"):
                    data=fw
                elif name.endswith(f"/fpga_mmc{parent}.bi3"):
                    data=bi
                elif name.endswith("ROM-NOT-INCLUDED.txt"):
                    data=data.replace(parent.encode(),str(n).encode())
                files[name.replace(parent,str(n))]=data
            proof["editions"][n]=dict(ARM=digest(fw),Flash_free=212992-len(fw),board=board,
                                     client=sha(client/"sink165.sfc"),ROM_free=read(client/"build.json")["physical_free_B"],
                                     guards=checks,phases=phase)
    proof["files"]={k:digest(v) for k,v in files.items()}
    files["manifest.json"]=(json.dumps(proof,indent=2)+"\n").encode()
    assert len(files)==22 and not any("restore" in k.lower() or k.lower().endswith(".nes") for k in files)
    dest=WORK/"MMC816-60SEC-MMC817-LONG.zip"
    with ZipFile(dest,"x",ZIP_DEFLATED) as z:
        for name,data in files.items():
            z.writestr(ZipInfo(name),data,compress_type=ZIP_DEFLATED)
    with ZipFile(dest) as z:
        assert z.testzip() is None and set(z.namelist())==set(files) and all(z.read(k)==v for k,v in files.items())
    proof["ZIP_SHA256"]=sha(dest)
    (ROOT/"analysis/trial816-package.json").write_text(json.dumps(proof,indent=2)+"\n",newline="\n")
    print(dest,proof["ZIP_SHA256"])


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    package(p.parse_args().temp)
