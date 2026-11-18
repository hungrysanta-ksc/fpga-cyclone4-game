"""Replay actual compact E1 heads on MMC826's unchanged SPI queue."""
import argparse
import shutil
from pathlib import Path

from analyze_nes_map830 import packets
from nes_repeat833 import OUT


def prepare(temp, dest):
    dest.mkdir(parents=True, exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    board=temp/"nes-trial816-board822held"
    for name in ("nes_sink_bridge165.sv","nes_sink_bus165.sv","nes_domain_reset124.sv","nes_sink_spi165.sv"):
        shutil.copyfile(board/name,dest/name)
    shutil.copyfile(OUT/"client/sink-program.hex",dest/"sink-program.hex")
    words=[]
    for phase in (1,2):
        folder=temp/f"nes-tile821-demoB-jointmirror-p{phase}-833stock"
        raw=[p for p in packets(folder) if p[:2]==bytes((9,5))]
        assert len(raw)==6 and all(len(p)==26 for p in raw)
        words.extend(raw)
    (dest/"heads.hex").write_text("\n".join(p.hex(" ") for p in words)+"\n")
    tb=(root/"tests/nes-functional/progress680_tb.sv").read_text()
    common=tb[:tb.index(" initial begin")].replace("module progress680_tb;","module repeat833_tb;")
    (dest/"repeat833_tb.sv").write_text(common+"""
 reg [7:0] heads[0:311],expected[0:25];
 reg [15:0] crc;
 initial begin
  $readmemh("heads.hex",heads);restart();
  for(int j=0;j<12;j++)begin
   crc=c16('hffff,'he1);tx[0]='he1;
   for(int i=0;i<26;i++)begin
    expected[i]=heads[26*j+i];tx[i+1]=expected[i];crc=c16(crc,expected[i]);
   end
   tx[27]=crc[15:8];tx[28]=crc[7:0];transfer(29);
   status();
   if(fault || {rx[3],rx[4]}!=j+1 || {rx[5],rx[6]}!=j)$fatal(1,"premature retirement");
   for(int i=0;i<26;i++)begin
    address='h400000+i;#40;rn=0;#85;
    if(oe||!dir||dout!==expected[i])$fatal(1,"queue byte %d",i);
    rn=1;#65;
   end
   ack[0]=0;ack[1]=9;for(int i=2;i<10;i++)ack[i]=expected[i];
   ack[10]='h65;ack[11]='h9a;publish();status();
   if(fault || !rx[2][1] || {rx[5],rx[6]}!=j+1)$fatal(1,"lost retirement");
   for(int i=0;i<12;i++)if(rx[7+i]!==ack[i])$fatal(1,"wrong receipt");
  end
  $display("PASS833 12 E1 heads, all bytes, 24 E0 snapshots and 12 validated credits");$finish;
 end
 initial begin #6000000;$fatal(1,"watchdog");end
endmodule
""")
    (dest/"job.ps1").write_text("""
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$q='C:/altera_standard/25.1std/questa_fse/win64'
& "$q/vlib.exe" work
if($LASTEXITCODE){throw 'vlib'}
& "$q/vlog.exe" -sv nes_domain_reset124.sv nes_sink_bus165.sv nes_sink_spi165.sv nes_sink_bridge165.sv repeat833_tb.sv *> compile.log
if($LASTEXITCODE){throw 'vlog'}
& "$q/vsim.exe" -c -lib work repeat833_tb -do 'onerror {quit -code 1}; run -all; quit -f' *> sim.log
if($LASTEXITCODE -or !(Select-String -Quiet -Path sim.log -Pattern 'PASS833')){throw 'queue replay failed'}
""")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("dest",type=Path)
    prepare(**vars(p.parse_args()))
