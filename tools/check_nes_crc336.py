# SPDX-License-Identifier: MIT
"""Actual M4 E9 CRC against independent CRC-CCITT, all legal payload lengths."""
import argparse,binascii,json,random
from pathlib import Path
from probe_nes_native289 import Producer
from nes_delta231 import sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);arm=Producer(a.source/'output.elf',None);rng=random.Random(336);cases=0
    for n in range(241):
        for b in (bytes(n),bytes([255])*n,bytes(i&255 for i in range(n)),bytes(rng.randrange(256) for _ in range(n))):
            arm.uc.mem_write(0x20028000,b or b'\0');assert arm.call('plan_crc336',[0x20028000,n])==binascii.crc_hqx(b,65535),(n,b.hex());cases+=1
    out=dict(passed=True,cases=cases,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),scope=__doc__)
    (a.out/'result.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n');print(json.dumps(out))


if __name__=='__main__':main()
