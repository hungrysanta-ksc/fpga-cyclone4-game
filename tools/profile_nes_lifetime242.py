# SPDX-License-Identifier: MIT
"""Validate a future RF write-elision rule, not a new fitted encoder.

FSTORE's old_byte/byte_at are not consumed on the cold or buffered map/raster
path. MAPLVALUE/RASTERVALUE overwrite them before LITERAL; subsequent direct
FSTORE does so too. Keep the direct-region writes. Check byte/cycle exactness
and initialization with the same real71 and synthetic fault/stall workloads.
"""
from pathlib import Path
import json, shutil, sys
from nes_delta231 import ROOT,sha
from nes_operand242 import instrument


def prune(source):
    old="     old_byte<=base_q;byte_at<=cursor;cursor<=cursor+1'b1;"
    new="     if(!cold&&cursor>=2112&&(cursor<3872||cursor>=5664))begin old_byte<=base_q;byte_at<=cursor;end\n     cursor<=cursor+1'b1;"
    assert source.count(old)==1
    return source.replace(old,new)


def main():
    guard='--guards' in sys.argv
    if guard:sys.argv.remove('--guards');import test_nes_operand242 as runner
    else:import profile_nes_source242 as runner
    out=Path(sys.argv[sys.argv.index('--out')+1])
    runner.instrument=lambda source:instrument(prune(source))
    try:runner.main()
    finally:
        if out.exists():shutil.copyfile(Path(__file__),out/'observer'/Path(__file__).name)
    f=out/'result.json';r=json.loads(f.read_text())
    r.update(lifetime_write_elision=True,lifetime_runner_sha256=sha(Path(__file__)),
             scope=__doc__,new_datapath=False,new_fit=False,physical=False)
    f.write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
