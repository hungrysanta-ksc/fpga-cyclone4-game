"""Replace the routed 707D ROM initialization, preserving the fitted logic and timing."""
import argparse
import re
import shutil
import subprocess
from types import SimpleNamespace

from pathlib import Path
from package_nes_trial704 import read, save, sha, image
from prepare_nes_trial792 import CLIENT, OUT, ROOT


def assemble(number, base, work, quartus):
    proof = read(ROOT / "analysis/trial763-package.json")["variants"]["763"]
    assert sha(base/"output_files/board.sof") == read(work.parent/"nes-trial763/packed763/image.json")["SOF"]
    pins = read(ROOT/"analysis/bg707-verification.json")["inputs"]
    client = CLIENT if number == 792 else OUT/"client793"
    for name, h in {**pins["base"], **pins["changed"]}.items():
        if name != "sink-program.hex":
            assert sha(base/name) == h, name
    assert sha(base/"sink-program.hex") == proof["ROM_bus"]["program"]
    replace_client(number, base, work, quartus, client)


def replace_client(number, base, work, quartus, client):
    """Change only the client MIF of an already routed and assembled project."""
    board = work/f"board{number}"
    shutil.copytree(base, board)
    old = bytes.fromhex((base/"sink-program.hex").read_text())
    new = bytes.fromhex((client/"sink-program.hex").read_text())
    mif, = (board/"db").glob("board.ram*_nes_sink_bus165_*.hdl.mif")
    pattern = re.compile(r"^(\s*)(\d+)(\s*:\s*)([01]{8})(;)", re.M)
    original = mif.read_text()
    def extract(s):
        rows = sorted((int(m[2]), int(m[4], 2)) for m in pattern.finditer(s))
        assert [k for k,v in rows] == list(range(5120))
        return bytes(v for k,v in rows)
    assert extract(original)==old and len(new)==5120 and old!=new
    updated = pattern.sub(lambda m:m[1]+m[2]+m[3]+f"{new[int(m[2])]:08b}"+m[5], original)
    assert extract(updated)==new
    mif.write_text(updated, newline="\n")
    shutil.copyfile(client/"sink-program.hex",board/"sink-program.hex")
    for exe, args in (("quartus_cdb", ["--update_mif"]), ("quartus_asm", [])):
        with (board/(exe+".log")).open("wb") as log:
            subprocess.run([quartus/(exe+".exe"), "board", *args], cwd=board, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=300)
    assert mif.name in (board/"quartus_cdb.log").read_text(errors="replace")
    assert extract(mif.read_text()) == new
    assert sha(board/"output_files/board.sof") != sha(base/"output_files/board.sof")
    for n in ("board.fit.rpt", "board.sta.rpt", "board.pin", "board.fit.summary", "board.sta.summary"):
        assert sha(base/"output_files"/n)==sha(board/"output_files"/n)
    image(SimpleNamespace(board=board,out=work/f"packed{number}",quartus=quartus,number=str(number)))
    save(work/f"routing{number}.json",dict(base_SOF=sha(base/"output_files/board.sof"),ROM=sha(client/"sink165.sfc"),
        FIT=sha(board/"output_files/board.fit.rpt"), STA=sha(board/"output_files/board.sta.rpt"), MIF=sha(mif)))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("number",type=int,choices=(792,793))
    for name in ("base","work","quartus"):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    assemble(a.number,a.base,a.work,a.quartus)
