"""G3: original, non-game diagnostic SNES ROM; no FPGA changes required.

Boot screen is drawn while executing cartridge ROM; a copied WRAM body then
probes the deployed $6000 endpoint. No IRQ, DMA, or game video is needed to
show these screens. Stop at the first valid snapshot (not proof of gameplay).
"""
from pathlib import Path
import ast
import hashlib
import json
import struct
import zlib
import sys

P = Path(__file__).resolve().parent
OUT = P / 'results/gbc-diagnostic-renderer'
G7 = '--g7' in sys.argv
G6 = '--g6' in sys.argv or G7
G5 = '--g5' in sys.argv or G6
G4 = '--g4' in sys.argv or G5
REV = 'G7' if G7 else 'G6' if G6 else 'G5' if G5 else 'G4' if G4 else 'G3'
FPGA = 0xa7 if G7 else 0xa6 if G6 else 0xa5 if G5 else 0xa4
if G4: OUT = P / ('results/gbc-diagnostic-renderer-'+REV.lower())
OUT.mkdir(parents=True, exist_ok=True)
# Reuse only the assembler class; importing the production builder would
# overwrite its artifacts and evidence.
tree = ast.parse((P / 'build_gbc_product_renderer.py').read_text())
scope = {'struct': struct}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.ClassDef)
                             and n.name == 'Asm'], type_ignores=[]), '<Asm>', 'exec'), scope)
Asm = scope['Asm']

# Hand-authored 5x7 glyphs, rendered as SNES Mode 0 2bpp tiles.
GLYPHS = {
 ' ': ['00000']*7,
 '0':['01110','10001','10011','10101','11001','10001','01110'],
 '1':['00100','01100','00100','00100','00100','00100','01110'],
 '2':['01110','10001','00001','00010','00100','01000','11111'],
 '3':['11110','00001','00001','01110','00001','00001','11110'],
 '4':['00010','00110','01010','10010','11111','00010','00010'],
 '5':['11111','10000','10000','11110','00001','00001','11110'],
 '6':['01110','10000','10000','11110','10001','10001','01110'],
 '7':['11111','00001','00010','00100','01000','01000','01000'],
 '8':['01110','10001','10001','01110','10001','10001','01110'],
 '9':['01110','10001','10001','01111','00001','00001','01110'],
 'A':['01110','10001','10001','11111','10001','10001','10001'],
 'B':['11110','10001','10001','11110','10001','10001','11110'],
 'C':['01111','10000','10000','10000','10000','10000','01111'],
 'D':['11110','10001','10001','10001','10001','10001','11110'],
 'E':['11111','10000','10000','11110','10000','10000','11111'],
 'F':['11111','10000','10000','11110','10000','10000','10000'],
 'G':['01111','10000','10000','10111','10001','10001','01111'],
 'H':['10001','10001','10001','11111','10001','10001','10001'],
 'I':['01110','00100','00100','00100','00100','00100','01110'],
 'J':['00001','00001','00001','00001','10001','10001','01110'],
 'K':['10001','10010','10100','11000','10100','10010','10001'],
 'L':['10000','10000','10000','10000','10000','10000','11111'],
 'M':['10001','11011','10101','10101','10001','10001','10001'],
 'N':['10001','11001','10101','10011','10001','10001','10001'],
 'O':['01110','10001','10001','10001','10001','10001','01110'],
 'P':['11110','10001','10001','11110','10000','10000','10000'],
 'Q':['01110','10001','10001','10001','10101','10010','01101'],
 'R':['11110','10001','10001','11110','10100','10010','10001'],
 'S':['01111','10000','10000','01110','00001','00001','11110'],
 'T':['11111','00100','00100','00100','00100','00100','00100'],
 'U':['10001','10001','10001','10001','10001','10001','01110'],
 'V':['10001','10001','10001','10001','10001','01010','00100'],
 'W':['10001','10001','10001','10101','10101','10101','01010'],
 'X':['10001','10001','01010','00100','01010','10001','10001'],
 'Y':['10001','10001','01010','00100','00100','00100','00100'],
 'Z':['11111','00001','00010','00100','01000','10000','11111'],
 ':':['00000','00100','00100','00000','00100','00100','00000'],
}
CHARS = ' 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ:'
tiles = bytearray()
for ch in CHARS:
    for row in GLYPHS[ch] + ['00000']:
        tiles += bytes((int(row, 2) << 2, 0))

def vaddr(a, word):
    a.write(0x2116, word & 255); a.write(0x2117, word >> 8)

def text(a, row, value):
    assert len(value) <= 26
    vaddr(a, 0x1000 + row*32 + 3)
    for ch in value.ljust(26):
        a.write(0x2118, CHARS.index(ch)); a.stz(0x2119)

def screen(a, title, color):
    a.write(0x2100, 0x80)
    a.stz(0x2121)
    a.write(0x2122, color & 255); a.write(0x2122, color >> 8)
    a.write(0x2122, 0xff); a.write(0x2122, 0x7f)
    text(a, 8, title)
    a.write(0x2100, 0x0f)

def vblank(a, name):
    a.label(name+'_out'); a.read(0x4212); a.emit(0x29, 0x80)
    a.branch(0xd0, name+'_out')
    a.label(name+'_in'); a.read(0x4212); a.emit(0x29, 0x80)
    a.branch(0xf0, name+'_in')

def hold(a, name):
    a.ldx16(120)
    vblank(a, name)
    a.emit(0xca); a.branch(0xd0, name+'_out')

def far_branch(a, opcode, label):
    a.emit(opcode ^ 0x20, 3)  # invert BEQ/BNE, skip absolute JMP
    a.jump(label)

# The diagnostic body lives entirely in WRAM after bootstrap.
b = Asm(0x2000)
b.label('wram_entry')
screen(b, '02 WRAM OK', 0x4000)
hold(b, 'wram_hold')
b.read(0xffb0); b.emit(0xc9, 1); far_branch(b, 0xd0, 'probe_endpoint')
screen(b, 'SNES DISPLAY CONTROL OK', 0x0200)
b.jump('terminal')
b.label('probe_endpoint')
b.read(0x6000); b.sta(0x20); b.emit(0xc9, 0xc3)
far_branch(b, 0xf0, 'endpoint_ok')
screen(b, 'E1 ENDPOINT SIGNATURE', 0x4010)
b.jump('terminal')
b.label('endpoint_ok')
if G4:
    b.read(0x6007); b.sta(0x24); b.emit(0xc9, FPGA)
    far_branch(b, 0xf0, 'fpga_ok')
    screen(b, f'E3 WRONG FPGA EXPECT {FPGA:02X}', 0x4010); b.jump('terminal')
    b.label('fpga_ok'); b.write(0x2e, 1); b.write(0x6008, 1)
screen(b, '03 ENDPOINT OK', 0x4100)
hold(b, 'endpoint_hold')
screen(b, '04 WAIT FIRST FRAME', 0x0210)
b.label('request')
b.write(0x6001, 0x80); b.write(0x6001, 1)
b.label('poll')
vblank(b, 'poll_vblank')
# Latch a single status sample per screen update, then display raw bytes.
b.read(0x6002); b.sta(0x21)
b.read(0x6003); b.sta(0x22)
b.read(0x6004); b.sta(0x23)
b.jsr('show_values')
b.read(0x21); b.emit(0x29, 0x10); far_branch(b, 0xf0, 'no_error')
screen(b, 'E2 FRAME ERROR', 0x0010); b.jump('terminal')
b.label('no_error')
b.read(0x21); b.emit(0x29, 0x09, 0xc9, 0x08); far_branch(b, 0xd0, 'poll')
b.read(0x21); b.emit(0x29, 0x02); far_branch(b, 0xd0, 'valid')
# Invalid startup snapshots are expected; retain that fact on screen and
# retry at video-frame cadence, never an unbounded tight request loop.
screen(b, '05 RETRY INVALID FRAME', 0x021f); b.jump('request')
b.label('valid')
screen(b, '06 VALID SNAPSHOT', 0x0200)
b.label('terminal')
b.jsr('show_values')
b.label('terminal_loop'); b.jump('terminal_loop')
b.label('show_values')
if G4:
    # The FPGA snapshot is held until the next request. Read all four bytes
    # before requesting another; never combine fields from separate captures.
    b.read(0x2e); far_branch(b, 0xf0, 'draw_values')
    b.read(0x6008); b.sta(0x25); b.emit(0x29, 2)
    far_branch(b, 0xf0, 'draw_values')
    for offset in range(4):
        b.read(0x6009+offset); b.sta(0x26+offset)
    b.write(0x6008, 1)
    b.label('draw_values')
b.write(0x2100, 0x80)
for pos, addr in enumerate((0x20, 0x21, 0x23, 0x22)):
    vaddr(b, 0x1000 + 12*32 + (7, 12, 17, 19)[pos])
    b.read(addr)
    b.emit(0x4a, 0x4a, 0x4a, 0x4a)  # lsr A x4
    b.jsr('hex_nibble')
    b.read(addr); b.emit(0x29, 0x0f); b.jsr('hex_nibble')
if G4:
    for row,col,addr in ((15,8,0x24),(15,16,0x25),
                         (18,3,0x26),(18,10,0x27),(18,17,0x28),(18,24,0x29)):
        vaddr(b, 0x1000+row*32+col)
        b.read(addr); b.emit(0x4a,0x4a,0x4a,0x4a); b.jsr('hex_nibble')
        b.read(addr); b.emit(0x29,15); b.jsr('hex_nibble')
b.write(0x2100, 0x0f); b.emit(0x60)
b.label('hex_nibble')
# Hex glyphs are contiguous at tile numbers 1..16.
b.emit(0x18, 0x69, 1); b.sta(0x2118); b.stz(0x2119); b.emit(0x60)
body = b.finish()
assert len(body) < 0x4000

a = Asm(0x8000)
a.emit(0x78, 0x18, 0xfb, 0xc2, 0x10, 0xe2, 0x20, 0xd8) # native, X16,A8, CLD
a.ldx16(0x1fff); a.emit(0x9a)
# Explicit bank/direct-page state, instead of relying on inherited values.
a.lda8(0); a.emit(0x48, 0xab)  # PHA / PLB: DBR=0
a.emit(0xc2, 0x20, 0xa9, 0, 0, 0x5b, 0xe2, 0x20) # D=0
a.write(0x2100, 0x80)
for reg in (0x4200,0x420b,0x420c,0x2105,0x2106,0x210b,0x212c,0x212d,
            0x212e,0x212f,0x2123,0x2124,0x2125,0x2130,0x2131,0x2133):
    a.stz(reg)
a.stz(0x210d); a.stz(0x210d)
a.write(0x210e, 0xff); a.write(0x210e, 0xff)
a.write(0x2107, 0x10); a.write(0x2115, 0x80)
vaddr(a, 0x1000)
a.ldx16(1024); a.label('clear_map')
a.stz(0x2118); a.stz(0x2119); a.emit(0xca); a.branch(0xd0, 'clear_map')
# Forward word copy from ROM font data using Y-free, supported opcodes.
vaddr(a, 0)
for i in range(len(tiles)//2):
    # Tiny font (~600 bytes): immediate writes isolate ROM-fetch tests from
    # DMA and indexed data-bus behavior.
    a.write(0x2118, tiles[i*2]); a.write(0x2119, tiles[i*2+1])
text(a, 5, 'FXPAK GBC '+REV+' DIAGNOSTIC')
text(a, 11, 'SIG  STAT COUNT')
if G4:
    text(a, 14, 'FPGA    SNAP')
    text(a, 17, 'CAP    BUF    ERR    PRE' if G6 else 'LIVE   SEEN   ERR    PIPE')
    text(a, 21, 'NO GAMEPLAY OR AUDIO')
    text(a, 23, 'TAKE PHOTO OF LAST SCREEN')
else:
    text(a, 16, 'NO GAMEPLAY OR AUDIO')
    text(a, 18, 'TAKE PHOTO OF LAST SCREEN')
for addr in range(0x20,0x2f if G4 else 0x24): a.stz(addr)
a.write(0x212c, 1)
screen(a, '01 ROM BOOT OK', 0x0010)
hold(a, 'boot_hold')
a.ldx16(len(body)-1); a.label('copy_body')
a.emit(0xbf, 0x00, 0xa0, 0x00); a.emit(0x9f, 0x00, 0x20, 0x7e)
a.emit(0xca); a.branch(0x10, 'copy_body'); a.emit(0x5c,0,0x20,0x7e)
boot = a.finish()
assert len(boot) < 0x2000
rom = bytearray([0xff])*0x20000
rom[:len(boot)] = boot
rom[0x2000:0x2000+len(body)] = body
rom[0x7fb0] = 0  # control ROM uses 1 and never touches FPGA registers
rom[0x7fc0:0x7fd5] = ('FXPAK GBC '+REV+' DIAG').encode().ljust(21,b' ')
rom[0x7fd5:0x7fdc] = bytes((0x20,0,7,0,1,0,0))
for off in (0x7fe4,0x7fe6,0x7fea,0x7fee,0x7ffa,0x7ffc,0x7ffe):
    struct.pack_into('<H',rom,off,0x8000)
rom[0x7fdc:0x7fe0] = b'\xff\xff\x00\x00'
checksum = sum(rom)&0xffff
struct.pack_into('<HH',rom,0x7fdc,checksum^0xffff,checksum)
(OUT/'gbc_snes.bin').write_bytes(rom)
# Stock-core control stops before probing the replacement FPGA registers.
control = bytearray(rom)
control[0x7fb0] = 1
control[0x7fdc:0x7fe0] = b'\xff\xff\x00\x00'
control_checksum = sum(control)&0xffff
struct.pack_into('<HH',control,0x7fdc,control_checksum^0xffff,control_checksum)
(OUT/(REV+'-SNES-display-check.sfc')).write_bytes(control)
result = dict(passed=True, diagnostic_only=True, actual_hardware=False,
              sha256=hashlib.sha256(rom).hexdigest(), crc32=f'0x{zlib.crc32(rom):08x}',
              control_sha256=hashlib.sha256(control).hexdigest(),
              boot_bytes=len(boot),body_bytes=len(body),body_labels=b.labels,
              boot_labels=a.labels,chars=CHARS,
              source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'build.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
