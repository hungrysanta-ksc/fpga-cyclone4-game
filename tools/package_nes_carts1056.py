"""Gate the 1056 board images and both installation archives."""
import hashlib
import json
import re
import struct
import zipfile
import zlib

from package_nes_kirby1027 import programmer, timing
from prepare_nes_carts1056 import CARTS, ROOT, OUT

def digest(data):
    return hashlib.sha256(data).hexdigest()

def package():
    prior=json.loads((ROOT/"analysis/nes-pair1055.json").read_text())["archives"]
    reference=json.loads((OUT/"reference.json").read_text())
    handoff=json.loads((OUT/"handoff.json").read_text())
    guards=json.loads((OUT/"guards.json").read_text())
    assert guards["battery_roundtrip_bytes"]==8192
    assert len(reference)==4 and len(handoff)==6
    assert all(row["commands"]==[0x60,0x62,0x63,0x64] and row["menu_released"] for row in handoff.values())
    images={}
    boards={}
    for game,ref in reference.items():
        m=ref["mapper"]
        assert m in CARTS and m not in boards
        assert len(ref["samples"])==15 and len({row.split()[-1] for row in ref["samples"]})>1
        sim=OUT/f"sim-{m}"
        address_check=re.search(rf"PASS mapper={m} writes=(\d+) reference_addresses=240",(sim/"result.log").read_text())
        boot=re.search(rf"PASS CPU mapper={m} vector=[^\r\n]+",(sim/"boot-vsim.log").read_text())
        assert address_check and boot,game
        route=OUT/f"final-{m}"
        board=timing(route)
        if m in (5,7):
            pins=[line.split("\t") for line in (route/"sram.tsv").read_text().splitlines()[1:]]
            corners={row[0] for row in pins}
            assert len(corners)==3
            for corner in corners:
                assert {(r[1],r[2]) for r in pins if r[0]==corner}=={
                    ("input","setup"),("input","hold"),("output","setup"),("output","hold")}
            board["sram_pin_paths"]=len(pins)
        image,p=programmer(route,route,1056)
        images[f"nes-m{m}.bi3"]=image
        boards[m]=dict(board,game=game,rom_sha256=ref["sha256"],rbf_sha256=p["rbf_sha256"],
                       mapper_writes=int(address_check[1]),compared_addresses=240,cpu_boot=boot[0])
    archives={}
    for profile,old in prior.items():
        base=OUT.parent/"nes-pair1055"/old["zip"]
        assert digest(base.read_bytes())==old["sha256"]
        fw=(OUT/profile/"link/src/obj-nes-100/firmware.stm").read_bytes()
        assert guards[profile]==dict(checked=20,sha256=digest(fw))
        size,crc,inverse=struct.unpack_from("<III",fw,8)
        assert fw[:4]==b"STM3" and size+512==len(fw)<=212992
        assert zlib.crc32(fw[512:])==crc==(inverse^0xffffffff)
        for name in images:
            assert ("/sd2snes/"+name).encode()+b"\0" in fw
        for prefix in (b"nes-progress-",b"nes-frame-",b"nes-game-last-"):
            assert (prefix+b"debug1056" in fw)==(profile=="debug")
            if profile=="release":
                assert prefix not in fw
        contents={}
        with zipfile.ZipFile(base) as archive:
            for name,h in old["files"].items():
                data=archive.read("sd2snes/"+name)
                assert digest(data)==h
                contents[name]=fw if name=="firmware.stm" else data
        contents.update(images)
        files={n:digest(data) for n,data in contents.items()}
        manifest=dict(edition=1056,profile=profile,files=files,firmware_bytes=len(fw))
        target=OUT/f"NES-1056-{profile.upper()}-SD-ROOT.zip"
        temp=target.with_suffix(".tmp")
        with zipfile.ZipFile(temp,"w",zipfile.ZIP_DEFLATED) as archive:
            for name,data in contents.items():
                archive.writestr("sd2snes/"+name,data)
            archive.writestr("manifest.json",json.dumps(manifest,indent=2))
            archive.writestr("README-KO.txt",(ROOT/"docs/nes-carts1056.ko.md").read_bytes())
        with zipfile.ZipFile(temp) as archive:
            assert archive.testzip() is None and len(archive.namelist())==len(contents)+2
            for name,h in files.items():
                assert digest(archive.read("sd2snes/"+name))==h
        temp.replace(target)
        archives[profile]=dict(manifest,zip=target.name,sha256=digest(target.read_bytes()))
    report=dict(boards=boards,archives=archives,release_handoff=handoff,guards=guards,physical_1056=False)
    (ROOT/"analysis/nes-carts1056.json").write_text(json.dumps(report,indent=2)+"\n")

if __name__=="__main__":
    package()
