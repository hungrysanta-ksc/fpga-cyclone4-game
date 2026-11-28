"""Bind the diagnostic fix to the routed 1059 boards and verify both archives."""
import json
import re
from pathlib import Path
from statistics import median
import struct
import zipfile
import zlib
from prepare_cart_debug1060 import OUT, PRIOR
from prepare_nes_carts1056 import ROOT
from package_cart_state1059 import sha


def measurements():
    result={}
    for edition in (1058,1059):
        for frame in (Path.home()/"Downloads").glob(f"nes-frame-debug{edition}-*.bin"):
            data=frame.read_bytes()
            text=frame.with_name(frame.name.replace("frame","game-last")).with_suffix(".txt").read_text()
            rec=dict(re.findall(r"(\w+)=(\w+)",text))
            if rec["id"] not in ("82","83"):
                continue
            assert all(rec[k]=="1" for k in ("start","stop","base")) and rec["err"]==rec["rom"]=="0"
            magic,ver,_,count,_,_,stride,cap=struct.unpack_from("<8H",data)
            assert (magic,ver,stride,cap)==(0x9001,edition,60,80) and count<=cap
            rows=[struct.unpack_from("<6H4B",data,16+i*stride) for i in range(count)]
            tail=[r for r in rows if r[0]>=5500 and r[8]&3==3]
            result[f"{edition}-{rec['id']}"]=dict(display1=int(rec["w1"]),display2=int(rec["w2"]),
                displayed55=struct.unpack_from("<H",data,4816)[0],samples=len(tail),
                dirty_map_zero=sum(r[7]==0 for r in tail),ack_ms=round(median((r[3]-r[4])*512/84000 for r in tail),2))
    assert len(result)==4
    return result


def package():
    prior=json.loads((ROOT/"analysis/nes-carts1059.json").read_text())["archives"]
    result={}
    for edition,archive in prior.items():
        base=PRIOR/archive["zip"]
        assert sha(base.read_bytes())==archive["sha256"]
        with zipfile.ZipFile(base) as z:
            files={n:z.read("sd2snes/"+n) for n in archive["files"]}
        assert {n:sha(v) for n,v in files.items()}==archive["files"]
        fw=(OUT/edition/"link/src/obj-nes-100/firmware.stm").read_bytes()
        size,crc,inv=struct.unpack_from("<III",fw,8)
        assert fw[:4]==b"STM3" and size+512==len(fw)<=212992 and crc==zlib.crc32(fw[512:])==inv^0xffffffff
        if edition=="debug":
            assert all(f"nes-{part}-debug1060".encode() in fw for part in ("progress","frame","game-last","stop"))
        else:
            assert files["firmware.stm"]==fw
        files["firmware.stm"]=fw
        manifest=dict(edition=1060,profile=edition,files={n:sha(v) for n,v in files.items()})
        target=OUT/f"NES-1060-{edition.upper()}-SD-ROOT.zip"
        tmp=target.with_suffix(".tmp")
        with zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED) as z:
            for n,v in files.items():z.writestr("sd2snes/"+n,v)
            z.writestr("manifest.json",json.dumps(manifest,indent=2))
            z.write(ROOT/"docs/nes-carts1060.ko.md","README-KO.txt")
        with zipfile.ZipFile(tmp) as z:
            assert z.testzip() is None
            assert {n:sha(z.read("sd2snes/"+n)) for n in files}==manifest["files"]
        tmp.replace(target)
        result[edition]=dict(zip=target.name,sha256=sha(target.read_bytes()),firmware_bytes=len(fw),**manifest)
    evidence=dict(archives=result,physical=measurements(),
                  reference_oam=json.loads((OUT/"battle-oam.json").read_text()))
    (ROOT/"analysis/nes-carts1060.json").write_text(json.dumps(evidence,indent=2)+"\n")


if __name__=="__main__":
    package()
