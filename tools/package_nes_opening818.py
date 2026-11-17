"""Bind the cold-reset opening comparison, ROM-specific ARM links and fitted vertical MMC3 board."""
import argparse
import csv
import json
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from analyze_nes_status689 import cost
from package_nes_trial704 import digest, read, sha
from prepare_nes_opening818 import ADVENTURE_SHA, ROM_SHA, WORK
from prepare_nes_trial816 import PROBES, ROOT
from check_nes_game478 import ELFFile


def linked_functions(src):
    with (src/"obj-nes-100/sd2snes.elf").open("rb") as f:
        elf=ELFFile(f)
        section=elf.get_section_by_name(".text")
        start=section["sh_addr"]
        data=section.data()
        result={}
        for sym in elf.get_section_by_name(".symtab").iter_symbols():
            offset=(sym["st_value"]&~1)-start
            if sym["st_info"]["type"]=="STT_FUNC" and sym["st_size"] and 0<=offset<len(data):
                result[sym.name]=data[offset:offset+sym["st_size"]]
        return result


def opening(temp,i,rom):
    normal=temp/f"nes-opening818-one{i}"
    repeat=temp/f"nes-opening818-two{i}"
    hidden=temp/f"nes-opening818-hide{i}"
    obs=read(normal/"result.json")
    assert obs==read(repeat/"result.json") and obs["sha256"]==rom
    assert obs["frames_sha256"]==sha(normal/"frames.csv")==sha(repeat/"frames.csv")
    def rows(d):
        with (d/"frames.csv").open() as f:
            return list(csv.DictReader(f))
    a,b=rows(normal),rows(hidden)
    assert len(a)==len(b)==3600
    assert all(all(x[k]==y[k] for k in ("frame","obj","changed","masked","mirror")) for x,y in zip(a,b))
    for start,end in ((5,40),(40,55)):
        pairs=[(x,y) for x,y in zip(a[start*60:end*60],b[start*60:end*60]) if x["sample"]!="-1"]
        obs["windows"][f"{start}-{end}"]["screen_samples_affected_by_sprites"]=sum(x["sample"]!=y["sample"] for x,y in pairs)
    obs["background_only_trace"]=sha(hidden/"frames.csv")
    return obs


def package(temp):
    base=temp/"nes-trial816-board816"
    board=temp/"nes-opening818-board"
    for f in base.rglob("*"):
        rel=f.relative_to(base)
        if len(rel.parts)>1 and rel.parts[0] not in ("rtl","sys"):
            continue
        if f.suffix in (".sv",".v",".vhd",".sdc",".qsf",".qpf",".hex"):
            before=f.read_bytes()
            if rel.as_posix()=="cart_nrom.sv":
                before=before.replace(b".flags(32'd4)",b".flags(32'h00004004)")
            assert (board/rel).read_bytes()==before,rel
    c=cost(board)
    s=(board/"output_files/board.sta.summary").read_text()
    assert c["unconstrained"]==cost(base)["unconstrained"] and c["STA"] and c["SOF"]
    tns=re.findall(r"^TNS\s+: ([-.\d]+)",s,re.M)
    assert len(tns)==s.count("Type  :")>=40 and all(float(n)==0 for n in tns) and min(c["slack_ns"].values())>=0
    packed=temp/"nes-opening818-packed"
    bi=(packed/"fpga_mmc818.bi3").read_bytes()
    image=read(packed/"image.json")
    assert image["SOF"]==c["reports"]["board.sof"] and image["BI3"]==digest(bi) and image["programmer"]["passed"]
    parent=read(ROOT/"analysis/trial816-package.json")
    archive=PROBES/"nes-trial816/MMC816-60SEC-MMC817-LONG.zip"
    assert sha(archive)==parent["ZIP_SHA256"]
    files={"README-KO.txt":(ROOT/"docs/nes-mmc818-819-trial.ko.md").read_bytes()}
    baseline=linked_functions(PROBES/"nes-trial816/link816/src")
    admission=read(WORK/"admission.json")
    assert len(admission)==8 and admission["818_captain"]["program"] and admission["819_adventure"]["program"]
    assert not any(r["program"] for k,r in admission.items() if k not in ("818_captain","819_adventure"))
    proof=dict(scope="No-input emulator workload; source RTL boots with ideal external ROM; physical measurements pending.",
               mapper=4,PRG_KiB=256,CHR_KiB=128,reset_mirroring="vertical",admission=admission,
               parent_zip=sha(archive),board={k:c[k] for k in ("LE","LAB","M9K","slack_ns","unconstrained","reports")},
               programmer_BI3=digest(bi),builds={})
    with ZipFile(archive) as z:
        for n,idx,slug,game,rom,title in ((819,1,"01-MMC819-ADVENTURE","adventure",ADVENTURE_SHA,"Takahashi Meijin no Boukenjima 4 (J)"),
                                          (818,0,"02-MMC818-TSUBASA","captain",ROM_SHA,"Captain Tsubasa Vol. 2 Super Striker (Japan)")):
            fw=(WORK/f"link{n}/src/obj-nes-100/firmware.stm").read_bytes()
            assert len(fw)<=212992
            functions=linked_functions(WORK/f"link{n}/src")
            assert functions.keys()==baseline.keys() and {k for k in baseline if baseline[k]!=functions[k]}=={"nes_menu_sd_probe"}
            for tag in ("progress","budget","game-last"):
                assert f"nes-{tag}-mmc{n}.txt".encode() in fw
            for x in (f"mmc{n}.nes",f"fpga_mmc{n}.bi3",f"NES MMC3 {n}.nh1"):
                assert x.encode()+b"\0" in fw
            suffix="819" if n==819 else ""
            menu=read(WORK/f"menu{suffix}.json")
            base_return=read(WORK/f"base{suffix}/result.json")
            deadline=read(WORK/f"deadline{suffix}.json")
            windows=read(WORK/f"windows{suffix}.json")
            assert menu["firmware"]==digest(fw)==base_return["firmware_sha256"]==deadline["firmware"]==windows["firmware_SHA256"]
            assert menu["rows"]["normal"]["released"]==1 and base_return["safe_return"] and base_return["base_restored"]
            assert deadline["passed"] and windows["layout"]=="trimmed" and windows["unfinished_excluded"]
            corepath=temp/"nes-opening818-core"/f"{game}.log"
            if game=="adventure" and (temp/"nes-opening818-core-adventure").is_dir():
                corepath=temp/"nes-opening818-core-adventure"/"adventure.log"
            core=corepath.read_text(errors="replace")
            match=re.search(rf"PASS818 {game} frames=(\d+) nt=(\d+) chr=(\d+) colors=(\d+)",core)
            assert match and "Errors: 0" in core,game
            proof["builds"][n]=dict(ROM=rom,firmware=digest(fw),flash_free=212992-len(fw),
                compared_named_functions=len(functions),changed_function="nes_menu_sd_probe",
                reference=opening(temp,idx,rom),RTL_boot=dict(zip(("frames","nametable_writes","CHR_reads","colors"),map(int,match.groups()))),
                menu=sha(WORK/f"menu{suffix}.json"),stop=sha(WORK/f"base{suffix}/result.json"),deadline=sha(WORK/f"deadline{suffix}.json"))
            prefix="01-MMC816-60SEC-SD-ROOT/"
            members=[k for k in z.namelist() if k.startswith(prefix)]
            assert len(members)==10
            for k in members:
                data=z.read(k)
                assert parent["files"][k]==digest(data)
                if k.endswith("/firmware.stm"):
                    data=fw
                elif k.endswith("/fpga_mmc816.bi3"):
                    data=bi
                elif k.endswith("ROM-NOT-INCLUDED.txt"):
                    data=f"Copy your {title} ROM here as mmc{n}.nes.\n".encode()
                files[slug+"-60SEC-SD-ROOT/"+k[len(prefix):].replace("816",str(n))]=data
    proof["files"]={k:digest(v) for k,v in files.items()}
    files["manifest.json"]=(json.dumps(proof,indent=2)+"\n").encode()
    assert len(files)==22 and not any(k.lower().endswith(".nes") or "restore" in k.lower() for k in files)
    dest=WORK/"MMC819-ADVENTURE-MMC818-TSUBASA-60SEC.zip"
    with ZipFile(dest,"x") as z:
        for k,v in files.items():
            z.writestr(ZipInfo(k),v,compress_type=ZIP_DEFLATED)
    with ZipFile(dest) as z:
        assert z.testzip() is None and all(z.read(k)==v for k,v in files.items())
    proof["ZIP_SHA256"]=sha(dest)
    (ROOT/"analysis/opening818-results.json").write_text(json.dumps(proof,indent=2)+"\n",newline="\n")
    print(dest,proof["ZIP_SHA256"])


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    package(p.parse_args().temp)
