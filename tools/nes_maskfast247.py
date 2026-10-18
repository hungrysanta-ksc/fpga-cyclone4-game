# SPDX-License-Identifier: MIT
"""Expanded diagnostic receiver: group append, unrolled stores and validation.

Same2471 packets and retirement contract. No product/full-board approval.
"""
from pathlib import Path
import argparse, json, shutil
import nes_maskboundary247 as boundary
from nes_delta231 import once, sha

BASE_TRANSFORM = boundary.transform_emit


def transform_emit(s):
    s = BASE_TRANSFORM(s)
    a = s.index(" c.label('coverage_loop212');")
    b = s.index(" c.emit(0x64,0x7c);", a)
    # Keep every pattern validity comparison; amortize index arithmetic.
    s = s[:a]+''' c.absolute(0xac,0x1254)
 c.label('coverage_loop212')
 for i in range(0,16,2):
  c.absolute(0xb9,0x1340+i);c.emit(0x49,255,255);sta(0x70)
  c.long(0xbf,0x400028+i);c.absolute(0x2d,0x70);cond(0xd0,'mark_bad212')
 c.emit(0x98,0x18,0x69,16,0,0xa8,0x8a,0x18,0x69,16,0,0xaa,0xe0,144,0);cond(0xd0,'coverage_loop212')
''' + s[b:]
    return s


def emit_boundary(c):
    def lda(a): c.absolute(0xad,a)
    def sta(a): c.absolute(0x8d,a)
    def imm(v): c.emit(0xa9);c.word(v)
    def cond(op,label): c.emit(op^0x20,3);c.jump(label)
    def call(label): boundary.prior.call(c,label)
    fixes={}
    def table(name):
        fixes[name]=len(c.data)+1;c.long(0xbf,0)
    # DP80 cursor,82 length,84 mask,86 group offset,88 first word offset.
    # DP90..92 is a long pointer into the inactive7F bank. No DB changes.
    # append owns60..7c. service runs after each <=16-byte group, as before.
    c.label('mask247');lda(0x1490);cond(0xd0,'mark_bad212')
    lda(0x120c);c.emit(0xc9,5,0);cond(0x90,'mark_bad212');sta(0x82)
    c.long(0xaf,0x400010);c.emit(0x29,255,0,0xc9,2,0);cond(0xd0,'mark_bad212')
    imm(0x7f);sta(0x92);imm(1);sta(0x80)
    c.label('mask_record247');lda(0x80);c.emit(0x18,0x69,2,0);c.absolute(0xcd,0x82);cond(0xb0,'mark_bad212')
    c.absolute(0xae,0x80);c.long(0xbf,0x400010);c.emit(0x29,255,0)
    c.absolute(0xcd,0x148e);cond(0x90,'mark_bad212');c.emit(0xaa,0x1a);sta(0x148e)
    c.emit(0x8a,0x0a,0x0a,0x0a,0x0a);sta(0x86)
    c.emit(0xda);c.absolute(0xae,0x80);c.long(0xbf,0x400010);c.emit(0xeb,0x29,255,0,0xfa,0xc9,0,0);cond(0xf0,'mark_bad212');sta(0x84)
    c.emit(0xe2,0x20);c.absolute(0x9d,0x1500);c.emit(0xc2,0x20)
    lda(0x80);c.emit(0x18,0x69,2,0);sta(0x80)
    # Validate the complete record before any payload read/store. Nonzero
    # mask gives2..16 bytes. Cursor and240-byte payload cannot wrap16 bits.
    lda(0x84);c.emit(0x0a,0xaa);table('count')
    c.emit(0x18);c.absolute(0x6d,0x80);c.absolute(0xcd,0x82)
    cond(0x90,'mask_size247');cond(0xd0,'mark_bad212')
    c.label('mask_size247');table('geometry');sta(0x88)
    c.emit(0xeb,0x29,255,0);sta(0x74)
    lda(0x88);c.emit(0x29,255,0,0x18);c.absolute(0x6d,0x86);sta(0x88)
    lda(0x86);c.emit(0x18);c.absolute(0x6d,0x1020);c.emit(0x69,0,0x50);sta(0x90)
    c.absolute(0xae,0x80)
    for bit in range(8):
        c.absolute(0x4e,0x84);cond(0x90,f'mask_skip{bit}_247')
        c.emit(0xa0,bit*2,0);c.long(0xbf,0x400010);c.emit(0x97,0x90,0xe8,0xe8)
        c.label(f'mask_skip{bit}_247')
    c.absolute(0x8e,0x80)
    # One span exactly matches repeated word append: internal holes <=14,
    # same section/linear mapping, total map extent <=4096. No outer padding.
    lda(0x88);c.emit(0x18);c.absolute(0x6d,0x1020);c.emit(0x69,0,0x50);sta(0x70)
    lda(0x1034);c.emit(0xeb,0x0a,0x0a,0x0a,0x0a,0x0a,0x0a,0x18,0x69,0,0x60);c.absolute(0x6d,0x88);sta(0x72)
    imm(4);sta(0x60);call('append212');cond(0x90,'mark_bad212')
    call('service');lda(0x1236);cond(0xd0,'mark_ok212')
    lda(0x80);c.absolute(0xcd,0x82);cond(0x90,'mask_record247');c.jump('mark_ok212')
    c.label('manifest247');lda(0x120a);c.absolute(0xcd,0x1490);cond(0xd0,'mark_bad212')
    lda(0x1490);cond(0xf0,'manifest_first247')
    c.emit(0xc9,240,0);cond(0xd0,'mark_bad212');imm(16);c.jump('manifest_size247')
    c.label('manifest_first247');imm(240)
    c.label('manifest_size247');c.absolute(0xcd,0x120c);cond(0xd0,'mark_bad212')
    c.emit(0xa2,0,0);c.absolute(0xac,0x1490)
    c.label('manifest_loop247')
    for i in range(0,16,2):
        c.long(0xbf,0x400010+i);c.absolute(0xd9,0x1500+i);cond(0xd0,'mark_bad212')
    c.emit(0x98,0x18,0x69,16,0,0xa8,0x8a,0x18,0x69,16,0,0xaa)
    c.absolute(0xec,0x120c);cond(0xd0,'manifest_loop247')
    lda(0x1490);c.emit(0x18);c.absolute(0x6d,0x120c);sta(0x1490);c.jump('mark_ok212')
    #1024 immutable bytes, emitted with assembler fixups on every relaxation
    # pass. Table0 is rejected at admission, but defined for deterministic ROM.
    for name in ('count','geometry'):
        fix=fixes[name];c.data[fix:fix+3]=(c.base+len(c.data)).to_bytes(3,'little')
        for mask in range(256):
            bits=[b for b in range(8) if mask>>b&1]
            v=2*len(bits) if name=='count' else (2*bits[0] | ((2*(bits[-1]-bits[0]+1))<<8)) if bits else 0
            c.word(v)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();boundary.transform_emit=transform_emit;boundary.emit_boundary=emit_boundary;boundary.install()
    r=boundary.prior.build(a.out.resolve())
    r.update(candidate='maskfast247_diagnostic',sink_version='2471',seal_bytes=190,
             body_capacity=8032,body_free=8032-r['body_bytes'],lookup_bytes=1024,
             scratch_address='DP80..93',metadata_end=0x1600,scope=__doc__,
             script_sha256=sha(Path(__file__)),runtime_verified=False,implementation_selected=False)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    shutil.copyfile(__file__,a.out/'builder.py')
    print(json.dumps({k:r[k] for k in ('body_bytes','body_free','program_bytes')},indent=2))


if __name__=='__main__':main()
