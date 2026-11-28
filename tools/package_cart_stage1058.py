"""Build the paired SD images from the closed board routes and the final ARM."""
import csv
import json
import struct
import zipfile
import zlib
from check_carts1056 import headers
import check_carts1056
from package_nes_kirby1027 import programmer, timing
from package_nes_carts1056 import digest, ROOT
from prepare_cart_stage1058 import BASE, OUT


def package():
    for version, tb, marker in ((1057,"prerender1058_tb","PASS_PRERENDER1058"),
                               (1058,"prerender1058_tb","PASS_PRERENDER1058"),
                               (1058,"cart_stage1057_tb","PASS1057"),
                               (1058,"page_receipt1058_tb","PASS_PAGE1058")):
        log=(OUT/f"{version}-{tb}.log").read_text()
        assert "# "+marker in log and "Errors: 0," in log
    report=json.loads((OUT/"stage-arm.json").read_text())
    assert report["warm_bank_retained"]=={"255":0,"97":76}
    old=json.loads((ROOT/"analysis/nes-carts1057.json").read_text())
    check_carts1056.OUT=OUT
    ref=json.loads((BASE.parent/"nes-carts1056/reference.json").read_text())
    proof=headers("debug",ref)
    boards={}
    changes={}
    for mapper in (7,21):
        route=OUT/f"fit-{mapper}"
        board=timing(route)
        if mapper==7:
            with (route/"sram.tsv").open() as stream:
                paths=list(csv.DictReader(stream,delimiter="\t"))
            corners={p["corner"] for p in paths}
            assert len(corners)==3 and all({(p["group"],p["check"]) for p in paths if p["corner"]==c}==
                   {("input","setup"),("input","hold"),("output","setup"),("output","hold")} for c in corners)
            board["sram_pin_paths"]=len(paths)
        changes[f"nes-m{mapper}.bi3"], fitted=programmer(route,route,1058)
        boards[mapper]=dict(board,rbf_sha256=fitted["rbf_sha256"])

    results={}
    for profile,prior in old["archives"].items():
        original=BASE/prior["zip"]
        assert digest(original.read_bytes())==prior["sha256"]
        with zipfile.ZipFile(original) as z:
            files={n:z.read("sd2snes/"+n) for n in prior["files"]}
        assert {n:digest(buf) for n,buf in files.items()}==prior["files"]
        files.update(changes)
        if profile=="debug":
            fw=(OUT/"debug/link/src/obj-nes-100/firmware.stm").read_bytes()
            size,crc,inv=struct.unpack_from("<III",fw,8)
            assert fw[:4]==b"STM3" and size+512==len(fw)<=212992 and crc==zlib.crc32(fw[512:])==inv^0xffffffff
            assert proof==dict(checked=20,sha256=digest(fw))
            assert b"debug1057" not in fw and all(f"nes-{n}-debug1058".encode() in fw for n in ("frame","stop","game-last","progress"))
            files["firmware.stm"]=fw
        manifest=dict(edition=1058,profile=profile,files={n:digest(v) for n,v in files.items()},firmware_bytes=len(files["firmware.stm"]))
        target=OUT/f"NES-1058-{profile.upper()}-SD-ROOT.zip"
        tmp=target.with_suffix(".tmp")
        with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED) as z:
            for name,buf in files.items():z.writestr("sd2snes/"+name,buf)
            z.writestr("manifest.json",json.dumps(manifest,indent=2))
            z.write(ROOT/"docs/nes-carts1058.ko.md","README-KO.txt")
        with zipfile.ZipFile(tmp) as z:
            assert z.testzip() is None and all(digest(z.read("sd2snes/"+n))==h for n,h in manifest["files"].items())
        tmp.replace(target)
        results[profile]=dict(manifest,zip=target.name,sha256=digest(target.read_bytes()))
    (ROOT/"analysis/nes-carts1058.json").write_text(json.dumps(dict(boards=boards,archives=results,stage=report),indent=2)+"\n")

if __name__=="__main__":
    package()
