# SPDX-License-Identifier: MIT
"""Every CRC state/input byte pair through the actual Cortex-M4 ELF."""
import argparse,json,shutil
from pathlib import Path
from probe_nes_arm264 import ARM
from nes_delta231 import sha


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    shutil.copyfile(a.source/'output.elf',d/'output.elf');arm=ARM(d/'output.elf',None)
    minimum=10**9;maximum=0
    for state in range(256):
        for byte in range(256):
            expected=state^byte
            for _ in range(8):expected=((expected<<1)^7 if expected&128 else expected<<1)&255
            before=arm.instructions;actual=arm.call('crc_byte283',[state,byte]);used=arm.instructions-before
            assert actual==expected,(state,byte,actual,expected)
            minimum=min(minimum,used);maximum=max(maximum,used)
    result=dict(passed=True,pairs=65536,instructions_per_call=[minimum,maximum],ELF_sha256=sha(d/'output.elf'),script_sha256=sha(Path(__file__)),hardware_cycles=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
