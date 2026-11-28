"""Package only the routed boards bound to the checked final 1059 links."""
import csv
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile
import zlib
from prepare_cart_state1059 import BASE, OUT
from prepare_nes_carts1056 import ROOT
from package_nes_kirby1027 import programmer, timing


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_log(name,pattern):
    text=(OUT/name).read_text(errors="replace")
    assert re.search(pattern,text,re.M) and re.search(r"^# Errors: 0,",text,re.M),name


def package():
    prior=json.loads((ROOT/"analysis/nes-carts1058.json").read_text())
    results=json.loads((OUT/"vrc/checks.json").read_text())
    assert results["states"]==[21264,22280] and results["battery"]==8192 and results["vrc_state"]==21264
    for m,words in ((7,2658),(5,2785),(21,2658)):
        check_log(f"resume-{m}-vsim.log",rf"^# PASS cartridge CPU resume 64 fetches and {words} words")
        check_log(f"mapper-{m}.test.log",rf"^# PASS mapper {m} capture")
    for version,count in ((1058,3072),(1059,1536)):
        check_log(f"mirror-{version}.test.log",rf"^# MIRROR_BYTES {count}$")
    check_log("demand1059_tb.log",r"^# PASS VRC4 BG/OBJ")
    check_log("prerender1058_tb.log",r"^# PASS_PRERENDER1058")
    replace={}
    results["boards"]={}
    for m in (5,7,21):
        route=OUT/("fit-21-demand" if m==21 else f"fit-{m}")
        record=timing(route)
        if m!=21:
            with (route/"sram.tsv").open() as f:rows=list(csv.DictReader(f,delimiter="\t"))
            corners={r["corner"] for r in rows}
            assert len(corners)==3 and all({(r["group"],r["check"]) for r in rows if r["corner"]==corner}==
                       {("input","setup"),("input","hold"),("output","setup"),("output","hold")} for corner in corners)
        bi,proof=programmer(route,route,1059)
        replace[f"nes-m{m}.bi3"]=bi
        record["rbf_sha256"]=proof["rbf_sha256"]
        results["boards"][str(m)]=record
    results["archives"]={}
    results["arm_handoff"]=json.loads((OUT/"vrc/handoff.json").read_text())
    for edition,archive in prior["archives"].items():
        base=BASE/archive["zip"]
        assert sha(base.read_bytes())==archive["sha256"]
        with zipfile.ZipFile(base) as z:
            files={n:z.read("sd2snes/"+n) for n in archive["files"]}
        assert {n:sha(v) for n,v in files.items()}==archive["files"]
        fw=(OUT/"vrc"/edition/"link/src/obj-nes-100/firmware.stm").read_bytes()
        size,crc,inv=struct.unpack_from("<III",fw,8)
        assert fw[:4]==b"STM3" and size+512==len(fw)<=212992 and crc==zlib.crc32(fw[512:])==inv^0xffffffff
        assert results["header"][edition]==dict(checked=20,sha256=sha(fw))
        if edition=="debug":
            assert all(f"nes-{n}-debug1059".encode() in fw for n in ("progress","game-last","frame","stop"))
        files.update(replace)
        files["firmware.stm"]=fw
        target=OUT/f"NES-1059-{edition.upper()}-SD-ROOT.zip"
        manifest=dict(edition=1059,profile=edition,files={n:sha(v) for n,v in files.items()})
        tmp=target.with_suffix(".tmp")
        with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED) as z:
            for n,v in files.items():z.writestr("sd2snes/"+n,v)
            z.writestr("manifest.json",json.dumps(manifest,indent=2))
            z.write(ROOT/"docs/nes-carts1059.ko.md","README-KO.txt")
        with zipfile.ZipFile(tmp) as z:
            assert z.testzip() is None and all(sha(z.read("sd2snes/"+n))==h for n,h in manifest["files"].items())
        tmp.replace(target)
        results["archives"][edition]=dict(zip=target.name,firmware_bytes=len(fw),sha256=sha(target.read_bytes()),**manifest)
    (ROOT/"analysis/nes-carts1059.json").write_text(json.dumps(results,indent=2)+"\n")


if __name__=="__main__":package()
