# SPDX-License-Identifier: MIT
"""Add zero-byte timing labels to the frozen fast receiver, proving byte equality."""
from pathlib import Path
import argparse,inspect,json,shutil
import nes_maskfast247 as fast
from nes_delta231 import once,sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True)
    a=p.parse_args();s=inspect.getsource(fast.emit_boundary)
    s=once(s,"    c.absolute(0xae,0x80)\n    for bit", "    c.label('profile_copy247');c.absolute(0xae,0x80)\n    for bit")
    s=once(s,"    c.absolute(0x8e,0x80)","    c.label('profile_copied247');c.absolute(0x8e,0x80)")
    s=once(s,"call('append212');cond", "c.label('profile_append247');call('append212');c.label('profile_appended247');cond")
    s=once(s,"    call('service');lda", "    c.label('profile_service247');call('service');c.label('profile_serviced247');lda")
    ns=dict(fast.__dict__);exec(compile(s,'maskprofile247-emitter','exec'),ns)
    fast.boundary.transform_emit=fast.transform_emit;fast.boundary.emit_boundary=ns['emit_boundary'];fast.boundary.install()
    r=fast.boundary.prior.build(a.out.resolve())
    for name in ('body.bin','sink-program.hex','sink165.sfc'):
        assert (a.out/name).read_bytes()==(a.baseline/name).read_bytes(),name
    r.update(candidate='maskprofile247_labels_only',byte_exact=True,scope=__doc__,baseline_sha256=sha(a.baseline/'result.json'),script_sha256=sha(Path(__file__)))
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');shutil.copyfile(__file__,a.out/'builder.py')
    print('PASS zero-byte labels; body/ROM exact5775B receiver')


if __name__=='__main__':main()
