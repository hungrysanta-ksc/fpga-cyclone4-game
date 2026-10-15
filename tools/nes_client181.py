# SPDX-License-Identifier: MIT
"""Paired1812 mailbox client candidate. No deployed180 files are modified.

Normal frames retain local differences. A raw frame (or exit from raw mode)
uses inactive VRAM; palette/OAM/three HDMA channels switch at final vblank.
All receive and display acknowledgements are emitted by the real65816 code.
"""
from pathlib import Path
import argparse, inspect, json, types
import nes_boot172 as boot
import nes_banked169 as banked
import nes_native_local165 as old
from nes_clip178 import replace, client_source

OFFSETS=old.OFFSETS
LIMITS=(*old.LIMITS[:5],3418)
call=old.call


def emit(c, prefix='local165', service=None):
    source=inspect.getsource(old.emit)
    # Raw payload is not a visible delta: validate sizes with the existing
    # routine, then choose the inactive-bank path before comparing any bytes.
    source=replace(source," # Setup each region; source bank is always SNES WRAM7F.",""" lda(0x1240);c.absolute(0x0d,0x1242);cond(0xd0,'budget')
 # Setup each region; source bank is always SNES WRAM7F.""")
    namespace=dict(old.__dict__);namespace['LIMITS']=LIMITS
    exec(compile(source,'client181-local','exec'),namespace)
    return namespace['emit'](c,prefix,service)


def emit_upload(c,prefix='upload165'):
    source=inspect.getsource(banked.emit_upload)
    # Replace both legacy unbounded waits with the serviced bounded wait.
    upload=inspect.getsource(old.emit_upload)
    begin=upload.index(" c.absolute(0xad,0x1024);cond(0xf0,'blank_ready')")
    end=upload.index(" label('blank_ready');",begin)
    upload=upload[:begin]+" c.emit(0xc2,0x20);call(c,'wait169');cond(0x90,'return');c.emit(0xe2,0x20)\n"+upload[end:]
    begin=upload.index(" c.absolute(0xad,0x1024);cond(0xd0,'scroll')")
    end=upload.index(" label('scroll')",begin)
    upload=upload[:begin]+" c.absolute(0xad,0x1024);cond(0xd0,'scroll');c.emit(0xc2,0x20);call(c,'wait169');cond(0x90,'return');c.emit(0xe2,0x20)\n"+upload[end:]
    upload=replace(upload," label('scroll')"," label('scroll');call(c,'display181')")
    upload=replace(upload," c.store(0x420c,2);c.store(0x2100,15);c.store(0x1025,3)",
                   " call(c,'hdma181');c.store(0x2100,15);c.store(0x1025,3)")
    source=replace(source,'source=inspect.getsource(old.emit_upload)','source=UPLOAD')
    # Fourth region is raw CHR. It is never a logical normal-tile delta.
    source=replace(source,"c.absolute(0xbd,0x1000);c.emit(0x38);c.absolute(0xed,0x1038)",
                   "c.absolute(0xbd,0x1000);c.emit(0xe0,6,0);cond(0xd0,'normal_size181');lda(0x1240);cond(0xf0,'large_next169');imm(2048);c.label('normal_size181');c.emit(0x38);c.absolute(0xed,0x1038)")
    source=replace(source,"lda(0x1034);c.emit(0x0a);sta(0x1072);c.emit(0x0a,0x18);c.absolute(0x6d,0x1072);c.absolute(0x6d,0x1036)",
                   "lda(0x1034);c.emit(0x0a,0x0a,0x0a,0x18);c.absolute(0x6d,0x1036)")
    source=replace(source,"c.emit(0xc9,6,0);cond(0x90,'large_region169')","c.emit(0xc9,8,0);cond(0x90,'large_region169')")
    source=replace(source,"([0,0x4000,0x5000],srcfix)","([0,0x4000,0x5000,0x6961],srcfix)")
    source=replace(source,"([0,0x4000,0x6000,0xc000,0x8000,0xa000],dstfix)",
                   "([0,0x4000,0x6000,0x5000,0xc000,0x8000,0xa000,0x9000],dstfix)")
    namespace=dict(banked.__dict__);namespace['UPLOAD']=upload
    exec(compile(source,'client181-upload','exec'),namespace)
    result=namespace['emit_upload'](c,prefix)
    emit_extra(c)
    return result|{'large_update':'inactive VRAM, up to7 chunks then final palette/OAM/HDMA flip','raw_chr_bytes':2048,'serviced_final_wait':True}


def emit_extra(c):
    def lda(a):c.absolute(0xad,a)
    def sta(a):c.absolute(0x8d,a)
    def imm(v):c.emit(0xa9);c.word(v)
    def cond(op,s):c.emit(op^0x20,3);c.jump(s)
    # Forced-blank boot: initialize only the two static raw maps. No save SRAM.
    c.label('maps181');c.emit(0xc2,0x20)
    for address,first in [(0x3800,320),(0x5800,832)]:
        imm(address);sta(0x2116);imm(first);call(c,'map_write181')
    c.emit(0x60)
    c.label('map_write181');c.emit(0xa2,32,0)
    c.label('map_words181');sta(0x2118);c.emit(0x1a,0xca);c.branch(0xd0,'map_words181')
    imm(0);c.emit(0xa2,0xe0,3);c.label('map_zero181');sta(0x2118);c.emit(0xca);c.branch(0xd0,'map_zero181')
    c.emit(0x60)
    # SEAL metadata: candidate count1240, visible count1242, mask123a.
    # Verify all three bounded configuration tables before any PPU write.
    c.label('validate181')
    lda(0x1020);c.emit(0x18,0x69);c.word(0x6500);sta(0x70)
    c.emit(0xe2,0x20);c.store(0x72,0x7f);c.emit(0xc2,0x20)
    c.emit(0xa0,0,0);c.absolute(0x9c,0x74)
    c.label('scroll_validate181');c.emit(0xe2,0x20,0xb7,0x70,0xc2,0x20,0x29,255,0)
    c.branch(0xf0,'scroll_end181');c.emit(0xc9,128,0);cond(0xb0,'invalid181')
    c.emit(0x18);c.absolute(0x6d,0x74);sta(0x74);c.emit(0x98,0x18,0x69,5,0,0xa8,0xc0,0x61,4);c.branch(0x90,'scroll_validate181');c.jump('invalid181')
    c.label('scroll_end181');lda(0x74);c.emit(0xc9,224,0);cond(0xd0,'invalid181')
    lda(0x1240);cond(0xf0,'normal181')
    lda(0x100a);c.emit(0xc9);c.word(3418);cond(0xd0,'invalid181')
    lda(0x1020);c.emit(0x18,0x69);c.word(0x7161);sta(0x70)
    # Counts and termination of A/B/enable are identical. Fixed ports/modes,
    # map addresses and window values cannot be changed by a malformed table.
    c.emit(0xa0,0,0);c.absolute(0x9c,0x74);c.absolute(0x9c,0x76)
    c.label('table181');c.emit(0xe2,0x20,0xb7,0x70,0xc2,0x20,0x29,255,0)
    cond(0xf0,'table_end181');c.emit(0xc9,128,0);cond(0xb0,'invalid181');sta(0x78)
    c.emit(0x18);c.absolute(0x6d,0x74);sta(0x74);c.emit(0xc9,225,0);cond(0xb0,'invalid181')
    # Pointer indexed by Y; B and enable sit at +81/+162.
    c.emit(0x98,0x48,0x18,0x69,81,0,0xa8,0xe2,0x20,0xb7,0x70,0xc2,0x20,0x29,255,0);c.absolute(0xcd,0x78);cond(0xd0,'invalid_pop181')
    c.emit(0x98,0x18,0x69,81,0,0xa8,0xe2,0x20,0xb7,0x70,0xc2,0x20,0x29,255,0);c.absolute(0xcd,0x78);cond(0xd0,'invalid_pop181')
    c.emit(0x68,0xa8,0xc8,0xb7,0x70,0xc9,3,0);cond(0xf0,'raw_table181');c.emit(0xc9,0,0);cond(0xd0,'invalid181')
    imm(0x0031);sta(0x7a);imm(0x0011);sta(0x7c);lda(0x123a);c.emit(0xc9,0x18,0);cond(0xd0,'unclip_table181');imm(17);c.jump('window_table181')
    c.label('unclip_table181');imm(0)
    c.label('window_table181');sta(0x7e);c.jump('values181')
    c.label('raw_table181');lda(0x76);c.emit(0x18);c.absolute(0x6d,0x78);sta(0x76);imm(0x0038);sta(0x7a);imm(1);sta(0x7c);c.absolute(0x9c,0x7e)
    c.label('values181')
    # Same mode/MOSAIC in bank B; same maps except the bank's +0x20.
    c.emit(0xb7,0x70);sta(0x78);c.emit(0x98,0x48,0x18,0x69,81,0,0xa8,0xb7,0x70);c.absolute(0xcd,0x78);cond(0xd0,'invalid_pop181');c.emit(0x68,0xa8,0xc8,0xc8,0xb7,0x70);c.absolute(0xcd,0x7a);cond(0xd0,'invalid181')
    c.emit(0x98,0x48,0x18,0x69,81,0,0xa8,0xb7,0x70,0x38,0xe9,0x20,0);c.absolute(0xcd,0x7a);cond(0xd0,'invalid_pop181')
    c.emit(0x98,0x18,0x69,79,0,0xa8,0xb7,0x70);c.absolute(0xcd,0x7c);cond(0xd0,'invalid_pop181');c.emit(0xc8,0xc8,0xb7,0x70);c.absolute(0xcd,0x7e);cond(0xd0,'invalid_pop181')
    c.emit(0x68,0xa8,0xc8,0xc8,0xc0,81,0);cond(0x90,'table181');c.jump('invalid181')
    c.label('invalid_pop181');c.emit(0x68);c.jump('invalid181')
    c.label('table_end181');lda(0x74);c.emit(0xc9,224,0);cond(0xd0,'invalid181');lda(0x76);c.absolute(0xcd,0x1240);cond(0xd0,'invalid181')
    # Check both other terminators and all three encoded lengths.
    for step in [81,81]:
        c.emit(0x98,0x18,0x69);c.word(step);c.emit(0xa8,0xe2,0x20,0xb7,0x70,0xc2,0x20,0x29,255,0);cond(0xd0,'invalid181')
    c.emit(0x98,0x38,0xe9,161,0);sta(0x78);c.emit(0xa0,243,0)
    c.label('length181');c.emit(0xb7,0x70);c.absolute(0xcd,0x78);cond(0xd0,'invalid181');c.emit(0xc8,0xc8,0xc0,249,0);c.branch(0xd0,'length181')
    c.emit(0x38,0x60)
    c.label('normal181');c.emit(0x98,0x1a);c.absolute(0xcd,0x100a);cond(0xd0,'invalid181');c.emit(0x38,0x60)
    c.label('invalid181');c.emit(0x18,0x60)
    # Reset live PPU state before HDMA takes effect on the next visible row.
    c.label('display181');c.store(0x2105,0);c.store(0x2106,0);c.store(0x212c,17);c.store(0x212d,0);c.store(0x212f,0)
    lda(0x123a);c.emit(0xc9,0x18);cond(0xd0,'unclip181');c.store(0x212e,17);c.emit(0x60)
    c.label('unclip181');c.store(0x212e,0);c.emit(0x60)
    # Channel1 scroll is configured by the ordinary uploader. Channels2/3
    # switch mode/map and enables/windows; every source belongs to candidate.
    c.label('hdma181');lda(0x1240);cond(0xf0,'single181')
    c.emit(0xc2,0x20);lda(0x1020);c.emit(0x18,0x69);c.word(0x7161);sta(0x4322)
    lda(0x1032);cond(0xf0,'mode_a181');lda(0x4322);c.emit(0x18,0x69,81,0);sta(0x4322)
    c.label('mode_a181');lda(0x1020);c.emit(0x18,0x69);c.word(0x7203);sta(0x4332);c.emit(0xe2,0x20)
    for a,v in [(0x4320,4),(0x4321,5),(0x4324,0x7f),(0x4330,4),(0x4331,0x2c),(0x4334,0x7f),(0x420c,14)]:c.store(a,v)
    c.emit(0x60);c.label('single181');c.store(0x420c,2);c.emit(0x60)


def source181(s):
    s=client_source(s)
    s=replace(s,'for a in range(0x2123,0x212c):c.store(a,0)',"c.emit(0xa2,8,0);c.label('clear_window181');c.absolute(0x9e,0x2123);c.emit(0xca);c.branch(0x10,'clear_window181')")
    s=replace(s,'for a in list(range(0x1000,0x1040,2))+list(range(0x1080,0x108c,2))+list(range(0x1220,0x123a,2)):c.absolute(0x9c,a)',"""for first,last in [(0x1000,0x103e),(0x1080,0x108a),(0x1220,0x1242)]:
  c.emit(0xa2);c.word(last-first);name=f'clear{first}';c.label(name);c.absolute(0x9e,first);c.emit(0xca,0xca);c.branch(0x10,name)""")
    s=replace(s,'for a in range(0,12,2):lda(0x1000+a);sta(0x1010+a)',"c.emit(0xa2,10,0);c.label('retire181');c.absolute(0xbd,0x1000);c.absolute(0x9d,0x1010);c.emit(0xca,0xca);c.branch(0x10,'retire181')")
    s=replace(s,'body=c.finish();assert len(body)<=0xec0',"body=c.finish();(out/'body.bin').write_bytes(body);(out/'labels.json').write_text(json.dumps(c.labels,indent=2));assert len(body)<=0xec0, (len(body),0xec0)")
    s=replace(s,'checkimm(0x120c,20)','checkimm(0x120c,24)')
    s=replace(s," c.label('poll');", " call(c,'maps181')\n c.label('poll');")
    s=replace(s," c.label('mask_valid178');sta(0x123a)",""" c.label('mask_valid178');sta(0x123a)
 c.long(0xaf,0x400024);c.emit(0xc9,0x12,0x18);cond(0xd0,'bad_packet')
 c.long(0xaf,0x400026);c.emit(0xc9,8,0);cond(0xb0,'bad_packet');sta(0x1240)
 call(c,'validate181');cond(0x90,'bad_packet')""")
    s=replace(s," c.absolute(0x9c,0x1228);imm(1);c.jump('reply')", " lda(0x1240);sta(0x1242)\n c.absolute(0x9c,0x1228);imm(1);c.jump('reply')")
    return s


def build(out):
    source=inspect.getsource(boot.build)
    source=replace(source,'source=Path(original.__file__).read_text()', 'source=source181(Path(original.__file__).read_text())')
    source=replace(source,'from nes_native_local165 import emit,call,OFFSETS,LIMITS\\nfrom nes_banked169 import emit_upload',
                   'from nes_client181 import emit,call,OFFSETS,LIMITS,emit_upload')
    namespace=dict(boot.__dict__);namespace['source181']=source181
    exec(compile(source,'client181-build','exec'),namespace)
    result=namespace['build'](out)
    result.update(scope=__doc__,seal_bytes=24,sink_version='1812',bundle_bytes=3418,metadata_end=0x1244,
                  raw_map_bytes=4096,save_sram=False)
    (out/'build.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);build(p.parse_args().out)
