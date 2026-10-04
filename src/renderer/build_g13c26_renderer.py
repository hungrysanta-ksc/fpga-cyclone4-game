from pathlib import Path
import ast,struct,hashlib,json,zlib
P=Path(__file__).resolve().parent;R=P/'results/g13c26-renderer-v1';R.mkdir(exist_ok=True);B=P/'results/g13c15-renderer-v4/gbc_snes.bin';rom=bytearray(B.read_bytes());scope={'struct':struct};tree=ast.parse((P/'build_gbc_product_renderer.py').read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Asm' or isinstance(n,ast.FunctionDef) and n.name=='dma'],type_ignores=[]),'<asm>','exec'),scope);Asm=scope['Asm'];dma=scope['dma']
tree=ast.parse((P/'build_gbc_diagnostic_renderer.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='GLYPHS' for t in n.targets));g=ast.literal_eval(node.value) if False else {};exec(compile(ast.Module(body=[node],type_ignores=[]),'<glyphs>','exec'),g);glyphs=g['GLYPHS'];glyphs['%']=['11001','11010','00100','01000','10110','00110','00000'];glyphs['#']=['11111']*7;glyphs['-']=['00000']*3+['11111']+['00000']*3
font=bytearray()
for i in range(96):
 ch=chr(i+32)
 for row in glyphs.get(ch,['00000']*7)+['00000']:font+=bytes([int(row,2)<<2,0])
def textrow(s):
 assert all(c in glyphs for c in s),s
 return [0]*((32-len(s))//2)+[ord(c)-32 for c in s]+[0]*(32-(32-len(s))//2-len(s))
def words(v):return b''.join(struct.pack('<H',x) for x in v)
base=[0]*1024;base[4*32:5*32]=textrow('GAME BOY COLOR');base[23*32:24*32]=textrow('FXPAK GBC')
records=[]
for i in range(107):
 if i<=100:rows=[textrow('LOADING AND CHECKING'),textrow(f'{i:3d}%'),textrow('#'*(i//5)+'-'*(20-i//5)),textrow('PLEASE WAIT')]
 elif i==101:rows=[textrow('LOADING SAVE DATA'),textrow('100%'),textrow('#'*20),textrow('PLEASE WAIT')]
 elif i==102:rows=[textrow('STARTING GAME'),textrow('100%'),textrow('#'*20),textrow('PLEASE WAIT')]
 else:rows=[textrow('LOAD FAILED'),textrow({103:'GAME READ OR VERIFY',104:'SAVE DATA READ',105:'CORE SETUP',106:'LOAD CONNECTION'}.get(i)),textrow(''),textrow('RETURNING TO MENU')]
 records.append(b''.join(words(row) for row in rows))
# Reset vector enters this isolated helper. Runtime body, DMA schedule and assets stay at their original addresses.
a=Asm(0xc800);a.emit(0x78,0xd8,0x18,0xfb,0xc2,0x10,0xe2,0x20);a.ldx16(0x1fff);a.emit(0x9a);a.lda8(0);a.emit(0x48,0xab,0xc2,0x20,0xa9,0,0,0x5b,0xe2,0x20)
a.absolute_label(0x20,'snapshot');a.read(0x600c);a.emit(0xc9,0x26);a.branch(0xf0,'ui');a.emit(0x4c,0,0x80)
a.label('ui');a.write(0x2100,0x80)
for reg in [0x4200,0x420c,0x2106,0x2123,0x2124,0x2125,0x212a,0x212b,0x212c,0x212d,0x212e,0x212f,0x2130,0x2131,0x2133]:a.stz(reg)
a.write(0x2115,0x80);a.stz(0x2116);a.stz(0x2117);dma(a,0x018800,0,0x09,0x18);dma(a,0x00d000,len(font),1,0x18)
a.stz(0x2116);a.write(0x2117,0x10);dma(a,0x00d800,2048,1,0x18)
a.stz(0x2121)
# Backdrop, text, spare cyan and white; BG1 uses palette zero.
palette=[0x1041,0x7f4a,0x7fff,0]
for c in palette:a.write(0x2122,c&255);a.write(0x2122,c>>8)
a.stz(0x2105);a.write(0x2107,0x10);a.stz(0x210b);a.stz(0x210d);a.stz(0x210d);a.write(0x210e,255);a.write(0x210e,3);a.write(0x212c,1);a.write(0x33,1)
a.label('loop');a.label('poll_out');a.read(0x4212);a.emit(0x29,0x80);a.branch(0xd0,'poll_out');a.label('poll_in');a.read(0x4212);a.emit(0x29,0x80);a.branch(0xf0,'poll_in');a.absolute_label(0x20,'snapshot');a.read(0x6009);a.sta(0x30);a.read(0x33);a.branch(0xd0,'first');a.read(0x30);a.emit(0xcd,0x31,0);a.branch(0xd0,'changed');a.jump('loop')
a.label('first');a.read(0x30);a.label('changed');a.stz(0x33);a.sta(0x31);a.emit(0xc9,103);a.branch(0x90,'index');a.lda8(106);a.read(0x30);a.emit(0xc9,0x84);a.branch(0xd0,'save_error');a.lda8(103);a.branch(0x80,'index');a.label('save_error');a.emit(0xc9,0x85);a.branch(0xd0,'other_error');a.lda8(104);a.branch(0x80,'index');a.label('other_error');a.lda8(106)
a.label('index');a.emit(0x18,0x69,0x80);a.sta(0x32)
a.label('wait_out');a.read(0x4212);a.emit(0x29,0x80);a.branch(0xd0,'wait_out');a.label('wait_in');a.read(0x4212);a.emit(0x29,0x80);a.branch(0xf0,'wait_in')
for row,off in [(9,0),(12,64),(14,128),(18,192)]:
 address=0x1000+row*32;a.write(0x2116,address&255);a.write(0x2117,address>>8);a.write(0x4370,1);a.write(0x4371,0x18);a.write(0x4372,off);a.read(0x32);a.sta(0x4373);a.write(0x4374,2);a.write(0x4375,64);a.stz(0x4376);a.write(0x420b,128)
a.write(0x2100,15);a.jump('loop')
a.label('snapshot');a.stz(0x6008);a.ldx16(0x2000);a.label('poll');a.read(0x6008);a.emit(0x29,3,0xc9,2);a.branch(0xf0,'snapshot_done');a.emit(0xca);a.branch(0xd0,'poll');a.label('snapshot_done');a.emit(0x60)
code=a.finish();assert len(code)<0x1000
writes=[(0x4800,code),(0x5000,font),(0x5800,words(base)),(0x10000,b''.join(records))];allowed=set()
for off,data in writes:
 assert all(x==255 for x in rom[off:off+len(data)]),(off,len(data));rom[off:off+len(data)]=data;allowed.update(range(off,off+len(data)))
rom[0x7ffc:0x7ffe]=struct.pack('<H',0xc800);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0]);cs=sum(rom)&65535;rom[0x7fdc:0x7fe0]=struct.pack('<HH',cs^65535,cs);allowed.update(range(0x7ffc,0x7ffe));allowed.update(range(0x7fdc,0x7fe0));old=B.read_bytes();diff=[i for i in range(len(rom)) if old[i]!=rom[i]];assert all(i in allowed for i in diff)
(R/'gbc_snes.bin').write_bytes(rom);(R/'ui-code.bin').write_bytes(code);(R/'font.bin').write_bytes(font);(R/'tilemap.bin').write_bytes(words(base));(R/'records.bin').write_bytes(b''.join(records));v=dict(passed=True,renderer_sha256=hashlib.sha256(rom).hexdigest(),crc32=zlib.crc32(rom),ui_bytes=len(code),labels=a.labels,changed_offsets=diff,gameplay_body_unchanged=True,baseline_sha256=hashlib.sha256(old).hexdigest(),palette=palette);(R/'verification.json').write_text(json.dumps(v,indent=2))


