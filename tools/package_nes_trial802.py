"""Gate both fortress editions on the same routed board and the original timing constraints."""
import argparse
import csv
import json
import re
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile

from assemble_nes_trial792 import replace_client
from check_nes_game478 import ELFFile
from package_nes_control798 import GBC, ROOT, verify
from package_nes_trial704 import digest, image, read, save, sha
from prepare_nes_trial802 import EDITIONS, PROBES, WORK
from prepare_nes_snapshot801 import serial_request, serial_snapshot
from rebind_nes_fortress800 import bind


def board_checks(board, temp):
    old = temp / "nes-fortress800-board-b-bound"
    same_sources = {}
    changed = {}
    spi_test = None
    for src in old.rglob("*"):
        rel = src.relative_to(old)
        if len(rel.parts) > 1 and rel.parts[0] not in ("rtl", "sys"):
            continue
        if src.suffix.lower() in (".sv", ".v", ".vhd", ".qsf", ".sdc", ".hex"):
            if rel.name == "nes_sink_spi165.sv" and sha(board/rel) != sha(src):
                status = serial_snapshot(src.read_text())
                spi_test = "h" if (board/rel).read_text() == status else "i"
                assert (board/rel).read_text() == (status if spi_test=="h" else serial_request(status))
                changed[rel.as_posix()] = sha(board/rel)
            elif rel.name == "cdc181.sdc" and sha(board/rel) != sha(src):
                raw = temp/"nes-trial763/board763/cdc181.sdc"
                assert (board/rel).read_text() == bind(raw.read_text(), (board/"output_files/board.map.rpt").read_text(errors="replace"))
                changed[rel.as_posix()] = sha(board/rel)
            elif rel.as_posix() == "board.qsf" and sha(board/rel) != sha(src):
                original = src.read_text()
                assert (board/rel).read_text() == original + "\nset_global_assignment -name ROUTER_EFFORT_MULTIPLIER 2.0\n"
            else:
                same_sources[rel.as_posix()] = sha(src)
                assert sha(board / rel) == same_sources[rel.as_posix()], rel
    reports = board / "output_files"
    fit = (reports / "board.fit.summary").read_text()
    sta = (reports / "board.sta.summary").read_text()
    assert "Fitter Status : Successful" in fit and "Lite Edition" in fit
    slacks = re.findall(r"Type\s+: (.+)\s+Slack\s+: ([-.\d]+)\s+TNS\s+: ([-.\d]+)", sta)
    assert len(slacks) == len(re.findall("^Type", sta, re.M)) >= 40
    assert all(float(s) >= 0 and float(t) == 0 for _, s, t in slacks)
    assert "Timing requirements not met" not in (board / "801-signoff.log").read_text()
    worst = {}
    for kind in ("Setup", "Hold", "Recovery", "Removal", "Minimum Pulse Width"):
        worst[kind] = min(float(s) for label, s, _ in slacks if "Model " + kind + " " in label)
    with (board / "paths801.tsv").open() as f:
        pairs = list(csv.DictReader(f, delimiter="\t"))
    assert len(pairs) == 12 and all(float(r["slack_ns"]) >= 0 for r in pairs)
    with (board / "io612.tsv").open() as f:
        io = list(csv.DictReader(f, delimiter="\t"))
    assert len(io) == 9 and all(float(r["slack"]) >= 0 for r in io)
    if "nes_sink_spi165.sv" in changed:
        eq = read(temp/f"nes-fortress801-snapshot-{spi_test}/result.json")
        assert eq["passed"] and len(eq["runs"]) == 4
        assert eq["pins"]["nes_sink_spi165.sv"] == changed["nes_sink_spi165.sv"]
        assert eq["reference"]["nes_sink_spi165.sv"] == sha(old/"nes_sink_spi165.sv")
    else:
        eq = None
    return dict(fit=fit.splitlines(), worst_slack_ns=worst, paths=pairs, io=io, changed=changed, spi_equivalence=eq,
                nominal_SDC=sha(old / "board.sdc"), qsf=sha(board/"board.qsf"), same_sources=same_sources,
                reports={n:sha(reports/n) for n in ("board.fit.rpt","board.sta.rpt","board.pin")})


def assemble(board, temp, qbin):
    board_checks(board, temp)
    out = temp / "nes-delivery802"
    out.mkdir(exist_ok=False)
    image(SimpleNamespace(number="802", board=board, out=out/"packed802", quartus=qbin))
    replace_client(803, board, out, qbin, PROBES/"nes-longrun694/client01")


def guards(temp, board):
    previous = read(ROOT/"analysis/fortress800.json")
    proof = []
    for mode in ("full","abort"):
        for phase in range(3):
            folder = temp/f"nes-fortress801-guards-{mode}-p{phase}"
            old = temp/f"nes-fortress800c-{'compact' if mode=='full' else 'abort'}-p{phase}"
            log = (folder/"simulation.log").read_text()
            original = (old/"simulation.log").read_text()
            assert digest((old/"simulation.log").read_bytes()) == previous["runs"][f"c-{'compact' if mode=='full' else 'abort'}-p{phase}"]["log_sha256"]
            def events(s):
                return [row for row in s.splitlines() if row.startswith(("# WRAP800 ", "# CASE699CPU ", "# ABORT800 ", "# DONE698"))]
            assert events(log) == events(original) and "# DONE698" in log
            inputs = read(folder/"inputs.json")["sources"]
            # The fixture also lists its generated bench; hardware units are pinned separately.
            for rel in ("rtl/ppu.sv","nes_rom_service.sv","nes_native_arbiter165.sv","nes_rom_physical.sv"):
                assert inputs[rel] == sha(board/rel)
            proof.append(dict(mode=mode, phase=phase, log=sha(folder/"simulation.log")))
    return proof


def package(board, temp):
    evidence = board_checks(board, temp)
    proof = guards(temp, board)
    delivery = temp/"nes-delivery802"
    reference = read(ROOT/"analysis/control798-package.json")
    original = PROBES/"nes-control798/MMC798-60SEC-MMC799-LONG.zip"
    assert sha(original) == reference["ZIP_SHA256"]
    files = {"README-KO.txt": (ROOT/"docs/nes-mmc802-803-trial.ko.md").read_bytes()}
    variants = {}
    with ZipFile(original) as archive:
        for parent, n in EDITIONS:
            mode = "60SEC" if n == 802 else "LONG"
            prefix = f"0{n-801}-MMC{n}-{mode}-SD-ROOT/"
            old = prefix.replace(str(n), str(parent))
            fw = (WORK/f"link{n}/src/obj-nes-100/firmware.stm").read_bytes()
            same = {k:archive.read(old+k) for k in (*GBC, "sd2snes/fpga_base.bi3","sd2snes/m3nu.bin")}
            assert all(digest(v) == reference["files"][old+k] for k,v in same.items())
            ctl = reference["variants"][str(parent)]
            report = verify(n,fw,same["sd2snes/gbc_snes.bin"],temp,{"ROM_SHA256":ctl["client"]},work=WORK,parent=parent)
            elf = Path("src/obj-nes-100/sd2snes.elf")
            with (PROBES/f"nes-control798/link{parent}"/elf).open("rb") as first, (WORK/f"link{n}"/elf).open("rb") as second:
                a,b = ELFFile(first),ELFFile(second)
                assert sha(PROBES/f"nes-control798/link{parent}"/elf) == ctl["ELF"]
                for tag in (".text",".data",".ahbram",".ARM.exidx",".rodata"):
                    u,v = a.get_section_by_name(tag), b.get_section_by_name(tag)
                    assert u["sh_addr"]==v["sh_addr"] and u["sh_size"]==v["sh_size"]
                    if tag==".rodata":
                        assert u.data().replace(str(parent).encode(),str(n).encode())==v.data()
                    else:
                        assert u.data()==v.data()
                report["identical_ARM_text_bytes"] = b.get_section_by_name(".text")["sh_size"]
            packed = delivery/f"packed{n}"
            bi = (packed/f"fpga_mmc{n}.bi3").read_bytes()
            img = read(packed/"image.json")
            target = board if n == 802 else delivery/"board803"
            rom = read(delivery/f"rom{n}/result.json")
            assert img["BI3"] == digest(bi) and img["SOF"] == sha(target/"output_files/board.sof")
            assert img["programmer"]["passed"] and rom["bytes"] == 5120
            assert rom["program"] == sha(target/"sink-program.hex") and rom["client"] == ctl["client"]
            assert rom["bus"] == sha(target/"nes_sink_bus165.sv")
            report.update(image=img, rom=rom)
            variants[n] = report
            files.update({prefix+k:v for k,v in same.items()})
            files[prefix+"sd2snes/firmware.stm"] = fw
            files[prefix+f"sd2snes/fpga_mmc{n}.bi3"] = bi
            files[prefix+"sd2snes/nes/ROM-NOT-INCLUDED.txt"] = f"Copy your SMB3(J) ROM here as mmc{n}.nes.\n".encode()
            for marker in ("NES MMC3","NES-DIAG/NES START","NES-DIAG/NES BOOT"):
                files[prefix+f"{marker} {n}.nh1"] = b""
    manifest = dict(variants=variants, board=evidence, fortress=proof,
                    physical_test=False, files={k:digest(v) for k,v in files.items()})
    files["manifest.json"] = (json.dumps(manifest,indent=2)+"\n").encode()
    zip_path = WORK/"MMC802-60SEC-MMC803-LONG.zip"
    with ZipFile(zip_path,"x",ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name,data)
    with ZipFile(zip_path) as z:
        assert set(z.namelist()) == set(files) and z.testzip() is None
        assert all(z.read(k)==v for k,v in files.items())
        assert not any("restore" in k.lower() for k in z.namelist())
    save(ROOT/"analysis/trial802-package.json",dict(**manifest,ZIP_SHA256=sha(zip_path)))
    print(zip_path, sha(zip_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("assemble","package"))
    parser.add_argument("board", type=Path)
    parser.add_argument("temp", type=Path)
    parser.add_argument("--quartus", type=Path)
    a = parser.parse_args()
    if a.action == "assemble":
        assemble(a.board,a.temp,a.quartus)
    else:
        package(a.board,a.temp)
