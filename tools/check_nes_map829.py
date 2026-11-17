"""Replay the cartridge transactions and actual ordered 65816 reads on the board RTL."""
from pathlib import Path
import argparse
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]


def vectors(temp, dest):
    groups=("demoB","change","earlyB")
    records=[]
    clips=[(group,"") for group in groups]+[("demoB",p) for p in ("split","one","two")]
    for group,policy in clips:
        for phase in (1,2):
            run=temp/f"nes-tile821-{group}-jointmirror-p{phase}-829ref2{policy}"
            assert json.loads((run/"joint.json").read_bytes())["passed"]
            wire=None
            for line in (run/"reads829.txt").read_text().splitlines():
                kind,*args=line.split()
                if kind=="P":
                    assert wire is None
                    wire=bytes.fromhex(args[0]);reads=[]
                elif kind=="R":
                    reads.append(tuple(int(s,16) for s in args))
                else:
                    assert kind=="A" and wire and wire[:2]==bytes([9,2])
                    ack=bytes.fromhex(args[0])
                    size=16+(len(wire)-16)//18*64
                    assert [a for a,_ in reads]==list(range(size))
                    records.append((wire,reads,ack))
                    wire=None
            assert wire is None
    assert records
    with dest.open("w") as out:
        for wire,reads,ack in records:
            print(len(wire),wire.hex(" "),len(reads),file=out)
            for address,value in reads:print(f"{address:x} {value:x}",file=out)
            print(ack.hex(" "),file=out)
    return len(records)


def prepare(temp,out):
    out.mkdir()
    board=temp/"nes-trial816-board829reserved"
    for name in ("nes_sink_bridge165.sv","nes_sink_bus165.sv","nes_sink_spi165.sv","nes_domain_reset124.sv","sink-program.hex"):
        shutil.copyfile(board/name,out/name)
    for name in ("map829_tb.sv","progress680_tb.sv"):
        shutil.copyfile(ROOT/"tests/nes-functional"/name,out/name)
    count=vectors(temp,out/"stim.txt")
    (out/"job.ps1").write_text("""
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$q='C:/altera_standard/25.1std/questa_fse/win64'
& "$q/vlib.exe" work
if($LASTEXITCODE){throw 'vlib'}
& "$q/vlog.exe" -sv nes_domain_reset124.sv nes_sink_bus165.sv nes_sink_spi165.sv nes_sink_bridge165.sv map829_tb.sv progress680_tb.sv *> compile.log
if($LASTEXITCODE){throw 'vlog'}
foreach($top in 'map829_tb','progress680_tb'){
 & "$q/vsim.exe" -c -lib work $top '+stim=stim.txt' '+lut=lut.txt' -do 'onerror {quit -code 1}; run -all; quit -f' *> "$top.log"
 if($LASTEXITCODE -or !(Select-String -Quiet -Path "$top.log" -Pattern 'PASS')){throw "functional failure $top"}
}
""",encoding="utf-8")
    print(count,"actual compact heads")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("temp",type=Path);p.add_argument("out",type=Path)
    a=p.parse_args();prepare(a.temp,a.out)
