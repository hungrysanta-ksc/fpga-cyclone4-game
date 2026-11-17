"""Bind the final linker output, fitted image, native row results and STOP guards before packaging."""
import json
import re
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
from package_nes_opening818 import ROOT, PROBES, cost, sha, digest, read
from prepare_nes_opening818 import ADVENTURE_SHA

def package(temp):
    work=PROBES/"nes-mask820"
    archive=PROBES/"nes-opening818/MMC819-ADVENTURE-MMC818-TSUBASA-60SEC.zip"
    old=read(ROOT/"analysis/opening818-results.json")
    assert sha(archive)==old["ZIP_SHA256"]
    board=temp/"nes-trial816-board820b"
    c=cost(board)
    assert c["SOF"] and c["STA"] and min(c["slack_ns"].values())>=0
    assert c["unconstrained"]==old["board"]["unconstrained"]
    summary=(board/"output_files/board.sta.summary").read_text()
    tns=re.findall(r"^TNS\s+: ([-.\d]+)",summary,re.M)
    assert len(tns)==summary.count("Type  :")>=40 and all(float(n)==0 for n in tns)
    client=PROBES/"nes-output815/client/sink165.sfc"
    rom=client.read_bytes()
    assert bytes.fromhex((board/"sink-program.hex").read_text())==rom[:5056]+rom[-64:]
    image=read(temp/"nes-mask820-packed/image.json")
    bi=(temp/"nes-mask820-packed/fpga_mmc820.bi3").read_bytes()
    assert image["SOF"]==c["reports"]["board.sof"] and image["BI3"]==digest(bi) and image["programmer"]["passed"]
    fw=(work/"link820b/src/obj-nes-100/firmware.stm").read_bytes()
    assert len(fw)<=212992
    for n in ["nes-budget-mmc820.txt","nes-progress-mmc820.txt","nes-game-last-mmc820.txt","mmc820.nes","fpga_mmc820.bi3","NES MMC3 820.nh1"]:
        assert n.encode()+b"\0" in fw
    guards=read(work/"guards.json")
    assert guards["protocol"]["ACK"]["corrupt_bits"]==152 and guards["protocol"]["firmware"]==digest(fw)
    menu=read(work/"check_nes_menu533.json")
    base=read(work/"base/result.json")
    limit=read(work/"check_nes_longrun692.json")
    bins=read(work/"check_nes_windows518.json")
    assert menu["firmware"]==base["firmware_sha256"]==limit["firmware"]==bins["firmware_SHA256"]==digest(fw)
    assert menu["rows"]["normal"]["released"] and base["safe_return"] and base["base_restored"] and limit["passed"]
    assert bins["layout"]=="trimmed" and bins["unfinished_excluded"] and read(work/"obj.json")["service_stop_pending"]
    stop=read(temp/"nes-mask820-stop/result.json")
    assert stop["passed"] and stop["client"]==sha(client) and len(stop["cases"])==11 and len(stop["receipts"])==6
    assert all(r["status"]==228 and r["commits"]==r["generation"]-905 for r in stop["cases"])
    source=read(temp/"nes-mask820-continuous03/result.json")
    assert source["frames"]==3600 and source["split"]==2016 and not source["bg_mismatch_frames"]
    dots=(temp/"nes-mask820-dots/dots.log").read_text(errors="replace")
    assert "PASS820 mask replay" in dots and all(f"dot={d} requested=1 first_over=-1 errors=00 valid=1" in dots for d in range(91,109))
    pictures=[]
    for plans,trace,render in (("pixels.json","game","snesdemo"),("crosspixels.json","crossing","snescross")):
        capture=read(temp/f"nes-mask820-{trace}/capture.json")
        ppu=read(temp/f"nes-mask820-{render}/result.json")
        assert capture["rom"]==ADVENTURE_SHA and sorted(capture["sampled"])==ppu["frames"] and ppu["mismatches"]==0
        for row in read(work/plans):
            assert row["frame"] in ppu["frames"] and row["errors"]==0
            assert row["raw"]==([0] if row["frame"]==1500 else [0,184])
            pictures.append({k:v for k,v in row.items() if k!="rows"})
    # Anchor the asynchronous PNG capture to direct end-of-frame PPU buffers,
    # including the last frame and all frames with a sprite on the split.
    from PIL import Image
    import io
    import struct
    anchors={r["frame"] for r in pictures}
    with (temp/"nes-mask820-continuous03/normal/frames.bin").open("rb") as frames:
        for frame in range(1,3601):
            n,=struct.unpack("<I",frames.read(4))
            png=frames.read(n)
            if frame in anchors:
                trace="crossing" if 2095<=frame<=2098 or frame==2130 else "game"
                raw=(temp/f"nes-mask820-{trace}/frame-{frame}.rgb").read_bytes()
                assert Image.open(io.BytesIO(png)).convert("RGB").tobytes()==raw,frame
        assert not frames.read(1)
    assert 3600 in {r["frame"] for r in pictures} and set(source["crossing"])<={r["frame"] for r in pictures}
    evidence=dict(edition=820,arm_sha256=digest(fw),arm_bytes=len(fw),flash_free=212992-len(fw),rom_sha256=ADVENTURE_SHA,
        client_sha256=sha(client),board={k:c[k] for k in ("LE","LAB","M9K","slack_ns","unconstrained","reports")},
        image_sha256=digest(bi),parent_zip=sha(archive),reference=source,display=pictures,native_ppu_pixels=len(pictures)*224*256,
        stop_boundaries=len(stop["cases"]),consume_cases=len(stop["receipts"]),corrupt_ACK_bits=152,
        timer_verified=True,base_return_verified=True,physical=False,
        scope="Reference game continuous 3600 NES frames; all observed split dots replayed on fitted raster. Ten cold collector/export and ARM plans displayed by an independent SNES DMA/HDMA driver. Production client STOP/manifest checked separately; continuous cartridge transport and physical FPS pending.")
    prefix="01-MMC819-ADVENTURE-60SEC-SD-ROOT/"
    dest_prefix="MMC820-ADVENTURE-60SEC-SD-ROOT/"
    files={"README-KO.txt":(ROOT/"docs/nes-mmc820-trial.ko.md").read_bytes()}
    with ZipFile(archive) as z:
        for k in z.namelist():
            if not k.startswith(prefix):continue
            data=z.read(k)
            assert digest(data)==old["files"][k]
            if k.endswith("/firmware.stm"):data=fw
            if k.endswith("/fpga_mmc819.bi3"):data=bi
            if k.endswith("/ROM-NOT-INCLUDED.txt"):data=data.replace(b"mmc819.nes",b"mmc820.nes")
            files[dest_prefix+k[len(prefix):].replace("819","820")]=data
    assert len(files)==11 and not any(k.lower().endswith(".nes") or "restore" in k.lower() for k in files)
    evidence["files"]={k:digest(v) for k,v in files.items()}
    files["manifest.json"]=(json.dumps(evidence,indent=2)+"\n").encode()
    dest=work/"MMC820-ADVENTURE-60SEC-SD-ROOT.zip"
    with ZipFile(dest,"x") as z:
        for k,v in files.items():z.writestr(ZipInfo(k),v,compress_type=ZIP_DEFLATED)
    with ZipFile(dest) as z:
        assert z.testzip() is None and all(z.read(n)==v for n,v in files.items())
    evidence["ZIP_SHA256"]=sha(dest)
    (ROOT/"analysis/mask820-results.json").write_text(json.dumps(evidence,indent=2)+"\n",newline="\n")
    print(dest,evidence["ZIP_SHA256"])

if __name__=="__main__":
    package(Path(sys.argv[1]))
