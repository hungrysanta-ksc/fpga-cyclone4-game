# SPDX-License-Identifier: MIT
"""489-compatible bounded word expansion and local-plan query consolidation.

No protocol/CRC/coverage/credit/final-ACK change. STOP service remains <=64B.
Experimental recipe; selection requires full schedule and ownership evidence.
"""
import argparse,json
from pathlib import Path
import nes_output489 as prior
from nes_native_local165 import call
from check_nes_game478 import sha

def once(s,a,b):
    assert s.count(a)==1,a[:80]
    return s.replace(a,b)

def emit_repeat491(c):
    def lda(a):c.absolute(0xad,a)
    def sta(a):c.absolute(0x8d,a)
    def imm(v):c.emit(0xa9);c.word(v)
    def cond(op,label):c.emit(op^0x20,3);c.jump(label)
    c.label('repeat491');c.emit(0xc2,0x20)
    # Read BOTH encoded bytes before mutation; preserve the complete word.
    c.long(0xaf,0x400010);sta(0x64);c.emit(0xe2,0x20);sta(0x2180)
    lda(0x65);sta(0x2180);c.emit(0xc2,0x20)
    lda(0x120c);c.emit(0x38,0xe9,2,0);sta(0x60)
    lda(0x7a);c.emit(0x18,0x69,2,0);sta(0x66)
    call(c,'service');lda(0x1236);cond(0xd0,'repeat_return491')
    c.label('repeat_loop491');lda(0x60);cond(0xf0,'repeat_return491')
    c.emit(0xc9,65,0);c.branch(0x90,'repeat_chunk491');imm(64)
    c.label('repeat_chunk491');sta(0x62)
    # Equal byte words use fixed-source DMA; other words overlap-MVN from seed.
    c.emit(0xe2,0x20);lda(0x64);c.absolute(0xcd,0x65);c.emit(0xc2,0x20);c.branch(0xd0,'repeat_word491')
    lda(0x66);sta(0x2181);imm(0x8008);sta(0x4300);imm(16);sta(0x4302)
    c.emit(0xe2,0x20);c.store(0x2183,1);c.store(0x4304,0x40);c.emit(0xc2,0x20);lda(0x62);sta(0x4305)
    c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20);c.branch(0x80,'repeat_done491')
    c.label('repeat_word491');c.emit(0x8b);lda(0x66);c.emit(0xa8,0x38,0xe9,2,0,0xaa)
    lda(0x62);c.emit(0x3a,0x54,0x7f,0x7f,0xab)
    c.label('repeat_done491');lda(0x66);c.emit(0x18);c.absolute(0x6d,0x62);sta(0x66)
    lda(0x60);c.emit(0x38);c.absolute(0xed,0x62);sta(0x60)
    call(c,'service');lda(0x1236);cond(0xd0,'repeat_return491');c.jump('repeat_loop491')
    c.label('repeat_return491');c.emit(0x60)

def build(out):
    previous=prior.original_source
    def source(s):
        s=previous(s)
        a=s.index(' c.absolute(0xac,0x120c);c.emit(0xa2,32,0);')
        b=s.index(" c.label('literal1814')",a)
        s=s[:a]+" call(c,'repeat491');call(c,'service');lda(0x1236);c.emit(0xc2,0x20);cond(0xd0,'stop_packet');c.jump('accepted')\n"+s[b:]
        s=once(s," c.label('quiet');call(c,'service');c.jump('quiet')", " c.label('quiet');call(c,'service');c.jump('quiet')\n emit_repeat491(c)")
        return 'from nes_consume491 import emit_repeat491\n'+s
    prior.original_source=source
    try:r=prior.build(out)
    finally:prior.original_source=previous
    r.update(candidate='consume491',scope=__doc__,unchanged_ABI='4891',word_expansion_max_chunk_B=64,new_RAM_B=0)
    (out/'build.json').write_text(json.dumps(r,indent=2)+'\n');return r

def prepare(arm,out):
    assert sha(arm/'obj-nes-100/firmware.stm')=='dbeb479a7f8a2ec3906a3f76effc9069796c3b6144bde5345f59396642de9b65'
    out.mkdir(parents=True,exist_ok=False);patch=out/'patch';patch.mkdir()
    name='nes_plan_service200.c';s=(arm/name).read_text()
    old=' if(p->early&&p->window){uint8_t flags;if(!poll(p,&flags,NES_PLAN215_FLUSH))return false;}'
    s=once(s,old,''' /*491 Local append owns no new FPGA work. Keep first BG flush, full
  * buffer flush and finish/retire polling as the actual supply boundaries. */''')
    (patch/name).write_text(s,encoding='utf8',newline='\n')
    r={'scope':__doc__,'baseline_SHA256':sha(arm/'obj-nes-100/firmware.stm'),'patch_sources':{name:sha(patch/name)},'new_RAM_B':0,'experimental':True}
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--arm',type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.arm,a.out) if a.arm else build(a.out)))
