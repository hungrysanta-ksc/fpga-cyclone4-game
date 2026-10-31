# SPDX-License-Identifier: MIT
"""Compare real D1 bytes and CRC/POP/STOP behavior with the schedule's input."""
import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path
from nes_transfer512 import input_packets, legacy_packets
from nes_raw506 import once, sha

ROOT = Path(__file__).resolve().parents[1]


def prepare(a):
    a.out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(a.rtl, a.out / "nes_native_spi165.sv")
    tb = (ROOT / "tests/nes-functional/native_spi165_tb.sv").read_text()
    tb = tb.replace("ag!=12", "ag!=records[0][92:77]").replace("8'hd3,12,1","8'hd3,records[0][92:77],1")
    if a.legacy:
        tb = once(tb, "pos=pos+4+width(kind);", "pos=pos+4+((kind==0 && (index&4096)!=0)?8:(kind==3?4:width(kind)));")
    else:
        tb = once(tb, "got_end=0;pos=1;", """if(rx[1]!=8'h51 || {rx[2],rx[3]}!=records[0][92:77])$fatal(1,"packet context");
      got_end=0;pos=4;""")
        tb = once(tb, "pos=pos+4+width(kind);", "pos=pos+2+((kind==0 && (index&4096)!=0)?8:(kind==3?4:width(kind)));")
        tb = once(tb, '  $display("PASS SPI165', """  reset=1;#100;reset=0;
  @(negedge clk);data=records[0];valid=1;@(posedge clk);@(negedge clk);valid=0;
  wait(ready);@(negedge clk);data=records[1];data[92:77]=~records[0][92:77];valid=1;
  @(posedge clk);@(negedge clk);valid=0;if(!fault||dut.sealed)$fatal(1,"mixed identity accepted");
  reset=1;#100;reset=0;#100;if(fault||dut.used||dut.sealed||dut.token)$fatal(1,"STOP leaked packet");
  $display("PASS SPI165""")
    (a.out / "tb.sv").write_text(tb)
    with a.records.open() as f:
        events = list(csv.DictReader(f))
    for g in range(905,917):
        records = [row["word"] for row in events if int(row["generation"]) == g]
        (a.out / f"records-{g}.hex").write_text("\n".join(records)+"\n")


def run(a):
    def tool(name, *args):
        with (a.out / (name+"-"+str(len(list(a.out.glob("*.log"))))+".log")).open("wb") as log:
            subprocess.run([str(a.bin / (name+".exe")),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    tool("vlib","work")
    tool("vlog","-sv","nes_native_spi165.sv","tb.sv")
    frames = []
    for g in range(905,917):
        rec = a.out / f"records-{g}.hex"
        shutil.copyfile(rec,a.out / "records.hex")
        tool("vsim","-c","-quiet","-do","onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0",
             "native_spi165_tb",f"+COUNT={len(rec.read_text().splitlines())}")
        raw = a.out / "transactions.txt"
        destination = a.out / f"transactions-{g}.txt"
        raw.replace(destination)
        packets = []
        for line in destination.read_text().splitlines():
            size, tx, rx = line.split()
            if bytes.fromhex(tx)[0] == 0xd1:
                packets.append(bytes.fromhex(rx)[1:-2])
        expected, _, _ = (legacy_packets if a.legacy else input_packets)((a.data / f"frame{g}.geometry").read_bytes(),(a.data / f"frame{g}.raw").read_bytes(),g)
        assert packets == expected, (g, list(map(len, packets)),list(map(len, expected)))
        frames.append(dict(generation=g,packets=len(packets),bytes=sum(map(len,packets)),wire_SHA256=sha(destination)))
    (a.out / "result.json").write_text(json.dumps(dict(passed=True,frames=frames),indent=2))

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("prepare","run"))
    for arg in ("rtl","records","out","data","bin"):
        p.add_argument("--"+arg,type=Path)
    p.add_argument("--legacy",action="store_true")
    a=p.parse_args()
    (prepare if a.mode=="prepare" else run)(a)
