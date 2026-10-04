"""Read frozen A7 fault telemetry before deliberately stopping SNES output.
Automatic faults and manual X both latch first, draw second. Never sample
again after stopping consumption: that would manufacture a buffer overrun.
"""
from pathlib import Path
import ast
P=Path(__file__).resolve().parent
WHY,CAP,BUF,ERR,PRE,SNAP,STAT,TXLO,TXHI=range(0x24,0x2d)

def assets(revision='G10'):
    # Reuse the existing hand-authored diagnostic font, without running its builder.
    tree=ast.parse((P/'build_gbc_diagnostic_renderer.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.Assign) and
           any(isinstance(t,ast.Name) and t.id in ('GLYPHS','CHARS') for t in n.targets)]
    scope={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<font>','exec'),scope)
    chars=scope['CHARS'];font=bytearray()
    for ch in chars:
        for row in scope['GLYPHS'][ch]+['00000']:font.extend((int(row,2)<<2,0))
    tilemap=bytearray(2048)
    labels=[(3,1,'FXPAK GBC '+revision+' DIAGNOSTIC'),(5,1,'WHY    ERR    STAT'),
            (6,1,'CG     HM     CHK'),(7,1,'CAP    BUF    PRE'),(8,1,'SLOT   GOT    WANT'),
            (10,1,'CH MD BB BK A1T  A2A  LC'),(18,1,'HEAD FIRST SIX TABLE BYTES'),
            (21,1,'END       PREV   PTR'),(24,1,'AUTO   SLOT   GOT    WANT')]
    for row,col,text in labels:
        for x,ch in enumerate(text):tilemap[2*(row*32+x+col)]=chars.index(ch)
    for ch in range(7):
        tilemap[2*((11+ch)*32+1)]=chars.index('0')
        tilemap[2*((11+ch)*32+2)]=chars.index(str(ch))
    return bytes(font),bytes(tilemap)

def emit_probe(a):
    a.label('g10_probe')
    a.read(0x4218);a.sta(0x30)
    a.write(0x6008,1);a.ldx16(0x400)
    a.label('g10_snapshot_wait')
    a.read(0x6008);a.sta(SNAP);a.emit(0x29,3,0xc9,2)
    a.branch(0xf0,'g10_snapshot_ok')
    a.emit(0xca);a.branch(0xd0,'g10_snapshot_wait')
    # Never present old CAP/BUF/ERR/PRE as the result of a timed-out request.
    for addr in (CAP,BUF,ERR,PRE):a.write(addr,255)
    a.write(WHY,2);a.jump('g10_show')
    a.label('g10_snapshot_ok')
    for i,addr in enumerate((CAP,BUF,ERR,PRE)):a.read(0x6009+i);a.sta(addr)
    a.read(ERR);a.branch(0xf0,'g10_no_fault')
    a.write(WHY,1);a.jump('g10_show')
    a.label('g10_no_fault')
    a.read(0x4218);a.emit(0x29,0x40);a.branch(0xf0,'g10_continue')
    a.write(WHY,3);a.jump('g10_show')
    a.label('g10_continue');a.emit(0x60)

def emit_screen(a,dma):
    a.label('g10_show')
    a.read(WHY);a.emit(0xc9,5);a.branch(0xd0,'c3_telemetry_done')
    a.write(0x6008,1);a.ldx16(0x400)
    a.label('c3_snapshot_wait');a.read(0x6008);a.sta(SNAP);a.emit(0x29,3,0xc9,2);a.branch(0xf0,'c3_snapshot_ok')
    a.emit(0xca);a.branch(0xd0,'c3_snapshot_wait')
    for addr in (CAP,BUF,ERR,PRE):a.write(addr,255)
    a.jump('c3_telemetry_done')
    a.label('c3_snapshot_ok')
    for i,addr in enumerate((CAP,BUF,ERR,PRE)):a.read(0x6009+i);a.sta(addr)
    a.label('c3_telemetry_done')
    # Snapshot reflects producer at stop, potentially newer than displayed page.
    a.read(0x6002);a.sta(STAT)
    a.read(0x6003);a.sta(TXLO);a.read(0x6004);a.sta(TXHI)
    a.emit(0x78)
    a.jsr('c1_capture')
    a.stz(0x4200);a.stz(0x420c);a.write(0x2100,0x80)
    a.jsr('r1_readback')
    a.jsr('c1_compare');a.jsr('c5_details')
    a.emit(0xc2,0x20);a.read(0x1b24);a.emit(0x29,0xff,0,0x0a,0xaa,0xbd,0,0x19);a.sta(0x1b34)
    a.read(0x1820);a.sta(0x1b38);a.emit(0xe2,0x20)
    for r in (0x2105,0x2106,0x210b,0x212d,0x212e,0x212f,0x2130,0x2131,0x2133):a.stz(r)
    a.write(0x2107,0x10);a.write(0x2115,0x80)
    a.stz(0x210d);a.stz(0x210d);a.write(0x210e,255);a.write(0x210e,255)
    a.stz(0x2116);a.stz(0x2117)
    font,tilemap=assets();dma(a,0x019000,len(font),1,0x18)
    a.stz(0x2116);a.write(0x2117,0x10);dma(a,0x019400,len(tilemap),1,0x18)
    a.stz(0x2121)
    for v in (0,0,255,127):a.write(0x2122,v) # black and white
    fields=[(5,5,WHY),(5,12,ERR),(5,19,STAT),(6,4,0x1b01),(6,11,0x1b08),(6,18,0x1b00),(7,5,CAP),(7,12,BUF),(7,19,PRE),
            (8,6,0x1b02),(8,12,0x1b05),(8,14,0x1b04),(8,20,0x1b07),(8,22,0x1b06),
            (22,1,0x1b67),(22,3,0x1b66),(22,11,0x1b69),(22,19,0x1b68),
            (25,1,0x1b23),(25,3,0x1b22),(25,9,0x1b24),(25,15,0x1b27),(25,17,0x1b26),(25,23,0x1b29),(25,25,0x1b28)]
    for ch in range(7):
        base=0x1a00+ch*11
        fields.extend((11+ch,col,base+off) for col,off in ((4,0),(7,1),(10,4),(13,3),(15,2),(18,9),(20,8),(23,10)))
    fields.extend((19,1+4*i,0x1b60+i) for i in range(6))
    for row,col,addr in fields:
        word=0x1000+row*32+col
        a.write(0x2116,word&255);a.write(0x2117,word>>8)
        invalid_guard=(0x1a00<=addr<0x1b00 or 0x1b01<=addr<0x1b10 or 0x1b60<=addr<=0x1b69)
        if invalid_guard:
            tag=f'c7_field_{row}_{col}'
            a.read(0x1b00);a.emit(0xc9,0xa1);a.branch(0xf0,tag+'_valid')
            # Uncollected values are blank; CHK00 explicitly identifies a skip.
            a.jump(tag+'_done');a.label(tag+'_valid')
        a.read(addr);a.emit(0x4a,0x4a,0x4a,0x4a);a.jsr('g10_hex')
        a.read(addr);a.emit(0x29,15);a.jsr('g10_hex')
        if invalid_guard:a.label(tag+'_done')
    a.write(0x212c,1);a.write(0x2100,15)
    a.label('g10_stop');a.jump('g10_stop')
    a.label('g10_hex');a.emit(0x18,0x69,1);a.sta(0x2118);a.stz(0x2119);a.emit(0x60)

    a.label('c5_details');a.read(0x1b00);a.emit(0xc9,0xa1);a.branch(0xf0,'c7_details_valid');a.emit(0x60);a.label('c7_details_valid')
    # Only after c1_capture froze channels and c1_compare finished. No runtime probe cost.
    a.stz(0x90);a.read(0x12);a.emit(0x49,1,0x0a,0x0a,0x0a,0x0a,0x0a,0x09,0x41);a.sta(0x91)
    a.write(0x92,0x7e);a.emit(0xa0,0,0)
    a.label('c5_head');a.emit(0xb7,0x90,0x99,0x60,0x1b,0xc8,0xc0,6,0);a.branch(0xd0,'c5_head')
    a.emit(0xc2,0x20);a.read(0x90);a.emit(0x18,0x6d,0x20,0x18);a.sta(0x1b66)
    # Read only WRAM, using frozen logical0 A2A. CPU reads cannot move HDMA.
    a.read(0x1a08);a.sta(0x90);a.emit(0xe2,0x20,0xa0,0,0,0xb7,0x90);a.sta(0x1b68)
    a.emit(0xc2,0x20);a.read(0x90);a.emit(0x3a);a.sta(0x90);a.emit(0xe2,0x20,0xb7,0x90);a.sta(0x1b69)
    a.emit(0x60)
