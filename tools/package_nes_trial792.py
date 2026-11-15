"""Release only the two measured links with passing capture, DMA, STOP and menu proofs."""
import argparse
import json
import struct
import zipfile
import zlib
from pathlib import Path

from analyze_nes_status689 import cost
from analyze_nes_boundary788 import LIMIT, RANGES, ms, result
from package_nes_trial704 import decode, digest, read, save, sha
from prepare_nes_trial792 import BASE, CLIENT, OUT, ROOT, PROBES


def phase(temp, n, p, client, fw):
    folder = temp / f"nes-trial792-{n}-p{p}"
    r = result(folder,temp/f"nes-range778-763-p{p}", client/"sink165.sfc")
    assert r["firmware"] == fw and r["verified"] == 66
    v = r["display_VBlanks"]
    refs = read(ROOT/"analysis/capture785.json")["phases"][str(p)]
    delta = {k:dict(dense_ms=r["dense_ms"]-refs[k]["dense_ms"],
                    ACK970_ms=ms(r["final970"]-refs[k]["final970"])) for k in ("763","783G")}
    gates = dict(capture=r["input"][951]["edge_margin_ms"]>0,
                 display=all(v[g]==x for g,x in ((909,2),(952,3),(953,2),(954,3),(960,2),(969,2))),
                 dma=r["first"]==[size for _,_,size in RANGES] and bool(r["map_lines"]) and max(r["map_lines"])<=252,
                 time=all(t<0 for d in delta.values() for t in d.values()))
    return dict(passed=all(gates.values()), gates=gates, capture951_ms=r["input"][951]["edge_margin_ms"],
                intervals=v, first969=r["first"], map_lines969=r["map_lines"], dense_ms=r["dense_ms"],
                final970=r["final970"],delta=delta,joint=sha(folder/"joint.json"))


def package(temp, archive, report):
    work=temp/"nes-trial792"
    original=read(ROOT/"analysis/trial704-package.json")
    previous=PROBES/"nes-trial704/trial01/MMC704-60SEC-MMC705-LONG.zip"
    assert sha(previous)==original["ZIP_SHA256"]
    data={}
    variants={}
    with zipfile.ZipFile(previous) as z:
        common={}
        for name in ("sd2snes/fpga_base.bi3","sd2snes/m3nu.bin"):
            key="01-MMC704-60SEC-SD-ROOT/"+name
            common[name]=z.read(key)
            assert digest(common[name])==original["files"][key]
    for n, prefix, client in ((792,"01-MMC792-60SEC-SD-ROOT/",CLIENT),(793,"02-MMC793-LONG-SD-ROOT/",OUT/"client793")):
        src=OUT/f"link{n}/src/obj-nes-100"
        payload=(src/"firmware.stm").read_bytes()
        size,crc,inv=struct.unpack_from("<III",payload,8)
        assert payload[:4]==b"STM3" and size+512==len(payload)<=LIMIT
        assert zlib.crc32(payload[512:])==crc and crc^inv==0xffffffff
        fw=digest(payload)
        if n==792:
            assert (BASE/"obj-nes-100/firmware.stm").read_bytes()[32:].replace(b"763",b"792")==payload[32:]
        cfg=f"sd2snes/fpga_mmc{n}.bi3"
        marker=f"NES MMC3 {n}.nh1"
        logs=[f"sd2snes/nes-{k}-mmc{n}.txt" for k in ("progress","budget","game-last")]
        for key in [marker,*("/"+v for v in [cfg,f"sd2snes/nes/mmc{n}.nes",*logs])]:
            assert key.encode()+b"\0" in payload
        packed=work/f"packed{n}"
        bitstream=(packed/Path(cfg).name).read_bytes()
        image=read(packed/"image.json")
        bus=read(work/f"rom{n}/result.json")
        route=read(work/f"routing{n}.json")
        assert image["SOF"]==sha(work/f"board{n}/output_files/board.sof")
        assert image["programmer"]["passed"] and image["BI3"]==digest(bitstream) and image["RBF"]==digest(decode(bitstream))
        prior=read(ROOT/"analysis/trial763-package.json")["variants"]["763"]
        fitted=cost(work/f"board{n}")
        assert all(fitted[k]==prior[k] for k in ("LE","LAB","M9K","slack_ns"))
        assert min(fitted["slack_ns"].values())>0 and fitted["SOF"] and fitted["STA"] and not fitted["LAB_error"]
        mifs=list((work/f"board{n}/db").glob("board.ram*_nes_sink_bus165_*.hdl.mif"))
        assert len(mifs)==1 and mifs[0].name in (work/f"board{n}/quartus_cdb.log").read_text(errors="replace")
        assert sha(mifs[0])==route["MIF"]
        assert bus["bytes"]==5120 and bus["client"]==route["ROM"]==sha(client/"sink165.sfc")
        assert bus["program"]==sha(client/"sink-program.hex")==sha(work/f"board{n}/sink-program.hex")
        checks=work/f"checks{n}"
        menu=read(checks/"menu.json")
        assert menu["firmware"]==fw and menu["marker_cases"]==4
        for fault in ("none","program","done","busy","token"):
            base=read(checks/f"base-{fault}/result.json")
            assert base["passed"] and base["firmware_sha256"]==fw and base["safe_return"]==base["base_restored"]==int(fault=="none")
            assert base["config_paths"]==["/"+cfg,"/sd2snes/fpga_base.bi3"]
        mode=read(checks/"mode.json")
        if n==792:
            assert mode["firmware_SHA256"]==fw and mode["unfinished_excluded"]
            assert [(w["start_s"],w["end_s"]) for w in mode["accepted"]]==[(5,40),(40,55)]
        else:
            assert mode["firmware"]==fw and mode["passed"] and mode["first_windows"]==[2,2]
            assert read(work/"exitCPU/result.json")["client"]==bus["client"] and read(work/"exitDMA/result.json")["passed"]
        guards=read(work/f"guards{n}.json")
        assert guards["firmware"]==fw and len(guards["retire"])==9 and guards["ACK"]["corrupt_bits"]==152
        if n==792: assert guards["timer"]["passed"] and guards["timer"]["firmware"]==fw
        if n==793:
            assert read(work/"exitDMA/result.json")["CPU"]==bus["client"]
        boot=read(work/"boot/result.json")
        assert boot["passed"] and sum(r["ROM"]==bus["client"] for r in boot["cases"])==2
        phases={}
        for p in (1,2):
            row=phase(temp,n,p,client,fw)
            assert row["passed"],(n,p,row)
            stop=read(work/f"stop{n}-p{p}/proof.json")
            assert stop["after_return"] and stop["map_offset"]==2496 and stop["commits"]==64 and stop["blanks_after_STOP"]>=3
            assert stop["client"]==bus["client"] and stop["retained"]==sha(temp/f"nes-trial792-{n}-p{p}/frame-968.rgb")
            row["STOP"]=stop
            phases[p]=row
        variants[n]=dict(Flash_B=len(payload),free_B=LIMIT-len(payload),ELF=sha(src/"sd2snes.elf"),firmware=fw,
                         BI3=image["BI3"],ROM=bus,route=route,fit={k:fitted[k] for k in ("LE","LAB","M9K","slack_ns")},phases=phases,guards=sha(work/f"guards{n}.json"),
                         checks={str(q.relative_to(checks)):sha(q) for q in checks.rglob("*.json")})
        for k,b in {marker:b"",cfg:bitstream,"sd2snes/firmware.stm":payload,**common}.items():
            data[prefix+k]=b
        data[prefix+"sd2snes/nes/ROM-NOT-INCLUDED.txt"]=f"Copy your MMC763 ROM as mmc{n}.nes in this directory.\n".encode()
    data["README-KO.txt"]=(ROOT/"docs/nes-mmc792-793-trial.ko.md").read_bytes()
    manifest=dict(variants=variants, files={k:digest(b) for k,b in data.items()},physical=False)
    data["manifest.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
    assert all("restore" not in k.lower() and not k.lower().endswith((".nes",".sav",".srm")) for k in data)
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,"x",zipfile.ZIP_DEFLATED) as z:
        for k,b in data.items(): z.writestr(k,b)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(data) and all(z.read(k)==b for k,b in data.items())
    save(report,dict(**manifest,ZIP_SHA256=sha(archive), ZIP_bytes=archive.stat().st_size))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("temp","archive","report"):p.add_argument(k,type=Path)
    a=p.parse_args()
    package(a.temp,a.archive,a.report)
