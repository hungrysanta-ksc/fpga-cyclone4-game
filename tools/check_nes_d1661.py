"""Check on-wire SPI edges against 660 including truncated and overlong D1."""
import argparse
from pathlib import Path
from check_nes_record657 import bench, check_rows, encode, prepare
from nes_raw506 import once


def run(a):
    def instrument(template):
        s = bench(template, a.guards, False, True, False, False)
        dut = " nes_native_spi165 dut(clk,reset,ss,sck,mosi,selected,miso,valid,ready,data,av,ar,aa,ag,fault);"
        s = once(s, dut, dut + """
 wire sel0,miso0,ready0,av0,aa0,fault0;
 wire [15:0] ag0;
 spi660 oracle(clk,reset,ss,sck,mosi,sel0,miso0,valid,ready0,data,av0,ar,aa0,ag0,fault0);
 always @(negedge clk)if(!reset &&
  {selected,miso,ready,av,aa,ag,fault,dut.read_seen} !==
  {sel0,miso0,ready0,av0,aa0,ag0,fault0,oracle.read_seen})$fatal(1,"SPI 660 cycle mismatch");
""")
        if a.guards:
            s = once(s, '  $fclose(out);$display("PASS652")', """  spi_tx[0]=8'hd1;transfer(14);
  if(dut.read_seen || !fault)$fatal(1,"short D1 accepted");
  transfer(15);if(!dut.read_seen)$fatal(1,"exact D1 rejected");
  transfer(16);if(dut.read_seen)$fatal(1,"long D1 accepted");
  $fclose(out);$display("PASS652")""")
        return (a.base / "nes_native_spi165.sv").read_text().replace("module nes_native_spi165(", "module spi660(", 1) + "\n" + s
    prepare(a, encoder=encode, codec="nes_geometry_sender653.sv", bench=instrument)
    if a.guards:
        check_rows((a.out / "blocks.txt").read_text().splitlines())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for k in ("board", "base", "data", "bin", "out"):
        p.add_argument("--" + k, type=Path, required=True)
    p.add_argument("--guards", action="store_true")
    run(p.parse_args())
