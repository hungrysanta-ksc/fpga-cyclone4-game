# SPDX-License-Identifier: MIT
"""Compiled ARM scheduling predicate: ready DMA/credit always returns first."""
import argparse,json,struct
from pathlib import Path
from probe_nes_native289 import Producer
from nes_delta231 import sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    arm=Producer(a.source/'output.elf',None);rows=[]
    for reason,sent,retired,phase,want in ((8,4,0,0,1),(8,3,0,0,0),(8,1,65533,0,1),(8,1,65534,0,0),(4,1,1,0,0),(4,1,0,0,1),(1,0,0,1,0),(1,0,0,0,1),(2,0,0,2,0),(4,4,0,2,0),(0,0,0,0,0)):
        arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',sent,retired))
        arm.uc.mem_write(arm.symbols['phase_ready302'],struct.pack('<I',phase))
        arm.uc.mem_write(arm.symbols['wait_reason302'],struct.pack('<I',reason))
        assert arm.call('work_pending302',[])==want
        rows.append(dict(reason=reason,sent=sent,retired=retired,phase=phase,planner_allowed=want))
    r=dict(passed=True,checks=rows,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),actual_SPI=False)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))


if __name__=='__main__':main()
