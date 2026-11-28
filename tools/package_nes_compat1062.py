"""Repackage both verified 1061 board sets with the separately linked 1062 firmware."""
import json
import struct
import zipfile
import zlib
from package_cart_state1059 import sha
from prepare_nes_compat1062 import ROOT, MEASURE, OUT

def package():
    evidence={n:json.loads((OUT/(n+".json")).read_text()) for n in ("baseline","planner","movement","loader","tetris")}
    evidence["archives"]={}
    previous=json.loads((ROOT/"analysis/nes-dq4-movement1061.json").read_text())["archives"]
    for mode,old in previous.items():
        src=MEASURE/old["zip"]
        assert sha(src.read_bytes())==old["sha256"]
        with zipfile.ZipFile(src) as z:
            entries={n:z.read("sd2snes/"+n) for n in old["files"]}
        assert {n:sha(v) for n,v in entries.items()}==old["files"]
        fw=(OUT/mode/"link/src/obj-nes-100/firmware.stm").read_bytes()
        size,crc,inv=struct.unpack_from("<III",fw,8)
        assert len(fw)==size+512 and len(fw)<=212992 and fw[:4]==b"STM3"
        assert zlib.crc32(fw[512:])==crc==inv^0xffffffff
        assert sha(fw)==evidence["loader"][mode]["sha256"]
        for name in ("progress","game-last","frame","stop"):
            assert (f"nes-{name}-debug1062".encode() in fw)==(mode=="debug")
        entries["firmware.stm"]=fw
        manifest=dict(edition=1062,profile=mode,files={n:sha(v) for n,v in entries.items()})
        dest=OUT/f"NES-1062-{mode.upper()}-SD-ROOT.zip"
        tmp=dest.with_suffix(".tmp")
        with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED) as z:
            for n,v in entries.items():z.writestr("sd2snes/"+n,v)
            z.writestr("manifest.json",json.dumps(manifest,indent=2))
            z.write(ROOT/"docs/nes-compat1062.ko.md","README-KO.txt")
        with zipfile.ZipFile(tmp) as z:
            assert z.testzip() is None
            assert {n:sha(z.read("sd2snes/"+n)) for n in entries}==manifest["files"]
        tmp.replace(dest)
        evidence["archives"][mode]=dict(zip=dest.name,sha256=sha(dest.read_bytes()),firmware_bytes=len(fw),**manifest)
    (ROOT/"analysis/nes-compat1062.json").write_text(json.dumps(evidence,indent=2)+"\n")

if __name__=="__main__":
    package()
