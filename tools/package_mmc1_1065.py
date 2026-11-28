"""Package only the board routes, ARM links and file layouts exercised in 1065."""
import csv
import json
import re
import struct
import zipfile
import zlib
from package_cart_state1059 import sha
from package_nes_kirby1027 import programmer,timing
from package_nes_headers1064 import checked_sim
from prepare_sxrom1065 import ROOT,OUT,PREVIOUS

def package(zelda_route="fit-zelda1"):
    report={"boards":{},"archives":{}}
    report["launch"]=json.loads((OUT/"fat-launch.json").read_text())
    assert report["launch"]["ff12"]["menu_released"] and report["launch"]["ff12"]["stage_blocks"]==1024
    report["zelda_launch"]=json.loads((OUT/"fat-zelda.json").read_text())
    assert all(v["stage_blocks"]==512 and v["menu_released"] for v in report["zelda_launch"].values())
    assert json.loads((OUT/"fat-state.json").read_text())["checkpoint"]==45840
    checked_sim(OUT/"resume-sxrom-vsim.log","PASS cartridge CPU resume 64 fetches and 5730 words")
    title=checked_sim(OUT/"title-fix/resume-1-vsim.log","PASS opening capture trace")
    assert "valid=0" not in title and "TITLE" in title
    baseline=checked_sim(OUT/"resume-1-vsim.log","PASS opening capture trace")
    rejected=re.findall(r"^# TITLE\s+(\d+) valid=0 errors=([0-9a-f]+)",baseline,re.M)
    assert [int(f) for f,e in rejected]==list(range(19,32))
    assert all(int(e,16)&0x2000 for f,e in rejected)
    report["baseline_obj_overflow_fields"]=[int(f) for f,e in rejected]
    report["sxrom_pin_trace"]={}
    for n in (1,2):
        pins=checked_sim(OUT/f"pins-{n}.log","PASS SXROM")
        writes,rom,ram=map(int,re.search(r"PASS SXROM writes=(\d+) ROM=(\d+) RAM=(\d+)",pins).groups())
        report["sxrom_pin_trace"][f"FF{n}"]=dict(mapper_writes=writes,prg_samples=rom,wram_samples=ram)
    report["sxrom_state"]=dict(battery_bytes=32768,checkpoint_bytes=45840,restored_cpu_reads=64)
    checked_sim(OUT/"sx-loader.log", "PASS FF3 loader 524288 accepted bytes, START and retained STOP length")
    from check_zelda_title1065 import main as check_title
    check_title()
    report["opening"]=json.loads((OUT/"title-planner.json").read_text())
    updates={}
    for name,route in (("nes-m1.bi3",zelda_route),("nes-sx.bi3","fit-sx1")):
        folder=OUT/route
        silicon=timing(folder)
        with (folder/"sram.tsv").open() as f:rows=list(csv.DictReader(f,delimiter="\t"))
        assert len({r["corner"] for r in rows})==3
        for corner in {r["corner"] for r in rows}:
            assert {(r["group"],r["check"]) for r in rows if r["corner"]==corner}=={("input","setup"),("input","hold"),("output","setup"),("output","hold")}
        updates[name],proof=programmer(folder,folder,1065)
        report["boards"][name]=dict(**silicon,rbf_sha256=proof["rbf_sha256"])
    prev=json.loads((ROOT/"analysis/nes-mmc1-board1064.json").read_text())
    for mode,source in prev["archives"].items():
        old=PREVIOUS/source["zip"]
        assert sha(old.read_bytes())==source["sha256"]
        with zipfile.ZipFile(old) as z:
            files={n:z.read("sd2snes/"+n) for n in source["files"]}
        assert {n:sha(v) for n,v in files.items()}==source["files"]
        fw=(OUT/mode/"link/src/obj-nes-100/firmware.stm").read_bytes()
        length,crc,inv=struct.unpack_from("<III",fw,8)
        assert fw[:4]==b"STM3" and len(fw)==length+512<=212992 and zlib.crc32(fw[512:])==crc==inv^0xffffffff
        for kind in ("game-last","frame","progress","stop"):
            assert (f"nes-{kind}-debug1065".encode() in fw)==(mode=="debug")
        files.update(updates);files["firmware.stm"]=fw
        manifest=dict(edition=1065,profile=mode,files={n:sha(v) for n,v in files.items()})
        target=OUT/f"NES-1065-{mode.upper()}-SD-ROOT.zip"
        tmp=target.with_suffix(".tmp")
        with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED) as z:
            for n,v in files.items():z.writestr("sd2snes/"+n,v)
            z.write(ROOT/"docs/nes-mmc1-1065.ko.md","README-KO.txt")
            z.writestr("manifest.json",json.dumps(manifest,indent=2))
        with zipfile.ZipFile(tmp) as z:
            assert z.testzip() is None and {n:sha(z.read("sd2snes/"+n)) for n in files}==manifest["files"]
        tmp.replace(target)
        report["archives"][mode]=dict(zip=target.name,bytes=len(fw),sha256=sha(target.read_bytes()),**manifest)
    (ROOT/"analysis/nes-mmc1-1065.json").write_bytes((json.dumps(report,indent=2)+"\n").encode())

if __name__=="__main__":package()
