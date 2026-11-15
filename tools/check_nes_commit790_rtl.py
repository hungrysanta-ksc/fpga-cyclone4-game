# SPDX-License-Identifier: MIT
"""Run the terminal COMMIT/collector-release slice using the board's two CDC mailboxes."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


def simulate(board, out, questa):
    assert os.environ.get("SALT_LICENSE_SERVER")=="18000@localhost"
    out.mkdir(parents=True, exist_ok=False)
    testdir=Path(__file__).resolve().parents[1]/"tests/nes-functional"
    inputs=[board/(n+".sv") for n in ("nes_native_export203","nes_native_mailbox165",
                                      "nes_native_spi165","nes_geometry_sender653")]
    inputs += [testdir/"spi200_bus.svh",testdir/"commit790_tb.sv"]
    for p in inputs:
        shutil.copyfile(p,out/p.name)
    def run(tool, args):
        log=out/(tool+".log")
        with log.open("wb") as stream:
            subprocess.run([str(questa/(tool+".exe")),*args],cwd=out,stdout=stream,
                           stderr=subprocess.STDOUT,check=True,timeout=120,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        text=log.read_text(errors="replace")
        assert not re.search(r"\*\* (?:Error|Fatal):",text),log
        return text
    run("vlib",["work"])
    run("vlog",["-sv",*[p.name for p in inputs if p.suffix==".sv"]])
    log=run("vsim",["-c","-gSPI_HALF=190.47619","work.commit790_tb","-do","run -all; quit -f"])
    match=re.search(r"PASS COMMIT790 D3_to_release_ns=([\d.]+) D3_to_available_ns=([\d.]+)",log)
    assert match, out/"vsim.log"
    proof=dict(scope="Terminal generation 953 after independently drained prefix; active NES and host clocks",
               D3_to_release_ns=float(match[1]),D3_to_available_ns=float(match[2]),
               sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (out/"proof.json").write_text(json.dumps(proof,indent=2)+"\n",newline="\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("board","out","questa"):parser.add_argument(name,type=Path)
    a=parser.parse_args()
    simulate(a.board,a.out,a.questa)
