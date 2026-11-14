"""Verify the linked frame logger and build the MMC770/771/772 SD-root handoff."""
import argparse
import csv
import struct
import zipfile
import zlib
from collections import defaultdict
from pathlib import Path

from analyze_nes_output768 import PROBES, ROOT, csv_groups, one, read, sha
from analyze_nes_status689 import cost
from package_nes_trial704 import decode, digest, save
from read_nes_frame769 import decode as frame_rows


def verify_records(directory, reference, firmware, client):
    j=read(directory/"joint.json")
    assert j["passed"] and j["commits"]==j["map_WRAM_VRAM_verified"]==66
    assert j["firmware_SHA256"]==firmware and j["client_SHA256"]==client
    cpu=csv_groups(directory/"window.csv")
    ev=read(directory/"events.json")
    marks=defaultdict(list)
    with (directory/"marks769.csv").open() as f:
        for g,a,v,frame,line,clock in csv.reader(f):
            marks[int(g)].append(tuple(map(int,(a,v,frame,line,clock))))
    rows=list(frame_rows((directory/"registered769.bin").read_bytes(),
                         "frame769=1\ntick_ms=10\nrows=66\ndropped=0"))
    offsets=set()
    for g,row in enumerate(rows,905):
        assert row["valid"] and row["generation"]==g
        m=marks[g];assert [x[0] for x in m]==[0x7004,0x7005,0x7006,0x7006,0x7007]
        assert m[0][1]==g%256 and m[2][1]==255
        seal=[x for x in cpu[g] if x["op"]==3]
        points=[one(seal,"seal"),next(x for x in seal if x["event"]=="ppu_dma"),one(seal,"ack")]
        for mark,point,label in zip((m[1],m[3],m[4]),points,("seal_vb","dma_vb","ack_vb"),strict=True):
            assert row[label]==mark[1] and mark[2]==point["frame"],(g,label)
            offsets.add((point["frame"]-mark[1])%256)
        for pat in ("frame-{}.rgb","map-{}.bin","expected-{}.bin"):
            assert (directory/pat.format(g)).read_bytes()==(reference/pat.format(g)).read_bytes()
        events=[x for x in ev if x["generation"]==g]
        a=one(events,"output_enter531")["clock"];b=one(events,"output_return531")["clock"]
        if not row["saturated"]:
            for op in ("E0","E8"):
                n=sum(x.get("opcode")==("0x"+op.lower()) and a<=x["start"]<=b for x in events)
                assert row["output_"+op]==n,(g,op,row["output_"+op],n)
    assert len(offsets)==1
    return dict(frames=len(rows), NMI_offset=offsets.pop(),physical=False,window="forced logger tick only",
                joint=sha(directory/"joint.json"),records=sha(directory/"registered769.bin"),
                marks=sha(directory/"marks769.csv"), checked_marks=3*len(rows),frame969=rows[64],
                compare_RGB_WRAM_VRAM=66, saturated=sum(r["saturated"] for r in rows))


def package(temp, out, report):
    work=PROBES/"nes-output769"
    prior=read(ROOT/"analysis/trial767-package.json")
    original=PROBES/"nes-timer767/MMC767-60SEC-MMC766-LONG.zip"
    assert sha(original)==prior["ZIP_SHA256"]
    entries={"시험안내.txt":(ROOT/"docs/nes-mmc770-trial.ko.md").read_bytes()}
    common={}
    with zipfile.ZipFile(original) as z:
        for name in ("fpga_base.bi3","m3nu.bin"):
            path="01-MMC767-B-60SEC-SD-ROOT/sd2snes/"+name
            data=z.read(path)
            assert digest(data)==prior["files"][path]
            common["sd2snes/"+name]=data
    wire=read(temp/"nes-wire769-02/result.json")
    assert wire["passed"]
    proof=read(ROOT/"analysis/bg707-verification.json")
    variants={};boards={}
    for number in (770,771,772):
        boardno=min(number,771)
        board=temp/f"nes-probe{boardno}-timing"
        client=work/("clientA" if number==770 else "clientB")
        client_hash=sha(client/"sink165.sfc")
        for name,h in {**proof["inputs"]["base"],**proof["inputs"]["changed"]}.items():
            if name not in ("nes_rom_spi.sv","nes_screen_status151.sv","nes_run_observer134.sv","sink-program.hex"):
                assert sha(board/name)==h,name
        for name,k in (("nes_rom_spi.sv","loader"),("nes_screen_status151.sv","screen")):
            assert sha(board/name)==wire[k]
        fwdir=work/f"arm{number}b";obj=fwdir/"src/obj-nes-100"
        fw=(obj/"firmware.stm").read_bytes();fwh=digest(fw)
        length,crc,inv=struct.unpack_from("<III",fw,8)
        assert fw[:4]==b"STM3" and length+512==len(fw)<=212992 and zlib.crc32(fw[512:])==crc and inv^crc==0xffffffff
        guard=read(work/f"final{number}.json")
        assert guard["firmware"]==fwh and guard["passed"] and guard["windows"]==[2,2]
        assert f"/sd2snes/nes-frame-mmc{number}.bin" in guard["modeled_FatFS_files"]
        menu=read(work/f"menu{number}b.json")
        assert menu["firmware"]==fwh and menu["marker_cases"]==4
        assert all(v["prepared"]==v["released"]==int(k=="normal") for k,v in menu["rows"].items())
        for fault in ("none","busy","token","program","done"):
            rec=read(work/f"base{number}b-{fault}/result.json")
            assert rec["passed"] and rec["firmware_sha256"]==fwh and rec["base_restored"]==rec["safe_return"]==int(fault=="none")
        if number!=770:
            credit=read(work/f"credit{number}b.json")
            assert credit["firmware"]==fwh and credit["seal_receipts"]["corrupt_bits"]==152
        rom=read(temp/f"nes-rom{boardno}-01/result.json")
        assert rom["bytes"]==5120 and rom["client"]==client_hash and rom["program"]==sha(board/"sink-program.hex")==sha(client/"sink-program.hex")
        im=temp/f"nes-image{boardno}-01";image=read(im/"image.json");bi=(im/f"fpga_mmc{boardno}.bi3").read_bytes()
        assert image["programmer"]["passed"] and image["SOF"]==sha(board/"output_files/board.sof")
        assert digest(decode(bi))==image["RBF"] and digest(bi)==image["BI3"]
        if number!=772:
            c=cost(board)
            assert c["SOF"] and c["STA"] and c["LAB"]<=963 and min(c["slack_ns"].values())>0
            assert c["unconstrained"]==proof["boards"]["D"]["unconstrained"]
            paths={k:min(float(x["slack"]) for x in c[k]) for k in ("io612.tsv","reader661.tsv","word660.tsv")}
            assert min(paths.values())>0
            schedule=verify_records(temp/f"nes-frame{number}-closed4-p1",temp/"nes-cost768-763-p1-ext",fwh,client_hash)
            boards[boardno]={k:c[k] for k in ("LE","LAB","M9K","reports","slack_ns","unconstrained")}
            boards[boardno].update(paths=paths,rom_bus=rom,image=image["BI3"],observer=sha(board/"nes_run_observer134.sv"))
        else:
            schedule="same fitted board and 65816 as 771, separate linked ARM timer/credit/menu tests"
        cfg=f"sd2snes/fpga_mmc{number}.bi3";game=f"sd2snes/nes/mmc{number}.nes";marker=f"NES MMC3 {number}.nh1"
        prefix=f"{number-769:02}-MMC{number}-"+("A" if number==770 else "B")+"-"+("LONG" if number==772 else "60SEC")+"-SD-ROOT/"
        logs=[f"sd2snes/nes-{k}-mmc{number}.txt" for k in ("progress","budget","game-last")]+[f"sd2snes/nes-frame-mmc{number}.bin"]
        for name in [marker,*("/"+x for x in [cfg,game,*logs])]:
            assert name.encode()+bytes(1) in fw,name
        for name,data in {marker:b"",cfg:bi,**common,"sd2snes/firmware.stm":fw,"sd2snes/nes/ROM-NOT-INCLUDED.txt":("Copy your usual ROM to "+game+"\n").encode()}.items():
            entries[prefix+name]=data
        variants[number]=dict(firmware=fwh,ELF=sha(obj/"sd2snes.elf"),Flash_B=len(fw),BSS_B=int((fwdir/"size.log").read_text().splitlines()[-1].split()[2]),guard=guard,schedule=schedule)
    with zipfile.ZipFile(out,"x",zipfile.ZIP_DEFLATED) as z:
        for name,data in entries.items():z.writestr(name,data)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None and set(entries)==set(z.namelist()) and all(z.read(k)==v for k,v in entries.items())
    save(report,dict(variants=variants,boards=boards,wire=wire,physical=False,ZIP_SHA256=sha(out),files={k:digest(v) for k,v in entries.items()}))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("temp","out","report"):p.add_argument(k,type=Path)
    a=p.parse_args();package(a.temp,a.out,a.report)
