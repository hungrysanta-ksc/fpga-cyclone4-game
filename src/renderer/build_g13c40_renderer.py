from pathlib import Path
import ast,struct,json,hashlib,zlib,re
P=Path(__file__).resolve().parent;R=P/'results/g13c40-renderer-v2';R.mkdir(exist_ok=False)
B=P/'results/g13c26-renderer-v1';C15=P/'results/g13c15-renderer-v4'
rom=bytearray((B/'gbc_snes.bin').read_bytes());old=bytes(rom);meta=json.loads((C15/'verification.json').read_text())
scope={'struct':struct};tree=ast.parse((P/'build_gbc_product_renderer.py').read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Asm' or isinstance(n,ast.FunctionDef) and n.name=='dma'],type_ignores=[]),'<asm>','exec'),scope)
Asm=scope['Asm'];dma=scope['dma']
def jsr(a,n):a.absolute_label(0x20,n)
# WRAM local state50..56: selection,flags,last buttons,edges,command,status,temporary.
a=Asm(0xa000)
a.emit(0x08,0xc2,0x10,0xda,0x5a,0xe2,0x20) # PHP X/Y16 saves; DB is already0 in body
a.read(0x3f);a.branch(0xd0,'active');a.jump('return')
a.label('active');a.read(0x4218);a.emit(0x29,0x30,0xc9,0x30);a.branch(0xf0,'shoulders');a.jump('return')
a.label('shoulders');a.read(0x4219);a.emit(0x29,0x10);a.branch(0xd0,'open');a.jump('return')
a.label('open');a.stz(0x5b);a.stz(0x6005);a.stz(0x6006);a.write(0x600d,1)
# Wait for existing IRQ blank before changing PPU or HDMA ownership.
a.label('wait_blank');jsr(a,'service');a.read(0x0b); # BLANK_SEEN patched below from original module constants
a.branch(0xf0,'wait_blank');a.emit(0x78);a.write(0x4200,1);a.stz(0x420c)
jsr(a,'reply')
a.stz(0x50);a.stz(0x52);a.stz(0x57);jsr(a,'save_status')
a.write(0x2100,0x80);a.write(0x2115,0x80);a.stz(0x2116);a.write(0x2117,0x70);dma(a,0x00d000,3072,1,0x18)
a.stz(0x2105);a.write(0x2108,0x68);a.write(0x210b,0x70);a.stz(0x210f);a.stz(0x210f);a.write(0x2110,255);a.write(0x2110,3);a.write(0x212c,2)
# Four 2bpp text palettes: white, green values, dim panel, bright panel.
# Glyphs +96 set plane1 so the row/panel fill is opaque.
BACKDROP=0x1c40;WHITE=0x7fd9;GREEN=0x53e8;CYAN=0x6624;HIGHLIGHT=0x4520;PANEL=0x1020
PALETTES=[[BACKDROP,WHITE,HIGHLIGHT,WHITE],[BACKDROP,GREEN,HIGHLIGHT,GREEN],[BACKDROP,CYAN,PANEL,CYAN],[BACKDROP,WHITE,PANEL,WHITE]]
a.stz(0x2121);a.write(0x2122,BACKDROP&255);a.write(0x2122,BACKDROP>>8)
a.write(0x2121,32)
for pal in PALETTES:
 for c in pal:a.write(0x2122,c&255);a.write(0x2122,c>>8)
jsr(a,'draw');a.write(0x2100,15)
jsr(a,'release')
a.label('loop');jsr(a,'frame');jsr(a,'buttons');a.read(0x53);a.emit(0x29,0x80);a.branch(0xf0,'not_b');a.jump('close')
a.label('not_b');a.read(0x53);a.emit(0x29,8);a.branch(0xf0,'not_up');a.read(0x50);a.branch(0xd0,'up_dec');a.write(0x50,8);a.read(0x50);a.label('up_dec');a.emit(0x3a);a.sta(0x50);jsr(a,'draw')
a.label('not_up');a.read(0x53);a.emit(0x29,4);a.branch(0xf0,'not_down');a.read(0x50);a.emit(0x1a,0xc9,8);a.branch(0x90,'down_ok');a.emit(0xa9,0);a.label('down_ok');a.sta(0x50);jsr(a,'draw')
a.label('not_down');a.read(0x53);a.emit(0x29,1);a.branch(0xd0,'select');a.jump('loop')
a.label('select');a.read(0x50);a.branch(0xd0,'action');a.jump('close')
a.label('action');a.emit(0xc9,4);a.branch(0xd0,'not_slot')
a.read(0x57);a.emit(0x1a,0x29,3);a.sta(0x57);a.stz(0x55);jsr(a,'draw');a.jump('loop')
a.label('not_slot');a.emit(0xc9,5);a.branch(0xd0,'not_state_save');a.read(0x57);a.emit(0x09,0x10);a.jump('send_action')
a.label('not_state_save');a.emit(0xc9,6);a.branch(0xd0,'not_state_load');a.read(0x57);a.emit(0x09,0x20);a.jump('send_action')
a.label('not_state_load');a.emit(0xc9,7);a.branch(0xd0,'ordinary');a.emit(0xa9,5)
a.label('ordinary');a.emit(0x1a)
a.label('send_action');a.sta(0x54);a.write(0x55,5);jsr(a,'draw')
a.read(0x54);a.sta(0x600d);jsr(a,'reply')
jsr(a,'save_status')
a.read(0x54);a.emit(0xc9,6);a.branch(0xd0,'result');a.read(0x51);a.emit(0x29,0x40);a.branch(0xd0,'result')
jsr(a,'release');a.write(0x2100,0x80);a.write(0x600d,7)
a.label('restart_wait');a.jump('restart_wait')
a.label('result');a.read(0x51);a.emit(0x29,0x60,0xc9,0x20);a.branch(0xd0,'result_draw');a.read(0x54);a.emit(0x29,0xf0,0xc9,0x10);a.branch(0xd0,'result_load');a.write(0x55,1);a.branch(0x80,'result_draw');a.label('result_load');a.emit(0xc9,0x20);a.branch(0xd0,'result_draw');a.write(0x55,6);a.label('result_draw');jsr(a,'frame');jsr(a,'draw');a.jump('loop')
a.label('close');jsr(a,'release');a.write(0x600d,5);jsr(a,'reply');a.read(0x51);a.emit(0x29,64);a.branch(0xf0,'close_ok');jsr(a,'save_status');jsr(a,'draw');a.jump('loop');a.label('close_ok');jsr(a,'idle')
a.write(0x2100,0x80);a.stz(0x420c);a.write(0x2105,3);a.stz(0x210b);a.write(0x212c,1)
a.stz(0x2d);a.stz(0x2e);a.stz(0x2f);a.stz(0x20);a.stz(0x21)
a.write(0x4209,185);a.stz(0x420a);a.read(0x4211);a.write(0x4200,0x21);a.emit(0x58)
a.label('return');a.emit(0xc2,0x10,0x7a,0xfa,0x28,0x6b)
a.label('frame');a.label('out');jsr(a,'service');a.read(0x4212);a.emit(0x29,0x80);a.branch(0xd0,'out')
a.label('in');jsr(a,'service');a.read(0x4212);a.emit(0x29,0x80);a.branch(0xf0,'in')
a.label('joystart');a.read(0x4212);a.emit(0x29,1);a.branch(0xf0,'joystart');
a.label('joywait');a.read(0x4212);a.emit(0x29,1);a.branch(0xd0,'joywait');a.emit(0x60)
a.label('buttons');a.read(0x4219);a.emit(0x29,0x8c);a.sta(0x56);a.read(0x4218);a.emit(0x29,0x80);a.branch(0xf0,'no_a')
a.read(0x56);a.emit(0x09,1);a.sta(0x56)
a.label('no_a');a.read(0x52);a.emit(0x49,255,0x2d,0x56,0);a.sta(0x53);a.read(0x56);a.sta(0x52);a.emit(0x60)
a.label('release');jsr(a,'frame');a.read(0x4218);a.emit(0x0d,0x19,0x42);a.branch(0xd0,'release');a.stz(0x52);a.emit(0x60)
a.label('reply');jsr(a,'service');a.read(0x600d);a.branch(0x30,'reply')
a.label('received');a.sta(0x51);a.emit(0x60)
# Offer an upload boundary periodically while waiting, even before pause ACK.
a.label('service');a.emit(0xee,0x5b,0);a.read(0x5b);a.emit(0x29,0x1f);a.branch(0xd0,'service_done')
a.read(0x6002);a.emit(0x29,1);a.branch(0xd0,'service_done');a.write(0x6001,1)
a.label('service_done');a.emit(0x60)
a.label('idle');a.read(0x6002);a.emit(0x29,1);a.branch(0xd0,'idle');a.emit(0x60)
a.label('save_status');a.stz(0x55)
a.read(0x51);a.emit(0x29,4);a.branch(0xf0,'not_config_error');a.write(0x55,4);a.emit(0x60)
a.label('not_config_error');a.read(0x51);a.emit(0x29,0x48);a.branch(0xf0,'not_save_error');a.write(0x55,2);a.emit(0x60)
a.label('not_save_error');a.read(0x51);a.emit(0x29,16);a.branch(0xf0,'has_ram');a.write(0x55,3);a.emit(0x60)
a.label('has_ram');a.read(0x51);a.emit(0x29,32);a.branch(0xf0,'status_done');a.write(0x55,1)
a.label('status_done');a.emit(0x60)
a.label('draw')
# Four option maps; cursor and selected state slot are small direct overlays.
a.read(0x51);a.emit(0x29,3,0xc2,0x20,0x29,0xff,0)
for i in range(11):a.emit(0x0a)
a.emit(0x09,0,0x80);a.sta(0x4372);a.emit(0xe2,0x20)
a.write(0x2115,0x80);a.stz(0x2116);a.write(0x2117,0x68);a.write(0x4370,1);a.write(0x4371,0x18);a.write(0x4374,3);a.stz(0x4375);a.write(0x4376,8);a.write(0x420b,128)
# Selected row: source bank03:a000 + options*512 + selection*64.
a.read(0x50);a.emit(0xc2,0x20,0x29,255,0)
for i in range(6):a.emit(0x0a)
a.emit(0xaa)
a.read(0x51);a.emit(0x29,3,0)
for i in range(9):a.emit(0x0a)
a.emit(0x18,0x69,0,0xa0);a.sta(0x4372)
a.emit(0x8a,0x18,0x6d,0x72,0x43);a.sta(0x4372)
a.emit(0x8a,0x18,0x69,0xc0,0x68);a.sta(0x2116);a.emit(0xe2,0x20)
a.write(0x4375,64);a.stz(0x4376);a.write(0x420b,128)
# Cursor at x=2, y=6+2*selection, outside the selected row fill.
a.emit(0xc2,0x20,0x8a,0x18,0x69,0xc2,0x68);a.sta(0x2116);a.emit(0xe2,0x20)
a.write(0x2118,ord('>')-32);a.stz(0x2119)
# STATE SLOT value at x=24,y=14; green and highlighted only on its row.
a.write(0x2116,0xd8);a.write(0x2117,0x69)
a.read(0x50);a.emit(0xc9,4);a.branch(0xd0,'slot_plain')
a.read(0x57);a.emit(0x18,0x69,ord('1')-32+96);a.branch(0x80,'slot_digit')
a.label('slot_plain');a.read(0x57);a.emit(0x18,0x69,ord('1')-32)
a.label('slot_digit');a.sta(0x2118);a.write(0x2119,4)
# Status row y=24.
a.read(0x55);a.emit(0xc2,0x20,0x29,255,0)
for i in range(6):a.emit(0x0a)
a.emit(0x18,0x69,0,0xf0);a.sta(0x4372);a.emit(0xe2,0x20)
a.stz(0x2116);a.write(0x2117,0x6b);a.stz(0x4374);a.write(0x4375,64);a.stz(0x4376);a.write(0x420b,128);a.emit(0x60)
# Input adapter returns A bit0 and R-hold bit1. Suppress R when L or Start
# participates so L+R+Start can always enter the menu without acceleration.
a.label('fast_pad');a.read(0x20);a.emit(0x29,0x30,0xc9,0x10);a.branch(0xd0,'fast_pad_off')
a.read(0x21);a.emit(0x29,0x10);a.branch(0xd0,'fast_pad_off');a.read(0x20)
for _ in range(7):a.emit(0x4a)
a.emit(0x09,2,0x60)
a.label('fast_pad_off');a.read(0x20)
for _ in range(7):a.emit(0x4a)
a.emit(0x60)
code=bytearray(a.finish())
# Recover actual constants without importing the old mutating builder.
tree=ast.parse((C15/'build.py').read_text());constants={}
for n in tree.body:
 if isinstance(n,ast.Assign):
  try:
   val=ast.literal_eval(n.value)
   for target in n.targets:
    if isinstance(target,ast.Name):constants[target.id]=val
  except (ValueError,TypeError):pass
blank=constants['BLANK_SEEN'];assert blank!=0
i=a.labels['wait_blank']-0xa000+3;assert code[i:i+3]==bytes([0xad,0x0b,0]);code[i+1]=blank
assert len(code)<0x1000,len(code)
def words(v):return b''.join(struct.pack('<H',x) for x in v)
def put(tiles,x,y,text,pal=0,opaque=False):
 assert 0<=x and x+len(text)<=32
 for j,ch in enumerate(text):tiles[y*32+x+j]=(ord(ch)-32)+(96 if opaque else 0)+(pal<<10)
def panel_row(text):
 tiles=[0]*32
 for x in range(3,29):tiles[x]=96+(3<<10)
 put(tiles,2,0,'|',2);put(tiles,29,0,'}',2)
 put(tiles,3,0,text,3,True);assert len(text)<=26
 return tiles
maps=bytearray();highlights=bytearray()
for opts in range(4):
 tiles=[0]*1024
 put(tiles,2,2,'GAMEBOY COLOR CORE MENU')
 put(tiles,2,4,'~'*28,2)
 for i,text in enumerate(['RESUME GAME','WRITE SRAM','AUTO WRITE SRAM','SOUND','STATE SLOT','SAVE STATE','LOAD STATE','RESET GAME']):
  put(tiles,4,6+2*i,text)
 for y,text in [(10,'ON' if opts&1 else 'OFF'),(12,'OFF' if opts&2 else 'ON'),(14,'1')]:put(tiles,24,y,text,1)
 for y in (22,25):put(tiles,2,y,'~'*28,2)
 for y in (23,24):
  for x in range(3,29):tiles[y*32+x]=96+(2<<10)
  put(tiles,2,y,'|',2);put(tiles,29,y,'}',2)
 put(tiles,3,23,'STATUS',2,True)
 put(tiles,2,27,'A SELECT   B RETURN')
 for i in range(8):
  row=tiles[(6+2*i)*32:(7+2*i)*32].copy()
  for x in range(3,30):row[x]+=96
  highlights+=words(row)
 maps+=words(tiles)
statuses=b''.join(words(panel_row(x)) for x in ['READY','SAVED','FAILED / RESET IF NEEDED','NO SAVE RAM','SETTINGS ERROR','WORKING / PLEASE WAIT','LOADED'])
# Only replace the seven shifts in the existing G9 joypad adapter.
pat=bytes.fromhex('ad18428d2000')+bytes([0x4a])*7+bytes.fromhex('8d0660')
assert rom.count(pat)==1
site=rom.index(pat)+6
rom[site:site+7]=bytes([0x20,a.labels['fast_pad']&255,a.labels['fast_pad']>>8,0xea,0xea,0xea,0xea])
writes=[(0x6000,code),(0x7000,statuses),(0x18000,maps),(0x1a000,highlights)]
for off,data in writes:
 assert all(x==255 for x in rom[off:off+len(data)]),(hex(off),len(data));rom[off:off+len(data)]=data
# Add a glyph unused by existing loading UI.
glyph=bytes(sum(([int(s,2)<<2,0] for s in ['10000','01000','00100','00010','00100','01000','10000','00000']),[]));g=0x5000+(ord('>')-32)*16;rom[g:g+16]=glyph
# Lowercase glyphs used by the exact SaveRAM labels.
for ch,lines in {'a':['00000','00000','01110','00001','01111','10001','01111','00000'],'v':['00000','00000','10001','10001','10001','01010','00100','00000'],'e':['00000','00000','01110','10001','11111','10000','01110','00000']}.items():
 g=0x5000+(ord(ch)-32)*16;rom[g:g+16]=bytes(sum(([int(x,2)<<2,0] for x in lines),[]))
# Menu-only line glyphs; these characters are not used in the loading UI.
for ch,lines in {'/':[0,2,4,8,16,32,64,0],'~':[0,0,0,255,0,0,0,0],'|':[128]*8,'}':[1]*8}.items():
 g=0x5000+(ord(ch)-32)*16;rom[g:g+16]=bytes(sum(([x,0]for x in lines),[]))
# Duplicate normal glyphs with an opaque background plane.
for t in range(96):
 src=0x5000+t*16;dst=0x5600+t*16
 rom[dst:dst+16]=bytes(sum(([rom[src+y*2],255]for y in range(8)),[]))
# Extend the boot-copied WRAM extra section; keep all existing body addresses.
extra_len=meta['wram_extra_bytes'];tramp=0x8000+extra_len
trampoline=bytes([0x22,0,0xa0,0x7e,0xad,0x12,0x42,0x60]);rom[0x3000+extra_len:0x3000+extra_len+8]=trampoline
pat=bytes([0xa2,(extra_len-1)&255,(extra_len-1)>>8]);site=rom.index(pat,0,meta['boot_bytes']);rom[site+1:site+3]=struct.pack('<H',extra_len+7)
site=0x100+meta['body_labels']['request_prepare']-0x2000;assert rom[site:site+3]==bytes([0xad,0x12,0x42]);rom[site:site+3]=bytes([0x20,tramp&255,tramp>>8])
# Copy the menu to WRAM at boot, while the Game Boy is still held in reset.
# C29 ran it from cartridge SRAM, stealing output-writer slots.
end=meta['boot_bytes']-4;assert rom[end:end+4]==bytes.fromhex('5c00207e')
copy=Asm(0x8000+end);copy.ldx16(len(code)-1);copy.label('copy_menu')
copy.emit(0xbf,0,0xe0,0,0x9f,0,0xa0,0x7e,0xca);copy.branch(0x10,'copy_menu');copy.emit(0x5c,0,0x20,0x7e)
boot_tail=copy.finish();assert end+len(boot_tail)<=0x80
rom[end:end+len(boot_tail)]=boot_tail
rom[0x7fdc:0x7fe0]=bytes([255,255,0,0]);cs=sum(rom)&65535;rom[0x7fdc:0x7fe0]=struct.pack('<HH',cs^65535,cs)
(R/'gbc_snes.bin').write_bytes(rom);(R/'menu-code.bin').write_bytes(code);(R/'maps.bin').write_bytes(maps);(R/'statuses.bin').write_bytes(statuses);(R/'highlights.bin').write_bytes(highlights)
v=dict(passed=True,backdrop=BACKDROP,palettes=PALETTES,ui_layout=dict(title=[2,2],menu_x=4,menu_y=6,menu_step=2,value_x=24,status_y=24,footer_y=27),renderer_sha256=hashlib.sha256(rom).hexdigest(),crc32=zlib.crc32(rom),labels=a.labels,menu_code_bytes=len(code),trampoline=tramp,blank_seen=blank,body_labels=meta['body_labels'],changed_offsets=[i for i in range(len(rom)) if old[i]!=rom[i]],actual_hardware=False,menu_execution='7e:a000',menu_upload_service=True,boot_bytes=end+len(boot_tail))
(R/'verification.json').write_text(json.dumps(v,indent=2))
