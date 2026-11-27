"""Mixed-language test of the FF3 checkpoint stream. Use the installed FLOAT wrapper."""
import re
import subprocess
import tempfile
from pathlib import Path
from prepare_nes_ff3_checkpoint import ROOT,OUT,prepare
from check_ff3_state_reference import DIGEST
import hashlib
import os
import sys
import struct
import zlib

BIN=Path("C:/altera_standard/25.1std/questa_fse/win64")


def run(firmware=None):
    game_slot=os.getenv("FF3_PHYSICAL_SLOT")
    replay=bool(game_slot or os.getenv("FF3_OPENING_FRAMES"))
    output=Path(os.getenv("FF3_REPLAY_OUT",str(OUT))) if replay else OUT
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ff3-rtl-") as tmp:
        tmp=Path(tmp)
        board=tmp/"core"
        fitted=os.getenv("FF3_CHECKPOINT_BOARD")
        if fitted:board=Path(fitted).resolve(strict=True)
        else:prepare(board)
        rom=next(p for p in (Path.home()/"Downloads/test").glob("Final Fantasy III*.nes")
                 if hashlib.sha256(p.read_bytes()).hexdigest()==DIGEST)
        prg=rom.read_bytes()[16:]
        (tmp/"prg.bin").write_bytes(prg)
        sim_args=[]
        if replay:
            frames=int(os.getenv("FF3_OPENING_FRAMES","8"))
            assert 1<=frames<=240
            sim_args.extend(["+scene_replay",f"+frames={frames}"])
            if os.getenv("FF3_MOVE_UP"):
                sim_args.append("+move_up")
            if os.getenv("FF3_ATTACK"):
                sim_args.append("+attack")
            if os.getenv("FF3_WALK_DOWN"):
                sim_args.append("+walk_down")
            if game_slot:
                raw=Path(game_slot).read_bytes()
                magic,schema,rom_key,prg_size,slot,size,serial,crc,hcrc=struct.unpack_from("<9I",raw)
                assert (magic,schema,rom_key,prg_size)==(0x5353454e,1,zlib.crc32(rom.read_bytes()),len(prg))
                assert 1<=slot<=4 and len(raw)==36+size and size==21264
                assert zlib.crc32(raw[:32])==hcrc and zlib.crc32(raw[36:])==crc
                (tmp/"physical.hex").write_text("".join(f"{word:016x}\n" for word, in struct.iter_unpack("<Q",raw[36:])))
                sim_args.append("+physical_slot")
        env=os.environ.copy()
        if firmware is not None:
            firmware=Path(firmware).resolve(strict=True)
            assert (firmware/"obj-nes-100/firmware.stm").is_file()
            (tmp/"ff3_disk_bridge.py").write_text(
                "import sys\nfrom pathlib import Path\n"
                f"sys.path.insert(0,{ascii(str(ROOT/'tools'))})\n"
                "from check_ff3_sd1043 import checkpoint_roundtrip\n"
                f"checkpoint_roundtrip(Path({ascii(str(firmware))}),{zlib.crc32(rom.read_bytes())})\n")
            env['PATH']=str(Path(sys.executable).parent)+os.pathsep+env['PATH']
            sim_args.append("+fatfs_roundtrip")
        def tool(name,*args):
            with (output/(name+"-checkpoint.log")).open("wb") as log:
                proc=subprocess.run([BIN/(name+".exe"),*args],cwd=tmp,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=max(1800,frames*65) if name=="vsim" and replay else 1800 if name=="vsim" else 800)
            result=(output/(name+"-checkpoint.log")).read_text(errors="replace")
            if proc.returncode or "** Error" in result or "** Fatal" in result:
                raise RuntimeError(result[-2400:])
            return result
        tool("vlib","work")
        qsf=(board/"board.qsf").read_text()
        vhdl=re.findall(r"^set_global_assignment -name VHDL_FILE (rtl/\S+)",qsf,re.M)
        tool("vcom","-2008",*[board/s for s in vhdl])
        sv=re.findall(r"^set_global_assignment -name SYSTEMVERILOG_FILE ((?:rtl|sys)/\S+)",qsf,re.M)
        sv+=["cart_nrom.sv","nes_probe.sv","nes_local_memory.sv","nes_native_ciram165.sv","nes_checkpoint_memory.sv"]
        if replay:
            sv += ["nes_native_compact181.sv","nes_native_planes165.sv","nes_native_raster181.sv",
                   "nes_patch_capture181.sv","nes_patch_rows181.sv","nes_native_frame201.sv"]
        imports=tmp/"state_import.sv"
        imports.write_text("import regs_savestates::*;\n")
        snapshot=board/"nes_chr_snapshot.sv"
        if not snapshot.exists():
            snapshot=ROOT/"src/nes/nes_chr_snapshot.sv"
        tool("vlog","-mfcu","-sv",*(["+define+FF3_PAGE_HISTORY"] if "clean_pages" in snapshot.read_text() else []),*(["+define+FF3_FITTED"] if fitted else []),*(["+define+FF3_SCENE"] if replay else []),*(["+define+FF3_PAGES"] if "changed_page" in snapshot.read_text() else []),*(["+define+FF3_BACKDROP"] if replay and "non_backdrop" in (board/"nes_native_raster181.sv").read_text() else []),*(["+define+FF3_CHR_HISTORY"] if "frame_unchanged" in snapshot.read_text() else []),board/sv[0],imports,snapshot,*[board/s for s in sv[1:]],ROOT/"tests/nes-functional/ff3_checkpoint_tb.sv")
        result=tool("vsim","-c","-L","altera_mf_ver","-suppress","3009","work.ff3_checkpoint_tb",*sim_args,"-do","onerror {quit -code 1}; run -all; quit -f")
        if replay:
            if 'PASS FF3 physical scene replay' not in result:raise RuntimeError(result[-1200:])
            return
        match=re.search(r"PASS FF3 checkpoint [^\r\n]+",result)
        if not match: raise RuntimeError(result[-2400:])
        print(match[0])


if __name__=="__main__":run(os.getenv("FF3_CHECKPOINT_ARM_SRC"))

