"""Build the FF3 SNES menu from the existing play client and GBC font."""
import ast
import json
from pathlib import Path

from boot_nes_column854 import build
from build_nes_trace_replay import Code
from nes_native_local165 import call
from nes_receipt941 import BASE as LOADER_SOURCE

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT.parent/'probes/nes-blank960/retry'
TEXT=('NES CORE MENU','RESUME GAME','WRITE SRAM','STATE SLOT','SAVE STATE',
      'LOAD STATE','EXIT TO MENU','A SELECT   B RETURN','OK','EMPTY')
CHARS=' 1234'+''.join(sorted(set(''.join(TEXT))-set(' 1234')))
SCRATCH=0x7e3c00  # after WRAM client end, before renderer commands at 7e:4000
PENDING,ROW,SLOT,HDMA,PREVIOUS,PRESSED,COLOR0,COLOR65,RESULT=range(0,18,2)


def overlay(*, turbo=False):
    c=Code(0x9400)
    label,br,emit=c.label,c.branch,c.emit
    def get(n):c.long(0xaf,SCRATCH+n)
    def put(n):c.long(0x8f,SCRATCH+n)
    def lda8(x):emit(0xa9,x)
    def lda16(x):c.absolute(0xa9,x)
    def ldx(x):c.absolute(0xa2,x)
    def read(a):c.absolute(0xad,a)
    def write(a):c.absolute(0x8d,a)
    def set16(a,x):
        emit(0xc2,0x20);lda16(x);write(a);emit(0xe2,0x20)
    def far(op,target):emit(op^0x20,3);c.jump(target)
    label('boot')
    lda8(0)
    for n in (PENDING,ROW,SLOT,HDMA,RESULT):put(n)
    if turbo:put(18)
    c.store(0x7000,2);emit(0x6b)
    for mask in (0,2,14):
        label('hdma'+str(mask));lda8(mask);put(HDMA);write(0x420c);emit(0x6b)
    label('pad')  # same A16 / X16 and DBR=0 as the original STA $6002
    emit(0x48);get(PENDING);emit(0x29,0xff,0);br(0xd0,'await_open')
    emit(0x68,0x48,0x29,0x30,0x10,0xc9,0x30,0x10);br(0xd0,'ordinary')
    emit(0x68);lda16(0);write(0x6002);emit(0xe2,0x20)
    lda8(1);put(PENDING);write(0x7002);emit(0x6b)
    label('ordinary');emit(0x68)
    if turbo:call(c,'turbo_pad')
    write(0x6002);emit(0xe2,0x20,0x6b)
    label('await_open');emit(0x68);lda16(0);write(0x6002);emit(0xe2,0x20)
    read(0x6002);emit(0xc9,1);br(0xf0,'open');emit(0x6b)
    label('open');emit(0xda,0x5a);lda8(0);put(ROW);put(RESULT)
    call(c,'blank');c.store(0x420c,0);c.store(0x2115,0x80)
    for cg,n in ((0,COLOR0),(65,COLOR65)):
        c.store(0x2121,cg);read(0x213b);put(n);read(0x213b);emit(0x29,0x7f);put(n+1)
    # Back up only the charset and the map touched by this dialog. Setting
    # VMADD for each word refreshes the VRAM read buffer before the read.
    for addr,size,back in ((0x7000,len(CHARS)*16,0x7ef800),(0x7c00,2048,0x7ef000)):
        emit(0xc2,0x20);ldx(0);label(f'backup{addr}')
        emit(0x8a,0x4a,0x18);c.absolute(0x69,addr);write(0x2116);read(0x2139)
        c.long(0x9f,back);emit(0xe8,0xe8);c.absolute(0xe0,size);br(0xd0,f'backup{addr}');emit(0xe2,0x20)
    c.store(0x2121,0);c.store(0x2122,0);c.store(0x2122,0)
    c.store(0x2121,65);c.store(0x2122,255);c.store(0x2122,127)
    c.store(0x2109,0x7c);c.store(0x210c,7)
    for a in (0x2111,0x2111,0x2112,0x2112):c.absolute(0x9c,a)
    set16(0x2116,0x7000);ldx(0);label('fontloop')
    emit(0xbf,0,0,0);font_ptr=len(c.data)-3
    write(0x2118);c.absolute(0x9c,0x2119);emit(0xe8);c.absolute(0xe0,len(CHARS)*8);br(0xd0,'fontloop')
    set16(0x2116,0x7c00);ldx(1024);emit(0xc2,0x20);lda16(0)
    label('clear');write(0x2118);emit(0xca);br(0xd0,'clear');emit(0xe2,0x20)
    def vaddr(row,col):set16(0x2116,0x7c00+row*32+col)
    text_refs=[]
    for i,s in enumerate(TEXT[:8]):
        vaddr(3 if i==0 else 24 if i==7 else 5+2*i,4)
        ldx(0);text_refs.append((len(c.data)-2,s));call(c,'text')
    c.store(0x212c,4);emit(0xc2,0x20);lda16(0xffff);put(PREVIOUS);emit(0xe2,0x20)
    label('redraw')
    for i in range(6):
        vaddr(7+2*i,2);get(ROW);emit(0xc9,i,0xd0,4,0xa9,CHARS.index('X'),0x80,2,0xa9,0)
        write(0x2118);c.absolute(0x9c,0x2119)
    vaddr(11,18);get(SLOT);emit(0x18,0x69,1);write(0x2118);c.absolute(0x9c,0x2119)
    vaddr(21,4);get(RESULT);br(0xf0,'end_status')
    emit(0xc9,1);br(0xd0,'empty')
    for ch in 'OK   ':lda8(CHARS.index(ch));write(0x2118);c.absolute(0x9c,0x2119)
    br(0x80,'end_status');label('empty')
    for ch in 'EMPTY':lda8(CHARS.index(ch));write(0x2118);c.absolute(0x9c,0x2119)
    label('end_status');c.store(0x2100,15)
    label('input');call(c,'field')
    label('pad_ready');read(0x4212);emit(0x29,0x81);br(0xd0,'pad_ready')
    emit(0xc2,0x20);read(0x4218);put(PRESSED)
    get(PREVIOUS);emit(0x49,0xff,0xff);c.long(0x2f,SCRATCH+PRESSED);emit(0x48)
    get(PRESSED);put(PREVIOUS);emit(0x68);put(PRESSED);emit(0xe2,0x20)
    get(PRESSED+1);emit(0x29,0x80);far(0xd0,'resume')
    get(PRESSED+1);emit(0x29,0x0c);br(0xf0,'choose')
    emit(0xc9,8);get(ROW);br(0x90,'down')
    emit(0x3a);br(0x10,'rowok');lda8(5);br(0x80,'rowok')
    label('down');emit(0x1a,0xc9,6);br(0x90,'rowok');lda8(0)
    label('rowok');put(ROW);c.jump('update')
    label('choose');get(PRESSED);emit(0x29,0x80);far(0xf0,'input')
    get(ROW);far(0xf0,'resume');emit(0xc9,2);br(0xd0,'act')
    get(SLOT);emit(0x1a,0x29,3);put(SLOT);c.jump('update')
    label('act');emit(0xc9,1);br(0xd0,'state');lda8(2);br(0x80,'request')
    label('state');emit(0xc9,3);br(0xd0,'load');get(SLOT);emit(0x09,0x10);br(0x80,'request')
    label('load');emit(0xc9,4);br(0xd0,'exit');get(SLOT);emit(0x09,0x20);br(0x80,'request')
    label('exit');lda8(7)
    label('request');write(0x7002);label('wait');call(c,'check_stop');read(0x6002)
    br(0x30,'wait');put(RESULT)
    label('update');call(c,'blank');c.jump('redraw')
    label('resume');call(c,'blank')
    for addr,size,back in ((0x7000,len(CHARS)*16,0x7ef800),(0x7c00,2048,0x7ef000)):
        set16(0x2116,addr);emit(0xc2,0x20);ldx(0);label(f'restore{addr}')
        c.long(0xbf,back);write(0x2118);emit(0xe8,0xe8);c.absolute(0xe0,size)
        br(0xd0,f'restore{addr}');emit(0xe2,0x20)
    for cg,n in ((0,COLOR0),(65,COLOR65)):
        c.store(0x2121,cg);get(n);write(0x2122);get(n+1);write(0x2122)
    call(c,'field');c.store(0x212c,0x11);get(HDMA);write(0x420c);c.store(0x2100,15)
    c.store(0x7002,5);label('resume_ack');call(c,'check_stop');read(0x6002);br(0x30,'resume_ack')
    lda8(0);put(PENDING);emit(0x7a,0xfa,0x6b)
    label('blank');call(c,'field');c.store(0x2100,0x80);emit(0x60)
    label('field');call(c,'check_stop');read(0x4212);br(0x30,'field')
    label('vblank');read(0x4212);br(0x10,'vblank')
    # Auto-joypad busy can start after the VBlank flag. Read on the following
    # active-field edge, as the game does, for all input samples.
    emit(0x60)
    label('check_stop');read(0x6001);br(0x30,'stopped');emit(0x60)
    label('stopped');br(0x80,'stopped')  # ARM owns reset and verified base return.
    label('text');c.absolute(0xbd,0);br(0x30,'text_done')
    write(0x2118);c.absolute(0x9c,0x2119);emit(0xe8);br(0x80,'text')
    label('text_done');emit(0x60)
    if turbo:
        # The pad service takes one settled auto-joypad sample per serviced
        # TV field, independently of whether the NES renderer publishes.
        label('turbo_pad');emit(0x48);c.absolute(0x89,0x4040);br(0xd0,'turbo_held')
        lda16(0);put(18);emit(0x68,0x60)
        label('turbo_held');get(18);emit(0x1a);c.absolute(0x29,3);put(18)
        c.absolute(0x89,2);br(0xd0,'turbo_off')
        emit(0x68,0x48);c.absolute(0x29,0x4040);emit(0x0a,0x03,1,0x83,1)
        label('turbo_off');emit(0x68,0x60)
    for pos,s in text_refs:
        c.data[pos:pos+2]=(c.base+len(c.data)).to_bytes(2,'little')
        c.emit(*(CHARS.index(ch) for ch in s),255)
    font=c.base+len(c.data)
    c.data[font_ptr:font_ptr+3]=font.to_bytes(3,'little')
    tree=ast.parse((ROOT/'src/renderer/base/build_gbc_diagnostic_renderer.py').read_text())
    table=next(n.value for n in tree.body if isinstance(n,ast.Assign)
               and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='GLYPHS')
    glyphs={k.value:ast.literal_eval(v) for k,v in zip(table.keys,table.values)
            if k.value in CHARS and k.value!=' '}
    glyphs[' ']=['00000']*7
    for ch in CHARS:c.emit(*(int(row,2)<<2 for row in glyphs[ch]),0)
    return c.finish(),c.labels


def program(out, *, turbo=False):
    rom,entry=overlay(turbo=turbo)
    original=(ORIGINAL/'body.bin').read_bytes()
    body=original
    if turbo:
        # The compact-row DMA needs a literal FF, formerly read from an
        # unmapped address that the menu now occupies. Reserve the final
        # byte of its ROM explicitly; verify the installed byte below.
        assert len(rom)<2048
        old=bytes.fromhex('a9 08 18 8d 00 43 a9 be 97 8d 02 43')
        assert body.count(old)==1
        body=body.replace(old,old[:7]+bytes.fromhex('ff 9b')+old[9:])
    for old,label in [(bytes.fromhex('8d0260e220'),'pad'),(bytes.fromhex('a9028d0070'),'boot')]+[
        (bytes((0xa9,n,0x8d,0x0c,0x42)),'hdma'+str(n)) for n in (0,2,14)]:
        assert body.count(old)==1,(old,body.count(old))
        body=body.replace(old,b'\x22'+entry[label].to_bytes(3,'little')+b'\xea')
    build(LOADER_SOURCE,out,body,json.loads((ORIGINAL/'labels.json').read_text()),
          compact_mvn=True,minimum=2,short_pairs=True)
    assert len(rom)<=2048,len(rom)
    hexfile=out/'sink-program.hex'
    with hexfile.open('a',newline='\n') as f:
        for byte in rom.ljust(2048,b'\xff'):f.write(f'{byte:02x}\n')
    image=bytearray((out/'sink165.sfc').read_bytes());image[0x1400:0x1400+len(rom)]=rom
    (out/'sink165.sfc').write_bytes(image)
    if turbo:
        assert bytes.fromhex(hexfile.read_text())[0x1bff]==image[0x1bff]==255
    (out/'menu-labels.json').write_text(json.dumps(entry,indent=2))
    return len(rom)
