# SPDX-License-Identifier: MIT
"""Accumulate ordered map spans within a packet; retain per-record service.

Only flush a pending span at a gap>96 or packet end. Same2471 wire, generic
append capacity checks and final coverage/display ownership. No product build.
"""
from pathlib import Path
import argparse,inspect,json,shutil
import nes_maskfast247 as fast
from nes_delta231 import once,sha


def emitter():
 s=inspect.getsource(fast.emit_boundary)
 s=once(s,'imm(1);sta(0x80)','imm(1);sta(0x80);c.absolute(0x9c,0x96)')
 s=once(s,"    c.absolute(0xae,0x80)\n    for bit", "    c.label('profile_copy247');c.absolute(0xae,0x80)\n    for bit")
 s=once(s,'    c.absolute(0x8e,0x80)',"    c.label('profile_copied247');c.absolute(0x8e,0x80)")
 a=s.index('    lda(0x88);c.emit(0x18);c.absolute(0x6d,0x1020)')
 b=s.index("    call('service');",a)
 s=s[:a]+'''    # Pending94=start,96=end; end0 is empty.8a preserves incoming end
    # across generic append's60..7c scratch. Ordered groups prevent overlap.
    c.label('batch_range247');lda(0x88);c.emit(0x18);c.absolute(0x6d,0x74);sta(0x8a)
    lda(0x96);cond(0xf0,'batch_new247')
    lda(0x88);c.emit(0x38);c.absolute(0xed,0x96);c.emit(0xc9,97,0);cond(0x90,'batch_merge247')
    call('batch_flush247');cond(0x90,'mark_bad212')
    c.label('batch_new247');lda(0x88);sta(0x94)
    c.label('batch_merge247');lda(0x8a);sta(0x96);c.label('batch_ranged247')
''' +s[b:]
 s=once(s,"    call('service');lda", "    c.label('profile_service247');call('service');c.label('profile_serviced247');lda")
 s=once(s,"cond(0x90,'mask_record247');c.jump('mark_ok212')", "cond(0x90,'mask_record247');call('batch_flush247');c.emit(0x60)")
 s=once(s,"    c.label('manifest247');", '''    c.label('batch_flush247')
    lda(0x94);c.emit(0x18);c.absolute(0x6d,0x1020);c.emit(0x69,0,0x50);sta(0x70)
    lda(0x1034);c.emit(0xeb,0x0a,0x0a,0x0a,0x0a,0x0a,0x0a,0x18,0x69,0,0x60);c.absolute(0x6d,0x94);sta(0x72)
    lda(0x96);c.emit(0x38);c.absolute(0xed,0x94);sta(0x74)
    imm(4);sta(0x60);call('append212');c.emit(0x60)
    c.label('manifest247');''')
 ns=dict(fast.__dict__);exec(compile(s,'maskbatch247-emitter','exec'),ns);return ns['emit_boundary']


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 fast.boundary.transform_emit=fast.transform_emit;fast.boundary.emit_boundary=emitter();fast.boundary.install()
 r=fast.boundary.prior.build(a.out.resolve())
 r.update(candidate='maskbatch247_diagnostic',sink_version='2471',seal_bytes=190,body_capacity=8032,body_free=8032-r['body_bytes'],lookup_bytes=1024,scratch_address='DP80..97',extra_scratch_bytes=6,metadata_end=0x1600,scope=__doc__,script_sha256=sha(Path(__file__)),runtime_verified=False,implementation_selected=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');shutil.copyfile(__file__,a.out/'builder.py');print(json.dumps({k:r[k] for k in ('body_bytes','body_free','program_bytes')},indent=2))


if __name__=='__main__':main()
