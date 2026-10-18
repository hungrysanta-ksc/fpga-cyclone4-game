# SPDX-License-Identifier: MIT
"""Port existing16-bit range marking into the5818B receiver's166B validity.

Same2471 wire, exact duplicate detection and coverage, no extra persistent
state. Actual runtime/whole-board results must be supplied separately.
"""
from pathlib import Path
import argparse,json,shutil
import nes_maskbatch247 as batch
import nes_rangemark247 as ranges
from nes_delta231 import sha


def transform(s):
    s=ranges.transform(batch.fast.transform_emit(s),16)
    assert s.count('0x1380')==2
    return s.replace('0x1380','0x1340')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    batch.fast.boundary.transform_emit=transform
    batch.fast.boundary.emit_boundary=batch.emitter()
    batch.fast.boundary.install()
    r=batch.fast.boundary.prior.build(a.out.resolve())
    r.update(candidate='validation247_diagnostic',sink_version='2471',seal_bytes=190,
             body_capacity=8032,body_free=8032-r['body_bytes'],range_mask_bits=16,
             range_table_bytes=34,valid_bytes_per_bank=166,extra_persistent_bytes=0,
             metadata_end=0x1600,scope=__doc__,script_sha256=sha(Path(__file__)),
             runtime_verified=False,implementation_selected=False)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    shutil.copyfile(__file__,a.out/'builder.py')
    print(json.dumps({k:r[k] for k in ('body_bytes','body_free','program_bytes')},indent=2))


if __name__=='__main__':main()
