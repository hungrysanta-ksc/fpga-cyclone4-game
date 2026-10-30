# SPDX-License-Identifier: MIT
"""Paired4891 raw-row/6-plane transport and actual65816 strided VRAM reconstruction.

Plane/row-major low-plane payload feeds actual strided VRAM DMA. Semantic
checks address compact tables directly. Two bank bytes certify implicit planes
only; invalidate before mutation and certify in the final display commit.
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

def emit_decode489(c):
    def lda(a):c.absolute(0xad,a)
    def sta(a):c.absolute(0x8d,a)
    def imm(v):c.emit(0xa9);c.word(v)
    def cond(op,label):c.emit(op^0x20,3);c.jump(label)
    c.label('compact489');c.absolute(0x9c,0x1258);c.absolute(0x9c,0x125c);imm(0x7161);sta(0x125e)
    lda(0x1240);cond(0xf0,'compact_ok489')
    lda(0x100a);c.emit(0xc9,0x5a,13);c.branch(0xd0,'compact_rows489')
    c.absolute(0xae,0x1034);c.emit(0xe2,0x20);c.absolute(0x9e,0x125a);c.emit(0xc2,0x20);c.jump('compact_ok489')
    c.label('compact_rows489');lda(0x1240);c.emit(0xc9,3,0);cond(0xb0,'compact_bad489')
    c.emit(0x0a,0x0a,0x0a,0x0a,0x0a,0x0a);sta(0x64);c.emit(0x0a,0x18);c.absolute(0x6d,0x64);sta(0x1258)
    c.emit(0x18,0x69,0x5a,5);c.absolute(0xcd,0x100a);cond(0xd0,'compact_bad489')
    lda(0x1258);c.emit(0x18,0x69,0x61,0x69);sta(0x125e)
    # A different implicit pattern invalidates the bank BEFORE any VRAM write.
    c.absolute(0xae,0x1034);c.emit(0xe2,0x20);c.absolute(0xbd,0x125a);c.absolute(0xcd,0x1240);c.branch(0xd0,'compact_invalidate489')
    c.emit(0xc2,0x20);imm(1);sta(0x125c);c.jump('compact_tables489')
    c.label('compact_invalidate489');c.emit(0xc9,0x80);c.branch(0xd0,'compact_unknown489');c.emit(0xc2,0x20);imm(2);sta(0x125c);c.emit(0xe2,0x20);c.label('compact_unknown489');c.absolute(0x9e,0x125a);c.emit(0xc2,0x20)
    c.label('compact_tables489');imm(3418);sta(0x100a)
    c.label('compact_ok489');c.emit(0x38,0x60)
    c.label('compact_bad489');c.emit(0x18,0x60)

# Use the same builder-local JSR helper; no new assembler dependency.
from nes_native_local165 import call

def emit_raw_dma489(c):
    def lda(a):c.absolute(0xad,a)
    def sta(a):c.absolute(0x8d,a)
    def imm(v):c.emit(0xa9);c.word(v)
    def cond(op,label):c.emit(op^0x20,3);c.jump(label)
    c.label('raw_dma489');c.emit(0x4a);sta(0x74);sta(0x76);sta(0x2116)
    lda(0x125c);c.branch(0xd0,'raw_initialized489')
    # Explicit zero fill uses the held SEAL reserved byte, not WRAM->WRAM DMA.
    imm(0x1809);sta(0x4300);imm(14);sta(0x4302);imm(0x40);sta(0x4304);imm(2048);sta(0x4305)
    c.emit(0xe2,0x20);c.store(0x2115,0x80);c.store(0x420b,1);c.emit(0xc2,0x20)
    c.label('raw_initialized489')
    lda(0x1020);c.emit(0x18,0x69,0x61,0x69);sta(0x4302);imm(0x7f);sta(0x4304);imm(0x1801);sta(0x4300)
    c.emit(0xe2,0x20);c.store(0x2115,0x81);c.emit(0xc2,0x20);imm(3);sta(0x66)
    c.label('raw_pair489');lda(0x1240);sta(0x68)
    c.label('raw_row489');call(c,'raw_service489');cond(0x90,'raw_return489')
    lda(0x76);sta(0x2116);imm(64);sta(0x4305);c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20)
    c.absolute(0xee,0x76);c.absolute(0xce,0x68);c.branch(0xd0,'raw_row489')
    lda(0x76);c.emit(0x38);c.absolute(0xed,0x1240);c.emit(0x18,0x69,8,0);sta(0x76);c.absolute(0xce,0x66);c.branch(0xd0,'raw_pair489')
    lda(0x125c);c.emit(0xc9,1,0);c.branch(0xf0,'raw_return489')
    # Plane6=1, plane7=0 for used rows; all other bytes remain zero.
    imm(0x1808);sta(0x4300);imm(0x93be);sta(0x4302);imm(0);sta(0x4304)
    c.emit(0xe2,0x20);c.store(0x2115,1);c.emit(0xc2,0x20);lda(0x1240);sta(0x68)
    c.label('raw_high489');call(c,'raw_service489');cond(0x90,'raw_return489')
    lda(0x76);sta(0x2116);imm(32);sta(0x4305);c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20)
    c.absolute(0xee,0x76);c.absolute(0xce,0x68);c.branch(0xd0,'raw_high489')
    c.label('raw_return489');c.emit(0xe2,0x20);c.store(0x2115,0x80);c.emit(0xc2,0x20,0x60)
    c.label('raw_boot489')
    # Only once, before first packet, while forced blank. Certify both banks zero.
    imm(0x1809);sta(0x4300);imm(0xffd6);sta(0x4302);imm(0);sta(0x4304)
    c.emit(0xe2,0x20);c.store(0x2115,0x80);c.emit(0xc2,0x20)
    for dest in [0x2800,0x4800]:
        imm(dest);sta(0x2116);imm(2048);sta(0x4305);c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20)
    imm(0x8080);sta(0x125a);c.emit(0x60)
    c.label('raw_service489');call(c,'service');lda(0x1236);c.branch(0xd0,'raw_stop489');c.emit(0x38,0x60)
    c.label('raw_stop489');c.emit(0xe2,0x20);c.store(0x1025,0xe4);c.emit(0xc2,0x20,0x18,0x60)

def emit_upload489(c,prefix='upload165'):
    import nes_dirty212
    s=inspect.getsource(nes_dirty212.emit_upload)
    s=once(s,"sta(0x72);imm(2048);sta(0x74);call(c,'append212')", """sta(0x72);imm(2048);sta(0x74)
 lda(0x1258);c.branch(0xf0,'raw_charge_ready489')
 lda(0x125c);c.emit(0xc9,2,0);c.branch(0xf0,'raw_zero_charge489');c.emit(0xc9,1,0);c.branch(0xf0,'raw_warm_charge489')
 lda(0x1240);c.emit(0xc9,2,0);c.branch(0xd0,'raw_charge_one489');imm(3264);c.branch(0x80,'raw_charge489')
 c.label('raw_charge_one489');imm(2656);c.branch(0x80,'raw_charge489')
 c.label('raw_zero_charge489');lda(0x1240);c.emit(0xc9,2,0);c.branch(0xd0,'raw_zero_one489');imm(1120);c.branch(0x80,'raw_charge489')
 c.label('raw_zero_one489');imm(512);c.branch(0x80,'raw_charge489')
 c.label('raw_warm_charge489');lda(0x1240);c.emit(0xc9,2,0);c.branch(0xd0,'raw_warm_one489');imm(864);c.branch(0x80,'raw_charge489')
 c.label('raw_warm_one489');imm(384)
 c.label('raw_charge489');sta(0x74)
 c.label('raw_charge_ready489');call(c,'append212')""")
    s=once(s," c.long(0xbf,0x7e4000);sta(0x4302)", """ lda(0x1258);c.branch(0xf0,'raw_legacy489')
 c.long(0xbf,0x7e4002);c.emit(0xc9,0,0x50);c.branch(0xf0,'raw_dispatch489');c.emit(0xc9,0,0x90);c.branch(0xd0,'raw_legacy489')
 c.label('raw_dispatch489');call(c,'raw_dma489');lda(0x1236);cond(0xd0,'upload_return212');c.jump('raw_advance489')
 c.label('raw_legacy489');c.long(0xbf,0x7e4000);sta(0x4302)""")
    s=once(s," c.emit(0xc2,0x20);lda(0x1252);", " c.emit(0xc2,0x20);c.label('raw_advance489');lda(0x1252);")
    s=once(s,' client.emit_extra(c)',' client.emit_extra(c)\n emit_raw_dma489(c)')
    import nes_client181
    extra=inspect.getsource(nes_client181.emit_extra)
    assert extra.count('c.emit(0x18,0x69);c.word(0x7161)')==2 and extra.count('c.emit(0x18,0x69);c.word(0x7203)')==1
    extra=extra.replace('c.emit(0x18,0x69);c.word(0x7161)', 'c.emit(0x18);c.absolute(0x6d,0x125e)')
    extra=extra.replace('c.emit(0x18,0x69);c.word(0x7203)', 'c.emit(0x18);c.absolute(0x6d,0x125e);c.emit(0x18,0x69,162,0)')
    ens=dict(nes_client181.__dict__);exec(compile(extra,'489-semantic-pointers','exec'),ens)
    class Client:
        emit_extra=staticmethod(ens['emit_extra'])
    ns=dict(nes_dirty212.__dict__);ns.update(emit_raw_dma489=emit_raw_dma489,client=Client)
    exec(compile(s,'compact489-upload','exec'),ns)
    return ns['emit_upload'](c,prefix)

def source(s):
    s=original_source(s).replace('0x71,0x22','0x91,0x48')
    s=once(s,'compact=rom[:4096];compact[0xfc0:0x1000]=rom[0x7fc0:]','compact=rom[:5120];compact[0x13c0:0x1400]=rom[0x7fc0:]')
    s=once(s,"call(c,'validate181');cond(0x90,'bad_packet')", "call(c,'compact489');lda(0x1236);cond(0xd0,'stop_packet');cond(0x90,'bad_packet');call(c,'validate181');cond(0x90,'bad_packet')")
    s=once(s," call(c,'maps181')"," c.absolute(0x9c,0x125a);call(c,'maps181');call(c,'raw_boot489')")
    s=once(s," lda(0x1240);sta(0x1242)", """ lda(0x1240);sta(0x1242);c.branch(0xf0,'raw_commit_done489')
 c.absolute(0xae,0x1034);c.emit(0xe2,0x20);lda(0x1258);c.branch(0xf0,'raw_commit489');lda(0x1240)
 c.label('raw_commit489');c.absolute(0x9d,0x125a);c.emit(0xc2,0x20)
 c.label('raw_commit_done489')""")
    definition='\n'.join(' '+line for line in inspect.getsource(emit_decode489).splitlines())
    return once(s," c.label('service');",definition+"\n emit_decode489(c)\n c.label('service');")

def build(out):
    import nes_dirty212,nes_bulk195
    class Inspector:
        @staticmethod
        def getsource(fn):
            s=inspect.getsource(fn)
            if fn is nes_bulk195.build:
                s=s.replace('0xf60','0x1360').replace('0xfc0','0x13c0').replace('0x1000','0x1400')
                s=s.replace('len(compact)==4096','len(compact)==5120').replace('program_bytes=4096','program_bytes=5120').replace('body_capacity=3936,body_free=3936-','body_capacity=4960,body_free=4960-').replace('compact4096_approved=True','compact4096_approved=False')
            if fn is nes_dirty212.build:
                s=once(s,'from nes_dirty212 import emit,emit_upload;from nes_client181 import call,OFFSETS,LIMITS','from nes_dirty212 import emit;from nes_output489 import emit_upload489 as emit_upload;from nes_client181 import call,OFFSETS,LIMITS')
            return s
    prior.source=source
    oldinspect=nes_dirty212.inspect;nes_dirty212.inspect=Inspector
    oldpriorinspect=prior.inspect;prior.inspect=Inspector
    try:r=prior.build(out)
    finally:prior.source=original_source;nes_dirty212.inspect=oldinspect;prior.inspect=oldpriorinspect
    r.update(candidate='compact489',sink_version='4891',seal_version='4891',new_SNES_context_bytes_used=8,new_frame_buffer_B=0,temporary_ARM_BG_workspace_B=384,program_ROM_growth_B=1024,new_persistent_RAM_B=2,new_frame_context_B=6,scope=__doc__)
    assert (out/'sink165.sfc').read_bytes()[0x13be]==255 and (out/'sink165.sfc').read_bytes()[0x7fd6]==0
    (out/'build.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    return r

def prepare(arm,out):
    assert sha(arm/'obj-nes-100/firmware.stm')=='e8062b78ff046d6b7b2f0c5ff25c0d95ef26fca709deb4885adcebf9b8d8492d'
    out.mkdir(parents=True,exist_ok=False);patch=out/'patch';patch.mkdir()
    originals={}
    for name in ['nes_native_sink165.c','nes_native_sink165.h']:
        p=arm/name;s=p.read_text(encoding='utf8');originals[name]=sha(p)
        # Expired BG workspace is temporary; canonical raw CHR is preserved.
        s=s.replace('nes_sink212_seal(struct nes_native_sink165 *s,const struct nes_native_video165 *p,','nes_sink212_seal(struct nes_native_sink165 *s,struct nes_native_video165 *p,')
        s=s.replace('nes_sink212_seal(struct nes_native_sink165 *,const struct nes_native_video165 *,','nes_sink212_seal(struct nes_native_sink165 *,struct nes_native_video165 *,')
        if name.endswith('.c'):
            s=s.replace('0x2271','0x4891')
            s=once(s,'  const uint8_t *parts[4]={p->patch.chr,', '''  /* Canonical raw CHR remains intact; compact bytes use expired BG keys.
   * Mode/enable/size retain their canonical positions after the2048B array. */
  unsigned packed=2048;const uint8_t *raw=p->patch.chr;
  if(p->patch_count<=2){
   uint8_t *out=(uint8_t *)p->bg_keys+4096;packed=0;
   for(unsigned plane=0;plane<3;plane++)for(unsigned row=0;row<p->patch_count;row++)for(unsigned tile=0;tile<32;tile++)
    for(unsigned bit=0;bit<2;bit++)out[packed++]=p->patch.chr[tile*64+plane*16+row*2+bit];
   raw=out;
  }
  const uint8_t *parts[4]={raw,''')
            s=once(s,'const unsigned lengths[4]={2048,81,81,81};','const unsigned lengths[4]={packed,81,81,81};')
        (patch/name).write_text(s,encoding='utf8',newline='\n')
    for name in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
        f=arm/name;originals[name]=sha(f);s=f.read_text(encoding='utf8')
        if name=='VERSION':
            assert 'NES-GAME227-DEV'in s;s=s.replace('NES-GAME227-DEV','NES-GAME489-DEV')
        else:
            assert '485'in s;s=s.replace('485','489')
        (patch/name).write_text(s,encoding='utf8',newline='\n')
    r={'scope':__doc__,'baseline_firmware_SHA256':sha(arm/'obj-nes-100/firmware.stm'),'baseline_sources':originals,'patch_sources':{p.name:sha(p) for p in patch.iterdir()},'hardware_ready':False,'new_frame_buffer_B':0}
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--arm',type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.arm,a.out) if a.arm else build(a.out)))
