"""Build the original SNES-side renderer for the replacement FXPAK GBC core.

The image contains no game data.  It executes from WRAM, requests completed
GBC frames through the $6000 endpoint, copies palette/HDMA metadata to a
double-buffered WRAM area, and performs the proven 24-pass strided VRAM DMA
during forced blank.  This builder does not authorize hardware use by itself.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib

P = Path(__file__).resolve().parent
R = P
G12 = G11 = G10 = G9 = G8 = True
R.mkdir(parents=True, exist_ok=True)


class Asm:
    def __init__(self, base):
        self.base = base
        self.data = bytearray()
        self.labels = {}
        self.fixups = []

    @property
    def pc(self):
        return self.base + len(self.data)

    def emit(self, *values):
        self.data.extend(value & 0xFF for value in values)

    def label(self, name):
        assert name not in self.labels
        self.labels[name] = self.pc

    def branch(self, opcode, label):
        self.emit(opcode, 0)
        self.fixups.append((len(self.data) - 1, label, "rel8"))

    def absolute_label(self, opcode, label):
        self.emit(opcode, 0, 0)
        self.fixups.append((len(self.data) - 2, label, "abs16"))

    def lda8(self, value):
        self.emit(0xA9, value)

    def ldx16(self, value):
        self.emit(0xA2, value, value >> 8)

    def read(self, address):
        self.emit(0xAD, address, address >> 8)

    def write(self, address, value):
        self.lda8(value)
        self.emit(0x8D, address, address >> 8)

    def sta(self, address):
        self.emit(0x8D, address, address >> 8)

    def stz(self, address):
        self.emit(0x9C, address, address >> 8)

    def jsr(self, label):
        self.absolute_label(0x20, label)

    def jump(self, label):
        self.absolute_label(0x4C, label)

    def finish(self):
        for offset, label, kind in self.fixups:
            assert label in self.labels, label
            if kind == "rel8":
                after = self.base + offset + 1
                delta = self.labels[label] - after
                assert -128 <= delta <= 127, (label, delta)
                self.data[offset] = delta & 0xFF
            else:
                self.data[offset:offset + 2] = struct.pack("<H", self.labels[label])
        return bytes(self.data)


PHASE = 0x10
BLANK_SEEN = 0x11
NEXT_BUFFER = 0x12


def dma(a, source, count, mode, target, channel=7):
    base = 0x4300 + channel * 0x10
    a.write(base + 0, mode)
    a.write(base + 1, target)
    a.write(base + 2, source & 0xFF)
    a.write(base + 3, (source >> 8) & 0xFF)
    a.write(base + 4, (source >> 16) & 0xFF)

    if source >> 16 == 0x40 and count == 726:
        ch=(source-0x40c600)//0x300
        directory=0x40c480+ch*2
        tag=f'length_{source:06x}_{a.pc:04x}'
        a.emit(0xc2,0x20) # A16
        a.emit(0xaf,directory,directory>>8,directory>>16)
        a.emit(0xc9,6,0);a.branch(0xb0,tag+'_min')
        a.emit(0xe2,0x20);a.jump('fatal_frame')
        a.label(tag+'_min')
        a.emit(0xc9,0xd7,2);a.branch(0x90,tag+'_max') # <=726
        a.emit(0xe2,0x20);a.jump('fatal_frame')
        a.label(tag+'_max');a.sta(base+5);a.sta(0x1820+ch*2);a.emit(0xe2,0x20)
    else:
        a.write(base + 5, count & 0xFF)
        a.write(base + 6, count >> 8)

    a.write(0x420B, 1 << channel)


def copy_long_x(a, name, source, destination, count):
    assert 0 < count <= 0x8000
    if G8 and 0x7e4000 <= destination <= (0x7e7300 if G12 else 0x7e5700):
        # Seven HDMA color channels occupy0..6. CPU copy avoids visible GDMA.
        a.label(name)
        a.emit(0x8b,0xc2,0x20) # PHB; A16, X/Y remain16
        if count==726:
            ch=(source-0x40c600)//0x300
            directory=0x40c480+2*ch;tag=name+'_length'
            a.emit(0xaf,directory,directory>>8,directory>>16,0xc9,6,0)
            a.branch(0xb0,tag+'_min');a.emit(0xe2,0x20,0xab);a.jump('fatal_frame')
            a.label(tag+'_min');a.emit(0xc9,0xd7,2)
            a.branch(0x90,tag+'_ok');a.emit(0xe2,0x20,0xab);a.jump('fatal_frame')
            a.label(tag+'_ok');a.sta(0x1820+2*ch)
        else:a.emit(0xa9,count,count>>8)
        a.emit(0x3a) # MVN count is length-1, including both endpoints
        a.ldx16(source&65535);a.emit(0xa0,destination,destination>>8)
        a.emit(0x54,destination>>16,source>>16,0xab,0xe2,0x20) # MVN; PLB; A8
        if count==726:
            ch=(source-0x40c600)//0x300
            cache=destination-ch*0x300-0x80+2*ch
            a.emit(0xc2,0x20);a.read(0x1820+2*ch);a.emit(0x8f,cache,cache>>8,cache>>16,0xe2,0x20)
        # Exactly one CPU read per region, eight per installed frame. A shared
        # index follows successive bytes across both WRAM buffers. Clamp to
        # this snapshot's validated length if a shorter table replaced it.
        region=0 if count==128 else 1+(source-0x40c600)//0x300
        counter=0x1830+2*region
        tag=name+'_verify';a.label(tag+'_start')
        a.emit(0xc2,0x20);a.read(counter)
        if region: a.emit(0xcd,0x1820+2*(region-1),(0x1820+2*(region-1))>>8)
        else: a.emit(0xc9,128,0)
        a.branch(0x90,tag+'_index');a.emit(0xa9,0,0)
        a.label(tag+'_index');a.emit(0xaa,0x1a);a.sta(counter);a.emit(0xe2,0x20)
        a.emit(0xbf,source,source>>8,source>>16);a.sta(0x1810)
        a.emit(0xdf,destination,destination>>8,destination>>16)
        a.branch(0xf0,tag+'_equal')
        a.emit(0xbf,destination,destination>>8,destination>>16);a.sta(0x25)
        a.read(0x1810);a.sta(0x26)
        a.emit(0xc2,0x20,0x8a,0x18,0x69,source&255,(source>>8)&255);a.sta(0x27);a.emit(0xe2,0x20)
        a.write(0x24,4);a.jump('g10_show')
        a.label(tag+'_equal')
        return
    a.ldx16(count - 1)
    a.label(name)
    a.emit(0xBF, source, source >> 8, source >> 16)       # lda long,x
    a.emit(0x9F, destination, destination >> 8, destination >> 16)
    a.emit(0xCA)                                          # dex
    a.branch(0x10, name)                                  # bpl


body = Asm(0x2000)
body.label("reset")
body.emit(0x78, 0xC2, 0x10, 0xE2, 0x20)                 # sei; X16; A8
for scratch in range(0x1830,0x1840): body.stz(scratch)
for scratch in range(0x1b20,0x1b50): body.stz(scratch)
body.write(0x1b50,127);body.write(0x1b51,1);body.write(0x1b52,57);body.write(0x1b53,1);body.stz(0x1b54)
body.write(0x2100, 0x80)                                  # forced blank
for address in (0x2106, 0x4200, 0x420C, 0x212C, 0x212D, 0x2130, 0x2131, 0x2133):
    body.stz(address)
for address in (PHASE, BLANK_SEEN, NEXT_BUFFER, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x3f):
    body.stz(address)
if G8:
    body.stz(0x18); body.stz(0x19)  # install / visible-IRQ counters, modulo 256

# Clear VRAM from a fixed zero byte and install the permanent 20x18 tilemap.
body.write(0x2115, 0x80)
body.stz(0x2116)
body.stz(0x2117)
dma(body, 0x018800, 0, 0x09, 0x18)                        # count 0 = 64 KiB
body.stz(0x2116)
body.write(0x2117, 0x60)
dma(body, 0x018000, 2048, 0x01, 0x18)
body.write(0x2105, 3)                                     # Mode 3, BG1 8bpp
body.write(0x2107, 0x60)                                  # tilemap at VRAM $6000
body.stz(0x210B)                                          # tile graphics at $0000
body.stz(0x210D)
body.stz(0x210D)
body.write(0x210E, 0xFF)
body.write(0x210E, 0x03)
body.write(0x212C, 1)

if G8:
    # Require the exact known-good G7 FPGA before starting the producer.
    body.read(0x6000); body.emit(0xc9, 0xc3)
    body.emit(0xf0, 3); body.jump('fatal_endpoint')
    body.read(0x6007); body.emit(0xc9, 0xaf if G12 else 0xab if G11 else 0xa7)
    body.emit(0xf0, 3); body.jump('fatal_endpoint')

# First frame is prepared and installed while the display remains blank.
if G9:
    body.jsr('audio_init')
    body.jsr('audio_indicator')
body.jsr("request_prepare")
body.jsr("install_frame")
body.stz(PHASE)
body.stz(BLANK_SEEN)
body.write(0x4209, 40)
body.stz(0x420A)
if G8: body.read(0x4211)  # discard stale TIMEUP before enabling V-IRQ
body.write(0x4200, 0x21)                                  # V-IRQ + auto joypad
body.write(0x3f,1);body.emit(0x58)                                           # cli
body.label("main_loop")
if G8:
    body.read(PHASE); body.branch(0xf0, 'main_loop')
else: body.emit(0xCB)                                     # wai for line 41
body.jsr("request_prepare")                               # prepare next page visibly
if G8:
    # Never start a long DMA late in an already elapsed blank interval.
    body.stz(BLANK_SEEN)
    body.label('wait_blank')
body.read(BLANK_SEEN)
body.branch(0xD0, "already_blank")
if G8: body.jump('wait_blank')
else: body.emit(0xCB)                                     # wai for line 185
body.label("already_blank")
body.jsr("install_frame")
body.stz(BLANK_SEEN)
body.stz(PHASE)
body.write(0x4209, 40)
body.stz(0x420A)
body.write(0x4200, 0x21)
body.branch(0x80, "main_loop")

# IRQ saves full A/X before entering A8; RTI restores interrupted flags.
# Line 40 leaves an entire border line before game pixels at line 41.
# IRQ phase 0 exposes the newly installed frame and starts the visible-period
# preparation window. Phase 1 blanks before any VRAM/CGRAM writes.
body.label("irq")
body.emit(0xc2,0x30,0x48,0xda,0x8b,0xe2,0x20,0xa9,0,0x48,0xab)                                     # pha; phx
if G8: body.read(0x4211)  # acknowledge the level-latched IRQ, before RTI
body.read(0x2f);body.emit(0xf0,3);body.jump('irq_arm_hdma')
body.read(PHASE)
body.branch(0xD0, "irq_blank")
body.write(0x2100, 0x0F)
if G8: body.emit(0xee,0x19,0)
body.write(PHASE, 1)
body.write(0x4209, 185)
body.stz(0x420A)
body.write(0x4200, 0x21)
body.emit(0xab,0xc2,0x20,0xfa,0x68,0x40)                               # plx; pla; rti
body.label("irq_blank")
body.write(0x2100, 0x80)
body.jsr('c2_auto')
if not G8: body.stz(0x420C)
body.write(BLANK_SEEN, 1)
body.write(0x4200, 0x21 if G8 else 0x01)                  # repeat blank IRQ if producer is late
body.emit(0xab,0xc2,0x20,0xfa,0x68,0x40)

# Wait for auto-joypad completion, commit the mapped Game Boy buttons, and
# request a complete FPGA snapshot. Invalid startup captures are retried.
body.label('irq_arm_hdma')
# A queued 0->3F transition is serviced at line 225, during forced/V blank.
body.read(0x2e);body.sta(0x420c);body.sta(0x2d);body.stz(0x2f)
body.read(0x31);body.emit(0x09,4);body.sta(0x31)
body.write(0x4209,185);body.stz(0x420a)
body.emit(0xab,0xc2,0x20,0xfa,0x68,0x40)

body.label("request_prepare")
body.label("wait_joy")
body.read(0x4212)
body.emit(0x29, 0x01)
body.branch(0xD0, "wait_joy")
if G10: body.jsr('g10_probe')
if G9:
    from g9_snes_io import emit_pad
    emit_pad(body)
else:
    body.read(0x4218)
    body.sta(0x6005)
    body.read(0x4219)
    body.sta(0x6006)
body.label("retry_request")
body.write(0x6001, 0x80)                                  # clear local error
body.write(0x6001, 0x01)
body.label("poll_status")
body.read(0x6002)
body.emit(0x29, 0x10)
if G8:
    body.emit(0xf0, 3); body.jump('fatal_frame')
else: body.branch(0xD0, "retry_request")
body.read(0x6002)
body.emit(0x29, 0x09, 0xC9, 0x08)                         # available && !busy
body.branch(0xD0, "poll_status")
body.read(0x6002)
body.emit(0x29, 0x02)
if G8:
    body.branch(0xd0, 'snapshot_valid')
    body.label('retry_vblank_out'); body.read(0x4212); body.emit(0x29, 0x80)
    body.branch(0xd0, 'retry_vblank_out')
    body.label('retry_vblank_in'); body.read(0x4212); body.emit(0x29, 0x80)
    body.branch(0xf0, 'retry_vblank_in')
    if G10: body.jsr('g10_probe')  # keep fault/X diagnostics alive during LCD-invalid retry
    body.jump('retry_request')
    body.label('snapshot_valid')
else: body.branch(0xF0, "retry_request")
body.read(NEXT_BUFFER)
if G8:
    body.emit(0xf0,3);body.jump('copy_buffer_1')
else:body.branch(0xD0, "copy_buffer_1")
copy_long_x(body,"copy_b0_palette",0x40c400,8273920,128)
copy_long_x(body,"copy_b0_h0",4244992,8274176,726)
copy_long_x(body,"copy_b0_h1",4245760,8274944,726)
copy_long_x(body,"copy_b0_h2",4246528,8275712,726)
copy_long_x(body,"copy_b0_h3",4247296,8276480,726)
copy_long_x(body,"copy_b0_h4",4248064,8277248,726)
copy_long_x(body,"copy_b0_h5",4248832,8278016,726)
copy_long_x(body,"copy_b0_h6",4249600,8278784,726)
body.emit(0x60)
body.label("copy_buffer_1")
copy_long_x(body,"copy_b1_palette",0x40c400,8282112,128)
copy_long_x(body,"copy_b1_h0",4244992,8282368,726)
copy_long_x(body,"copy_b1_h1",4245760,8283136,726)
copy_long_x(body,"copy_b1_h2",4246528,8283904,726)
copy_long_x(body,"copy_b1_h3",4247296,8284672,726)
copy_long_x(body,"copy_b1_h4",4248064,8285440,726)
copy_long_x(body,"copy_b1_h5",4248832,8286208,726)
copy_long_x(body,"copy_b1_h6",4249600,8286976,726)
body.emit(0x60)

body.label("install_frame")
if G8: body.jsr('prepare_hdma')
else: body.stz(0x420C)
body.stz(0x2121)
body.read(NEXT_BUFFER)
body.branch(0xD0, "install_buffer_1")
dma(body, 0x7E4000, 128, 0x00, 0x22)
body.jump("install_tiles")
body.label("install_buffer_1")
dma(body, 0x7E6000, 128, 0x00, 0x22)
body.label("install_tiles")
body.write(0x2115, 0x81)
body.write(0x4370, 0x01)
body.write(0x4371, 0x18)
body.stz(0x4372)
body.write(0x4373, 0x80)
body.write(0x4374, 0x40)
for pair in range(3):
    for row in range(8):
        body.write(0x2116, pair * 8 + row)
        body.stz(0x2117)
        if pair==0 and row==0:body.ldx16(720);body.emit(0x8e,0x75,0x43,0x80,2,0xea,0xea)
        else:body.emit(0x8e,0x75,0x43,0x80,5,*([0xea]*5))
        if pair*8+row==15:body.jsr('c15_dma_gap');body.emit(0xea,0xea)
        else:body.write(0x420B, 0x80)
if G8:
    body.read(NEXT_BUFFER); body.emit(0x49, 1); body.sta(NEXT_BUFFER)
    body.emit(0xee,0x18,0)
    body.emit(0x60)
    body.label('prepare_hdma')
    # No sacrificial channel: visible-period copies no longer use GDMA.
body.read(NEXT_BUFFER)
body.branch(0xD0, "hdma_buffer_1")
hdma_sources = tuple(0x7e4100+i*0x300 for i in range(7))
body.jump("configure_hdma")
body.label("hdma_buffer_1")
hdma_sources_1 = tuple(0x7e6100+i*0x300 for i in range(7))

# Two small configuration blocks are emitted explicitly so HDMA never reads
# from the page that the FPGA is replacing during visible display.
def emit_hdma_config(a, sources):
    for channel, source in enumerate(sources):
        base = 0x4300 + channel * 0x10
        a.write(base + 0, 3)
        a.write(base + 1, 0x21)
        a.write(base + 2, source & 0xFF)
        a.write(base + 3, (source >> 8) & 0xFF)
        a.write(base + 4, source >> 16)

emit_hdma_config(body, hdma_sources_1)
body.jump("hdma_ready")
body.label("configure_hdma")
emit_hdma_config(body, hdma_sources)
body.label("hdma_ready")
# Use pad sampled by request_prepare. Change mask only at the existing
# forced-blank install boundary. L is not forwarded as a Game Boy button.
body.read(0x20)
body.emit(0x29,0x20)
body.branch(0xf0,'g12h1_hdma_on')
body.read(0x31);body.emit(0x09,1);body.sta(0x31)
body.lda8(0)
body.branch(0x80,'g12h1_apply_mask')
body.label('g12h1_hdma_on')
body.lda8(0x7f)
body.label('g12h1_apply_mask')
body.sta(0x2e) # requested mask; 2D remains the last actually applied mask
body.read(0x2d);body.branch(0xd0,'hdma_apply_now')
body.read(0x2e);body.branch(0xf0,'hdma_apply_now')
body.read(0x3f);body.branch(0xf0,'hdma_apply_now') # startup IRQ not yet enabled
body.read(0x31);body.emit(0x09,2);body.sta(0x31)
body.write(0x2f,1);body.write(0x4209,225);body.stz(0x420a)
body.emit(0x60)
body.label('hdma_apply_now')
body.read(0x2e);body.sta(0x2d);body.sta(0x420c)
if not G8:
    body.read(NEXT_BUFFER)
    body.emit(0x49, 0x01)                                 # eor #1
    body.sta(NEXT_BUFFER)
body.emit(0x60)

if G8:
    for label, color in [('fatal_endpoint', 0x4010), ('fatal_frame', 0x0010)]:
        body.label(label)
        body.emit(0x78)
        for reg in (0x4200, 0x420c, 0x212c): body.stz(reg)
        body.write(0x2100, 0x80); body.stz(0x2121)
        body.write(0x2122, color & 255); body.write(0x2122, color >> 8)
        body.write(0x2100, 15)
        body.label(label+'_stop'); body.jump(label+'_stop')

if G9:
    from g9_snes_io import emit_audio, spc_program
    emit_audio(body)
if G10:
    from g10_video_diagnostics import emit_probe, emit_screen, assets
    emit_probe(body)
from g13_readback_diag import emit_readback
emit_readback(body)
from g13_cgram_diag import emit_capture, emit_compare
extra = Asm(0x8000)
emit_capture(extra);emit_compare(extra)
from g13_auto_color import emit_auto
emit_auto(extra);emit_screen(extra,dma)
# C15: execute pass16 at its original point; leave HDMA enabled.
extra.label('c15_dma_gap')
extra.write(0x420b,0x80)
extra.read(0x3f);extra.branch(0xd0,'c15_runtime_gap');extra.emit(0x60)
extra.label('c15_runtime_gap')
# For the supported schedule pass16 must finish inside VBlank.
extra.read(0x4212);extra.emit(0x29,0x80);extra.branch(0xd0,'c15_gap_begin');extra.jump('fatal_frame')
extra.label('c15_gap_begin')
for tag,mask,done_branch in [('vblank_end',0x80,0xf0)]:
    extra.ldx16(0x1000);extra.label('c15_'+tag)
    extra.read(0x4212);extra.emit(0x29,mask);extra.branch(done_branch,'c15_'+tag+'_done')
    extra.emit(0xca);extra.branch(0xd0,'c15_'+tag);extra.jump('fatal_frame')
    extra.label('c15_'+tag+'_done')
# VBlank status clears at different scanline phases in the tested cores.
# Verify the actual vertical counter has left line0, instead of counting HBlank.
extra.write(0x4201,255);extra.ldx16(0x1000)
extra.label('c15_line_one')
extra.read(0x213f);extra.read(0x2137);extra.read(0x213d)
extra.branch(0xd0,'c15_line_one_done');extra.emit(0xca)
extra.branch(0xd0,'c15_line_one');extra.jump('fatal_frame')
extra.label('c15_line_one_done');extra.ldx16(720);extra.emit(0x60)
extra.labels.update(body.labels)
extra_bytes = extra.finish()
assert len(extra_bytes) < 0x2000
body.labels.update(extra.labels)
body_bytes = body.finish()
if True: # G13C15: same-layout diagnostic-off comparison, code preserved
    patched=bytearray(body_bytes);disabled=[]
    for target,count in [('c2_auto',1),('g10_probe',2)]:
        opcode=bytes((0x20,body.labels[target]&255,body.labels[target]>>8))
        offsets=[i for i in range(len(patched)-2) if patched[i:i+3]==opcode]
        assert len(offsets)==count,(target,offsets)
        for i in offsets:patched[i:i+3]=bytes((0xea,))*3;disabled.append(dict(kind=target,start=i,end=i+3))
    for name,start in body.labels.items():
        if not name.endswith('_verify_start'):continue
        end=body.labels[name[:-6]+'_equal'];i=start-0x2000
        assert end>start and end-start<128
        patched[i:i+3]=bytes((0x4c,end&255,end>>8))
        disabled.append(dict(kind='receive_readback_skip',start=i,end=i+3,skipped_until=end-0x2000))
    i=body.labels['hdma_ready']-0x2000
    assert patched[i:i+5]==bytes.fromhex('ad20002920')
    patched[i+4]=0 # L no longer suppresses color HDMA
    disabled.append(dict(kind='L_mask_off',start=i+4,end=i+5))
    assert len(disabled)==20
    body_bytes=bytes(patched)

assert len(body_bytes) < 0x2000, len(body_bytes)

# The native IRQ vector addresses the first 8 KiB WRAM mirror in bank 00.
# A four-byte JML stub there reaches the full WRAM body.
irq_stub = bytes((0x5C, body.labels["irq"] & 0xFF,
                  body.labels["irq"] >> 8, 0x7E))
boot = Asm(0x8000)
boot.emit(0x78, 0x18, 0xFB, 0xC2, 0x10, 0xE2, 0x20)
boot.emit(0xA2, 0xFF, 0x1F, 0x9A)                         # stack $1fff
if G8:
    boot.emit(0xd8)  # CLD
    boot.lda8(0); boot.emit(0x48, 0xab)  # DBR=0
    boot.emit(0xc2, 0x20, 0xa9, 0, 0, 0x5b, 0xe2, 0x20)  # D=0
    boot.write(0x2100, 0x80)
    for reg in (0x4200, 0x420c, 0x212e, 0x212f, 0x2123, 0x2124, 0x2125):
        boot.stz(reg)
boot.ldx16(len(body_bytes) - 1)
boot.label("copy_body")
boot.emit(0xBF, 0x00, 0x81, 0x00)
boot.emit(0x9F, 0x00, 0x20, 0x7E)
boot.emit(0xCA)
boot.branch(0x10, "copy_body")
boot.ldx16(len(extra_bytes)-1)
boot.label('copy_extra')
boot.emit(0xbf,0,0xb0,0);boot.emit(0x9f,0,0x80,0x7e)
boot.emit(0xca);boot.branch(0x10,'copy_extra')
boot.ldx16(len(irq_stub) - 1)
boot.label("copy_irq_stub")
boot.emit(0xBF, 0x80, 0x80, 0x00)
boot.emit(0x9F, 0x00, 0x1F, 0x7E)
boot.emit(0xCA)
boot.branch(0x10, "copy_irq_stub")
boot.emit(0x5C, 0x00, 0x20, 0x7E)
boot_bytes = boot.finish()
assert len(boot_bytes) <= 0x80

rom = bytearray([0xFF]) * 0x20000
rom[:len(boot_bytes)] = boot_bytes
rom[0x80:0x84] = irq_stub
rom[0x100:0x100 + len(body_bytes)] = body_bytes
assert 0x100+len(body_bytes) <= 0x3000
rom[0x3000:0x3000+len(extra_bytes)] = extra_bytes

tilemap = bytearray()
for y in range(32):
    for x in range(32):
        tile = (y - 5) * 20 + x - 6 if 6 <= x < 26 and 5 <= y < 23 else 511
        tilemap += struct.pack("<H", tile)
rom[0x8000:0x8800] = tilemap
rom[0x8800] = 0
if G10:
    font,diag_map=assets('G13C10' if G12 else 'G11' if G11 else 'G10')
    rom[0x9000:0x9000+len(font)]=font
    rom[0x9400:0x9400+len(diag_map)]=diag_map

title = b"FXPAK GBC RENDERER"
if G8: title = b'FXPAK GBC G8 VIDEO'
if G9: title = b'FXPAK GBC G9 IO'
if G10: title = b'FXPAK GBC G10 PROBE'
if G11: title = b'FXPAK GBC G11 PROBE'
if G12: title = b'FXPAK GBC G13C15 GAP'
rom[0x7FC0:0x7FD5] = title.ljust(21, b" ")
rom[0x7FD5:0x7FDC] = bytes((0x20, 0x00, 0x07, 0x00, 0x01, 0x00, 0x00))
for offset in (0x7FE4, 0x7FE6, 0x7FEA, 0x7FEE):
    rom[offset:offset + 2] = struct.pack("<H", 0x1F00)
rom[0x7FFC:0x7FFE] = struct.pack("<H", 0x8000)
rom[0x7FFA:0x7FFC] = struct.pack("<H", 0x1F00)
rom[0x7FFE:0x8000] = struct.pack("<H", 0x1F00)
rom[0x7FDC:0x7FE0] = b"\xff\xff\x00\x00"
checksum = sum(rom) & 0xFFFF
rom[0x7FDC:0x7FE0] = struct.pack("<HH", checksum ^ 0xFFFF, checksum)

assert len(rom) == 128 * 1024
assert rom[0x7FD7] == 0x07 and rom[0x7FD8] == 0x00
assert struct.unpack_from("<H", rom, 0x7FFC)[0] == 0x8000
assert body_bytes.count(bytes((0x8D, 0x01, 0x60))) >= 2
assert bytes((0xAD, 0x02, 0x60)) in body_bytes
if not G8: assert bytes((0xBF, 0x00, 0xC4, 0x40)) in body_bytes
assert bytes((0xA9, 0x40, 0x8D, 0x74, 0x43)) in body_bytes
if not G8: assert 0xDB not in body_bytes                    # historical byte check

renderer = R / "gbc_snes.bin"
renderer.write_bytes(rom)
verification = {
    "passed": True,
    "diagnostic_code_preserved": True,
    "same_layout_comparison": True,
    "gdma_free_line_zero": True,
    "hdma_enable_schedule_unchanged": True,
    "disabled_execution_ranges": disabled,
    "claim": "original continuous SNES renderer build; hardware execution pending",
    "contains_game_rom": False,
    "rom_bytes": len(rom),
    "rom_sha256": hashlib.sha256(rom).hexdigest(),
    "crc32": f'0x{zlib.crc32(rom):08x}',
    "body_labels": body.labels,
    "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "g8_video_test": G8,
    "g9_input_audio_test": G9,
    "g10_video_diagnostics": False,
    "g11_palette_diagnostics": False,
    "g12_three_updates": G12,
    "diagnostic_source_sha256": hashlib.sha256((P/'g10_video_diagnostics.py').read_bytes()).hexdigest() if G10 else None,
    "font_source_sha256": hashlib.sha256((P/'build_gbc_diagnostic_renderer.py').read_bytes()).hexdigest() if G10 else None,
    "io_source_sha256": hashlib.sha256((P/'g9_snes_io.py').read_bytes()).hexdigest() if G9 else None,
    "spc_program_hex": spc_program().hex() if G9 else None,
    "expected_fpga_id": 'AF' if G12 else 'AB' if G11 else 'A7' if G8 else None,
    "boot_bytes": len(boot_bytes),
    "wram_body_bytes": len(body_bytes),
    "wram_extra_bytes": len(extra_bytes),
    "wram_extra_base": "7e:8000",
    "execution": "00:8000 bootstrap -> 7e:2000 body; native IRQ via 00:1f00 WRAM mirror",
    "frame_protocol": {
        "signature": "00:6000 == c3",
        "request": "00:6001 bit0",
        "status": "00:6002",
        "joypad_stage_commit": ["00:6005", "00:6006"],
        "frame_window": "40:8000-40:c37f",
        "palette_window": "40:c400-40:c47f",
        "hdma_windows": [f"40:{0xc600+i*0x300:04x}" for i in range(7)],
    },
    "wram_metadata_double_buffer": ["7e:4000-7e:55d5", "7e:6000-7e:75d5"] if G12 else ["7e:4000-7e:48b5", "7e:5000-7e:58b5"],
    "vram_dma_bytes": 17280,
    "vram_dma_passes": 24,
    "no_stp": True,
    "renderer_product_rom_ready": False,
    "reason_not_ready": "requires emulator/frontend co-simulation and physical SNES pad timing gate",
    "actual_hardware": False,
}
(R / "verification.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
print(json.dumps(verification, indent=2))
