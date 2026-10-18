# SPDX-License-Identifier: MIT
"""Diagnostic2472: exact packed spans and exact zero-RLE manifest together.

Bounded CPU word copy, per-span/per-RLE-run service, ordinary final display
ownership. No new DMA aperture, firmware package or whole-board approval.
"""
from pathlib import Path
import argparse,json,shutil
import nes_validation247 as validation
from nes_delta231 import once,sha

boundary=validation.batch.fast.boundary
BASE_SOURCE=boundary.source


def source(s):
 s=BASE_SOURCE(s).replace('0x71,0x24','0x72,0x24')
 s=once(s,"c.emit(0xc9,10,0);cond(0xf0,'manifest_packet247')", "c.emit(0xc9,10,0);cond(0xf0,'manifest_packet247');c.emit(0xc9,11,0);cond(0xf0,'manifest_packet247')")
 s=once(s,"c.label('manifest_packet247');checkimm(0x1200,0x020a);call(c,'manifest247')", "c.label('manifest_packet247');lda(0x1200);c.emit(0xc9,10,2);cond(0xf0,'manifest_call247');c.emit(0xc9,11,2);cond(0xd0,'bad_packet');c.label('manifest_call247');call(c,'manifest247')")
 s=once(s,'c.absolute(0x9c,0x148e);c.absolute(0x9c,0x1490)', 'c.absolute(0x9c,0x148e);c.absolute(0x9c,0x1490);c.absolute(0x9c,0x1492)')
 return s


def emit(c):
 def lda(a):c.absolute(0xad,a)
 def sta(a):c.absolute(0x8d,a)
 def imm(v):c.emit(0xa9);c.word(v)
 def cond(op,label):c.emit(op^0x20,3);c.jump(label)
 def call(label):boundary.prior.call(c,label)
 fixes=[]
 def prefix():fixes.append(len(c.data)+1);c.long(0xbf,0)
 #80=packet cursor,82=length,84=span bytes,86=start,8a=end;
 #90..92=destination pointer,94..97=pending span. Existing scratch reused.
 c.label('mask247');lda(0x1492);cond(0xd0,'mark_bad212')
 lda(0x120c);c.emit(0xc9,6,0);cond(0x90,'mark_bad212');sta(0x82)
 c.long(0xaf,0x400010);c.emit(0x29,255,0,0xc9,3,0);cond(0xd0,'mark_bad212')
 imm(1);sta(0x80);imm(0x7f);sta(0x92);c.absolute(0x9c,0x96)
 c.label('span_record247');lda(0x80);c.emit(0x18,0x69,3,0);c.absolute(0xcd,0x82);cond(0xb0,'mark_bad212')
 c.absolute(0xae,0x80);c.long(0xbf,0x400010);sta(0x86);c.emit(0x29,1,0);cond(0xd0,'mark_bad212')
 lda(0x86);c.emit(0xc9,0,16);cond(0xb0,'mark_bad212');c.absolute(0xcd,0x148e);cond(0x90,'mark_bad212')
 c.long(0xbf,0x400012);c.emit(0x29,255,0);cond(0xf0,'mark_bad212');c.emit(0xc9,33,0);cond(0xb0,'mark_bad212');c.emit(0x0a);sta(0x84)
 c.emit(0x18);c.absolute(0x6d,0x86);c.emit(0xc9,1,16);cond(0xb0,'mark_bad212');sta(0x8a)
 lda(0x80);c.emit(0x18,0x69,3,0);sta(0x80);c.absolute(0x6d,0x84);c.absolute(0xcd,0x82);cond(0x90,'span_admitted247');cond(0xd0,'mark_bad212')
 c.label('span_admitted247');lda(0x8a);sta(0x148e)
 # Global non-overlap proves each newly set receipt bit is unique.
 lda(0x86);c.emit(0x4a);sta(0x6a);lda(0x84);c.emit(0x4a);sta(0x6c)
 c.label('span_receipt247');lda(0x6a);c.emit(0x29,15,0);sta(0x70)
 imm(16);c.emit(0x38);c.absolute(0xed,0x70);c.absolute(0xcd,0x6c);c.branch(0x90,'span_take247');lda(0x6c)
 c.label('span_take247');sta(0x72)
 lda(0x70);c.emit(0x0a,0xaa);prefix();c.emit(0x49,255,255);sta(0x74)
 lda(0x70);c.emit(0x18);c.absolute(0x6d,0x72);c.emit(0x0a,0xaa);prefix();c.absolute(0x2d,0x74);sta(0x74)
 lda(0x6a);c.emit(0x4a,0x4a,0x4a,0x29,0xfe,0xff,0xaa)
 c.absolute(0xbd,0x1500);c.absolute(0x0d,0x74);c.absolute(0x9d,0x1500)
 lda(0x6a);c.emit(0x18);c.absolute(0x6d,0x72);sta(0x6a);lda(0x6c);c.emit(0x38);c.absolute(0xed,0x72);sta(0x6c);cond(0xd0,'span_receipt247')
 lda(0x86);c.emit(0x18);c.absolute(0x6d,0x1020);c.emit(0x69,0,0x50);sta(0x90)
 c.absolute(0xae,0x80);c.emit(0xa0,0,0);c.label('span_copy247')
 c.long(0xbf,0x400010);c.emit(0x97,0x90,0xe8,0xe8,0xc8,0xc8);c.absolute(0xcc,0x84);c.branch(0xd0,'span_copy247');c.absolute(0x8e,0x80)
 lda(0x96);cond(0xf0,'span_new247');lda(0x86);c.emit(0x38);c.absolute(0xed,0x96);c.emit(0xc9,97,0);cond(0x90,'span_merge247')
 call('batch_flush247');cond(0x90,'mark_bad212')
 c.label('span_new247');lda(0x86);sta(0x94)
 c.label('span_merge247');lda(0x8a);sta(0x96)
 c.label('span_service247');call('service');c.label('span_serviced247');lda(0x1236);cond(0xd0,'mark_ok212')
 lda(0x80);c.absolute(0xcd,0x82);cond(0x90,'span_record247');call('batch_flush247');c.emit(0x60)
 c.label('batch_flush247');lda(0x94);c.emit(0x18);c.absolute(0x6d,0x1020);c.emit(0x69,0,0x50);sta(0x70)
 lda(0x1034);c.emit(0xeb,0x0a,0x0a,0x0a,0x0a,0x0a,0x0a,0x18,0x69,0,0x60);c.absolute(0x6d,0x94);sta(0x72)
 lda(0x96);c.emit(0x38);c.absolute(0xed,0x94);sta(0x74);imm(4);sta(0x60);call('append212');c.emit(0x60)
 #1492 records the chosen manifest kind. Zero-length/mixed-kind fragments
 #cannot open another map lifetime or bypass final256B coverage.
 c.label('manifest247');lda(0x120a);c.absolute(0xcd,0x1490);cond(0xd0,'mark_bad212')
 lda(0x1492);cond(0xf0,'manifest_kind247');c.absolute(0xcd,0x1200);cond(0xd0,'mark_bad212')
 c.label('manifest_kind247');lda(0x1200);sta(0x1492);c.emit(0xc9,10,2);cond(0xf0,'manifest_dense247')
 lda(0x120c);c.emit(0xc9,2,0);cond(0x90,'mark_bad212');sta(0x82)
 c.long(0xaf,0x400010);c.emit(0x29,255,0,0xc9,3,0);cond(0xd0,'mark_bad212')
 imm(1);sta(0x80)
 c.label('manifest_run247');c.absolute(0xae,0x80);c.emit(0xe2,0x20);c.long(0xbf,0x400010);c.emit(0xc2,0x20,0x29,255,0);sta(0x86);c.emit(0x29,127,0,0x1a);sta(0x84)
 c.emit(0x18);c.absolute(0x6d,0x1490);c.emit(0xc9,1,1);cond(0xb0,'mark_bad212')
 c.emit(0xe8);c.absolute(0x8e,0x80);c.absolute(0xac,0x1490);lda(0x86);c.emit(0x29,128,0);cond(0xd0,'manifest_zero247')
 lda(0x80);c.emit(0x18);c.absolute(0x6d,0x84);c.absolute(0xcd,0x82);cond(0x90,'manifest_literal247');cond(0xd0,'mark_bad212')
 c.label('manifest_literal247');c.emit(0xe2,0x20)
 c.label('manifest_literal_loop247');c.long(0xbf,0x400010);c.absolute(0xd9,0x1500);cond(0xd0,'manifest_bad8_247');c.emit(0xe8,0xc8)
 c.absolute(0xce,0x84);c.branch(0xd0,'manifest_literal_loop247');c.emit(0xc2,0x20);c.jump('manifest_ran247')
 c.label('manifest_zero247');c.emit(0xe2,0x20)
 c.label('manifest_zero_loop247');c.absolute(0xb9,0x1500);cond(0xd0,'manifest_bad8_247');c.emit(0xc8);c.absolute(0xce,0x84);c.branch(0xd0,'manifest_zero_loop247');c.emit(0xc2,0x20)
 c.label('manifest_ran247');c.absolute(0x8e,0x80);c.absolute(0x8c,0x1490)
 c.label('manifest_service247');call('service');c.label('manifest_serviced247');lda(0x1236);cond(0xd0,'mark_ok212')
 lda(0x80);c.absolute(0xcd,0x82);cond(0x90,'manifest_run247');c.jump('mark_ok212')
 c.label('manifest_bad8_247');c.emit(0xc2,0x20);c.jump('mark_bad212')
 c.label('manifest_dense247');lda(0x1490);cond(0xf0,'manifest_first247');c.emit(0xc9,240,0);cond(0xd0,'mark_bad212');imm(16);c.jump('manifest_size247')
 c.label('manifest_first247');imm(240)
 c.label('manifest_size247');c.absolute(0xcd,0x120c);cond(0xd0,'mark_bad212');c.emit(0xa2,0,0);c.absolute(0xac,0x1490)
 c.label('manifest_loop247')
 for i in range(0,16,2):c.long(0xbf,0x400010+i);c.absolute(0xd9,0x1500+i);cond(0xd0,'mark_bad212')
 c.emit(0x98,0x18,0x69,16,0,0xa8,0x8a,0x18,0x69,16,0,0xaa);c.absolute(0xec,0x120c);cond(0xd0,'manifest_loop247')
 lda(0x1490);c.emit(0x18);c.absolute(0x6d,0x120c);sta(0x1490);c.jump('mark_ok212')
 for fix in fixes:c.data[fix:fix+3]=(c.base+len(c.data)).to_bytes(3,'little')
 for i in range(17):c.word((1<<i)-1)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 boundary.source=source;boundary.transform_emit=validation.transform;boundary.emit_boundary=emit;boundary.install()
 r=boundary.prior.build(a.out.resolve())
 r.update(candidate='jointdecode247_diagnostic',sink_version='2472',seal_bytes=190,body_capacity=8032,body_free=8032-r['body_bytes'],extra_persistent_bytes=2,scope=__doc__,script_sha256=sha(Path(__file__)),runtime_verified=False,implementation_selected=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');shutil.copyfile(__file__,a.out/'builder.py');print(json.dumps({k:r[k] for k in ('body_bytes','body_free','program_bytes')},indent=2))


if __name__=='__main__':main()
