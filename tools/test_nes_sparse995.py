"""Exercise a partial STOP, missing literal and structurally valid but bad SEAL."""
import argparse
from pathlib import Path
from check_nes_plan975 import directory, packet_path, replay
from nes_raw506 import once
from nes_receiver995 import lua
from nes_sparse995 import encode


def run(temp, phase, case):
    trace = directory(temp, phase, "978returned", "cold")
    cmds, _ = packet_path(trace, 911)
    op = 3 if case == "semantic" else 2
    idx = next(i for i,c in enumerate(cmds) if c[0:2] == (911,op) and
               (op == 3 or bytes.fromhex(c[3])[10:12] == (1322).to_bytes(2,"little")))
    cmds = cmds[:idx+1]
    g,op,clock,wire,bulk,obs,duration = cmds[-1]
    b = bytearray.fromhex(wire)
    if case == "semantic":
        b[36] ^= 1  # version in reconstructed SEAL, outside the E1 identity
        cmds[-1] = (g,op,clock,b.hex(),bulk,obs,duration)
    hdr = bytearray(b[:16])
    compressed = encode(b[16:])
    if case == "truncated":
        compressed = compressed[:-1]
    hdr[11] |= 128
    hdr[12:14] = len(compressed).to_bytes(2,"little")
    compact = hdr+compressed
    def instrument(s):
        s=lua(s)
        key = traces / ("wire995-%04x-%04x-%08x.bin" % (
            g,int.from_bytes(hdr[2:4],"little"),int.from_bytes(hdr[4:8],"little")))
        key.write_bytes(compact)
        if case == "stop":
            s=once(s," if a==0x6001 then", """ if a==0x6001 then
  if packet and canonical995 and pw(8)==911 and word(0xe602)==8 then
   sample516('partial_stop995',64);return 128
  end""")
        return s
    traces=temp/f"nes-sparse995-guard-{case}-p{phase}"
    if case == "stop":
        traces=traces.with_name(traces.name+"-bounded")
    return replay(temp,trace,traces,"fixed",cmds,g,"stop_decode" if case=="stop" else "span",observe=instrument)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("case",choices=("stop","truncated","semantic"))
    a=p.parse_args();run(a.temp,a.phase,a.case)
