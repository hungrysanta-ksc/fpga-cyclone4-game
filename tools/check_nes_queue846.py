"""Exercise four queued OAM/SEAL heads and each invalid receipt on MMC826 RTL."""
import argparse
from pathlib import Path
from analyze_nes_section841 import folder, packets
from check_nes_queue845 import prepare as fixture


def prepare(dest):
    fixture(dest)
    data = packets(folder(1,"846safeboot"))[-4:]
    assert [(p[0],p[1]) for p in data] == [(2,4),(8,4),(4,4),(3,0)]
    (dest/"heads.hex").write_text("\n".join(p.ljust(256,b"\0").hex(" ") for p in data)+"\n")
    tb = dest/"repeat833_tb.sv"
    s = tb.read_text().replace("bytes845[0:767]","bytes845[0:1023]")
    s = s.replace("failat<4","failat<5").replace("i<3","i<4").replace("i==2","i==3")
    s = s.replace("{rx[3],rx[4]}!=3","{rx[3],rx[4]}!=4")
    s = s.replace("PASS845 queued palette DATA and RLE then SEAL, three wrong identities blocked, final ACK checked",
                  "PASS846 OAM DATA/pattern/RLE and SEAL, four bad identities blocked, final ACK checked")
    tb.write_text(s,newline="\n")
    job = dest/"job.ps1"
    job.write_text(job.read_text().replace("PASS845","PASS846"),newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("dest",type=Path)
    prepare(p.parse_args().dest)
