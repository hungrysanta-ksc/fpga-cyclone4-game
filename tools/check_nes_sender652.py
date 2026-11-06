"""Drive the fitted board's exporter, both CDC mailboxes and D0..D3 RAM owner."""
import argparse
import binascii
import json
from pathlib import Path
import shutil
import subprocess
from check_nes_fault641 import ROOT,digest
from nes_geometry650 import encode

def prepare(a, *, encoder=encode, codec="nes_geometry_sender652.sv", bench=None):
    a.out.mkdir(parents=True,exist_ok=False)
    names=[codec,"nes_native_spi165.sv","nes_native_export203.sv","nes_native_mailbox165.sv"]
    for name in names:shutil.copyfile(a.board/name,a.out/name)
    source=(ROOT/"tests/nes-functional/native_spi165_tb.sv").read_text()
    tasks=source[source.index(" function automatic [7:0] c8"):source.index(" always @(posedge clk)if(!reset")]
    tb=(Path(__file__).with_name("sender652_tb.sv")).read_text().replace("// SPI_TASKS",tasks.replace("tx[","spi_tx["))
    if bench:tb=bench(tb)
    (a.out/"tb.sv").write_text(tb)
    with (a.out/"scenes.txt").open("w") as sc:
        for gen in range(905,958):
            raw=(a.data/f"frame{gen}.raw").read_bytes()
            packets,counts,arrays=encoder((a.data/f"frame{gen}.geometry").read_bytes(),raw,gen)
            lines=[]
            for k,values in enumerate([*arrays,[],raw]):
                if len(values):lines.extend([f"@{2048*k:x}",*(f"{x:016x}" for x in values)])
            (a.out/f"scene{gen}.hex").write_text("\n".join(lines)+"\n")
            print(gen,counts[0]//33,counts[2],counts[3],counts[5]//32,len(raw)//256,len(packets),file=sc)
    for tool,args in (("vlib",["work"]),("vlog",["-sv",*names,"tb.sv"]),
             ("vsim",["-c","-quiet","sender652_tb",*(["+GUARDS"] if a.guards else []),"-do","onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0"])):
        with (a.out/(tool+".log")).open("wb") as f:
            subprocess.run([a.bin/(tool+".exe"),*args],stdout=f,stderr=subprocess.STDOUT,cwd=a.out,check=True,timeout=900)
    assert "PASS652" in (a.out/"vsim.log").read_text()
    if a.guards:return
    timings={}
    rows=(a.out/"blocks.txt").read_text().splitlines()
    for gen in range(905,958):
        actual=[]
        expect=encoder((a.data/f"frame{gen}.geometry").read_bytes(),(a.data/f"frame{gen}.raw").read_bytes(),gen)[0]
        for r in rows:
            g,i,cycles,codec,b=r.split()
            if int(g)!=gen:continue
            wire=bytes.fromhex(b)
            assert int(i)==len(actual) and wire[:-2]==expect[int(i)],(gen,i,len(wire),len(expect[int(i)]),wire[:40].hex(),expect[int(i)][:40].hex())
            assert binascii.crc_hqx(wire[:-2],65535)==int.from_bytes(wire[-2:],"big")
            actual.append(dict(ready_cycles=int(cycles),codec_cycles=int(codec),wire=wire[:-2].hex()))
        assert len(actual)==len(expect)
        timings[gen]=actual
    (a.out/"sender.json").write_text(json.dumps(timings))
    print(sum(map(len,timings.values())),"independently checked D1 transactions")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("out","board","data","bin"):p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--guards",action="store_true")
    prepare(p.parse_args())
