# SPDX-License-Identifier: MIT
"""Paired4882 raw-row/6-plane transport and actual65816 canonical expansion.

The expired ARM BG-key workspace holds compact data. SNES expands only
the inactive candidate, validates the existing canonical tables/coverage, then
uses unchanged DMA/VBlank/final ACK. No retained history or new frame buffer.
"""
import argparse
import inspect
import json
from pathlib import Path
import nes_repeat227 as prior
from check_nes_game478 import sha

original_source=prior.source

def once(s,a,b):
    assert s.count(a)==1,a[:100]
    return s.replace(a,b)

def emit_decode488(c):
    def lda(a):c.absolute(0xad,a)
    def sta(a):c.absolute(0x8d,a)
    def imm(v):c.emit(0xa9);c.word(v)
    def cond(op,label):c.emit(op^0x20,3);c.jump(label)
    c.label('compact488')
    lda(0x1240);cond(0xf0,'compact_ok488')
    lda(0x100a);c.emit(0xc9,0x5a,13);cond(0xf0,'compact_ok488')
    lda(0x1240);c.emit(0xc9,3,0);cond(0xb0,'compact_bad488');sta(0x60)
    imm(8);c.emit(0x38);c.absolute(0xed,0x60);c.emit(0x0a);sta(0x62)
    lda(0x60);c.emit(0x0a,0x0a,0x0a,0x0a,0x0a,0x0a);sta(0x64);c.emit(0x0a,0x18);c.absolute(0x6d,0x64);sta(0x64)
    c.emit(0x18,0x69,0x5a,5);c.absolute(0xcd,0x100a);cond(0xd0,'compact_bad488')
    lda(0x1020);c.emit(0x18,0x69,0x61,0x69);sta(0x70)
    c.emit(0x18);c.absolute(0x6d,0x64);c.emit(0x18,0x69,248,0,0xaa)
    lda(0x1020);c.emit(0x18,0x69,0x59,0x72,0xa8,0x8b);imm(248);c.emit(0x44,0x7f,0x7f,0xab)
    # Preserve the compact prefix and clear only its remaining canonical tail.
    lda(0x70);c.emit(0x18);c.absolute(0x6d,0x64);sta(0x6a);sta(0x2181)
    c.emit(0xe2,0x20);c.store(0x2183,1);c.emit(0xc2,0x20)
    imm(0x8008);sta(0x4300);imm(14);sta(0x4302);imm(0x40);sta(0x4304)
    imm(2048);c.emit(0x38);c.emit(0xe5,0x64);sta(0x4305)
    c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20)
    lda(0x60);c.emit(0xc9,2,0);c.branch(0xd0,'compact_stride_one488');imm(12);c.branch(0x80,'compact_stride488')
    c.label('compact_stride_one488');imm(6)
    c.label('compact_stride488');sta(0x62);lda(0x6a);c.emit(0x38);c.emit(0xe5,0x62);c.emit(0xaa)
    lda(0x70);c.emit(0x18,0x69,0xc0,7,0xa8);imm(32);sta(0x64);c.emit(0x8b)
    c.label('compact_tile488');c.emit(0xe2,0x20,0xa9,0x7f,0x48,0xab,0xc2,0x20);lda(0x60);c.emit(0xc9,2,0);cond(0xd0,'compact_one488')
    for src,dst in [(0,0),(2,2),(4,16),(6,18),(8,32),(10,34)]:c.absolute(0xbd,src);c.absolute(0x99,dst)
    imm(255);c.absolute(0x99,48);c.absolute(0x99,50)
    c.emit(0x98);c.absolute(0xcd,0x6a);cond(0xb0,'compact_advance488');imm(0)
    for plane in range(4):
        for row in range(2,8):c.absolute(0x99,plane*16+row*2)
    c.jump('compact_advance488')
    c.label('compact_one488')
    for src,dst in [(0,0),(2,16),(4,32)]:c.absolute(0xbd,src);c.absolute(0x99,dst)
    imm(255);c.absolute(0x99,48)
    c.emit(0x98);c.absolute(0xcd,0x6a);cond(0xb0,'compact_advance488');imm(0)
    for plane in range(4):
        for row in range(1,8):c.absolute(0x99,plane*16+row*2)
    c.label('compact_advance488');c.emit(0x8a,0x38);c.emit(0xe5,0x62);c.emit(0xaa,0x98,0x38,0xe9,64,0,0xa8,0xab)
    c.absolute(0xce,0x64);lda(0x64);c.emit(0x29,3,0);c.branch(0xd0,'compact_continue488');call(c,'service');lda(0x1236);cond(0xd0,'compact_bad488');lda(0x64);c.branch(0xf0,'compact_done488');c.label('compact_continue488');c.emit(0x8b);c.jump('compact_tile488')
    c.label('compact_done488');imm(3418);sta(0x100a)
    c.label('compact_ok488');c.emit(0x38,0x60)
    c.label('compact_bad488');c.emit(0x18,0x60)

# Use the same builder-local JSR helper; no new assembler dependency.
from nes_native_local165 import call


def source(s):
    s=original_source(s).replace('0x71,0x22','0x82,0x48')
    s=once(s,'compact=rom[:4096];compact[0xfc0:0x1000]=rom[0x7fc0:]','compact=rom[:8192];compact[0x1fc0:0x2000]=rom[0x7fc0:]')
    s=once(s,"call(c,'validate181');cond(0x90,'bad_packet')", "call(c,'compact488');lda(0x1236);cond(0xd0,'stop_packet');cond(0x90,'bad_packet');call(c,'validate181');cond(0x90,'bad_packet')")
    definition='\n'.join(' '+line for line in inspect.getsource(emit_decode488).splitlines())
    return once(s," c.label('service');",definition+"\n emit_decode488(c)\n c.label('service');")

def build(out):
    import nes_dirty212,nes_bulk195
    class Inspector:
        @staticmethod
        def getsource(fn):
            s=inspect.getsource(fn)
            if fn is nes_bulk195.build:
                s=s.replace('0xf60','0x1f60').replace('0xfc0','0x1fc0').replace('0x1000','0x2000')
                s=s.replace('len(compact)==4096','len(compact)==8192').replace('program_bytes=4096','program_bytes=8192').replace('body_capacity=3936,body_free=3936-','body_capacity=8032,body_free=8032-').replace('compact4096_approved=True','compact4096_approved=False')
            return s
    prior.source=source
    oldinspect=nes_dirty212.inspect;nes_dirty212.inspect=Inspector
    oldpriorinspect=prior.inspect;prior.inspect=Inspector
    try:r=prior.build(out)
    finally:prior.source=original_source;nes_dirty212.inspect=oldinspect;prior.inspect=oldpriorinspect
    r.update(candidate='compact488',sink_version='4882',seal_version='4882',new_SNES_context_bytes_used=0,new_frame_buffer_B=0,temporary_ARM_BG_workspace_B=384,temporary_SNES_staging_tail_B=0,program_ROM_growth_B=4096,scope=__doc__)
    assert (out/'sink165.sfc').read_bytes()[0x1fbe]==255
    (out/'build.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    return r

def prepare(arm,out):
    assert sha(arm/'obj-nes-100/firmware.stm')=='e8062b78ff046d6b7b2f0c5ff25c0d95ef26fca709deb4885adcebf9b8d8492d'
    out.mkdir(parents=True,exist_ok=False);patch=out/'patch';patch.mkdir()
    originals={}
    for name in ['nes_native_sink165.c','nes_native_sink165.h']:
        p=arm/name;s=p.read_text(encoding='utf8');originals[name]=sha(p)
        # Explicit mutable lifetime: the expired BG-key half becomes packet scratch.
        s=s.replace('nes_sink212_seal(struct nes_native_sink165 *s,const struct nes_native_video165 *p,','nes_sink212_seal(struct nes_native_sink165 *s,struct nes_native_video165 *p,')
        s=s.replace('nes_sink212_seal(struct nes_native_sink165 *,const struct nes_native_video165 *,','nes_sink212_seal(struct nes_native_sink165 *,struct nes_native_video165 *,')
        if name.endswith('.c'):
            s=s.replace('0x2271','0x4882')
            s=once(s,'  const uint8_t *parts[4]={p->patch.chr,', '''  /* Canonical raw CHR remains intact; compact bytes use expired BG keys.
   * Mode/enable/size retain their canonical positions after the2048B array. */
  unsigned packed=2048;const uint8_t *raw=p->patch.chr;
  if(p->patch_count<=2){
   uint8_t *out=(uint8_t *)p->bg_keys+4096;packed=0;
   for(unsigned tile=0;tile<32;tile++)for(unsigned plane=0;plane<3;plane++)for(unsigned row=0;row<p->patch_count;row++)
    for(unsigned bit=0;bit<2;bit++)out[packed++]=p->patch.chr[tile*64+plane*16+row*2+bit];
   raw=out;
  }
  const uint8_t *parts[4]={raw,''')
            s=once(s,'const unsigned lengths[4]={2048,81,81,81};','const unsigned lengths[4]={packed,81,81,81};')
        (patch/name).write_text(s,encoding='utf8',newline='\n')
    r={'scope':__doc__,'baseline_firmware_SHA256':sha(arm/'obj-nes-100/firmware.stm'),'baseline_sources':originals,'patch_sources':{p.name:sha(p) for p in patch.iterdir()},'hardware_ready':False,'new_frame_buffer_B':0}
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--arm',type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.arm,a.out) if a.arm else build(a.out)))
