# SPDX-License-Identifier: MIT
"""Run actual65816 DMA/HDMA/PPU for both VRAM banks and compare every pixel.
Synthetic final NES colors, not actual SMB3 frames or production client.
"""
from pathlib import Path
import argparse,hashlib,json,os,struct,subprocess
from nes_patch181 import encode,LAYOUTS
from build_nes_trace_replay import Code
from build_nes_game164 import palette
ROOT=Path(__file__).resolve().parents[1]
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ROWS=[0,1,7,8,185,186,223]
CAPTURED=None
def raw(y,x,phase):return (y*11+x*3+x//7+phase*19)&63
def fixture(phase):return [(y,bytes(raw(y,x,phase) if CAPTURED is None else (CAPTURED[y,x]+phase*19)&63 for x in range(256))) for y in ROWS]
def build(out):
    plans=[encode(fixture(i),i) for i in range(2)]
    c=Code(0x8000);payload=bytearray()
    c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab)
    for a,v in [(0x2100,128),(0x4200,0),(0x420c,0),(0x2105,0),(0x2106,0),(0x2107,0x31),(0x210b,0),(0x2101,1),
                (0x212c,17),(0x212d,0),(0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),(0x2132,224),(0x2133,0),(0x2115,128)]:c.store(a,v)
    for a in range(0x2123,0x212c):c.store(a,0)
    def blank(name):
        c.label(name+'a');c.absolute(0xad,0x4212);c.branch(0x30,name+'a')
        c.label(name+'b');c.absolute(0xad,0x4212);c.branch(0x10,name+'b')
    def upload(kind,address,data):
        source=0xc000+len(payload);payload.extend(data)
        if kind=='vram':
            c.store(0x2116,(address//2)&255);c.store(0x2117,address//512);mode,port=1,0x18
        elif kind=='wram':
            c.store(0x2181,address&255);c.store(0x2182,address>>8);c.store(0x2183,0);mode,port=0,0x80
        elif kind=='cgram':c.store(0x2121,0);mode,port=2,0x22
        else:c.store(0x2102,0);c.store(0x2103,0);mode,port=0,4
        for a,v in [(0x4300,mode),(0x4301,port),(0x4302,source&255),(0x4303,source>>8),(0x4304,0),(0x4305,len(data)&255),(0x4306,len(data)>>8),(0x420b,1)]:c.store(a,v)
    lut=palette();cg=bytearray(512)
    for i,k in enumerate([15,1,33,48]):cg[i*2:i*2+2]=lut[k*2:k*2+2]
    cg[128:256]=lut;cg[258:260]=lut[0x16*2:0x16*2+2];upload('cgram',0,cg)
    # Normal rows retain a sprite crossing the two patch rows. If OBJ remains
    # enabled in mode3 it covers patched pixels and the full-image check fails.
    oam=bytearray(544)
    for i in range(128):oam[i*4+1]=240
    oam[:4]=bytes([80,184,0,0x30]);upload('oam',0,oam)
    pattern=bytes(v for y in range(8) for v in (0xaa,0xcc))
    obj=bytes([255,0]*8)+bytes(16)
    table_addresses=[]
    for i,p in enumerate(plans):
        l=p['layout'];upload('vram',l['bg'],pattern);upload('vram',l['obj'],obj)
        upload('vram',l['map'],bytes(2048));upload('vram',l['patch'],p['chr']);upload('vram',l['patch_map'],p['map'])
        addrs=[]
        for j,t in enumerate(p['hdma']):
            address=0x9000+i*0x1000+j*0x400;upload('wram',address,t);addrs.append(address)
        table_addresses.append(addrs)
    blank('first')
    for phase in range(2):
        if phase:
            c.label('wait');c.absolute(0xad,0x6000);c.branch(0xf0,'wait');blank('flip');c.store(0x420c,0)
        c.store(0x210b,0 if phase==0 else 6);c.store(0x2101,1 if phase==0 else 2)
        for j,(address,port,mode) in enumerate(zip(table_addresses[phase],[5,0x2c,0x0d],[4,4,3]),1):
            for off,val in [(0,mode),(1,port),(2,address&255),(3,address>>8),(4,0x7e)]:c.store(0x4300+j*16+off,val)
        c.store(0x420c,14)
        if not phase:c.store(0x2100,15)
        c.store(0x7000,phase+1)
    c.label('done');c.branch(0x80,'done');code=c.finish()
    assert len(code)<0x4000 and len(payload)<0x3fc0,(len(code),len(payload))
    rom=bytearray([255])*32768;rom[:len(code)]=code;rom[0x4000:0x4000+len(payload)]=payload
    rom[0x7fc0:0x7fd5]=b'NES ROW PATCH181'.ljust(21,b' ');rom[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0]);rom[0x7fdc:0x7fe0]=bytes([255,255,0,0])
    for off in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,off,0x8000)
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum)
    (out/'native.sfc').write_bytes(rom)
    return dict(code_bytes=len(code),payload_bytes=len(payload),hdma_bytes=[list(map(len,p['hdma'])) for p in plans])
def expected(phase):
    lut=struct.unpack('<64H',palette());data=bytearray(7*256*3)
    for y in range(224):
        for x in range(256):
            if y in ROWS:k=raw(y,x,phase)
            elif 80<=x<88 and 184<=y<192:k=0x16
            else:k=[15,1,33,48][((0xaa>>(7-x%8))&1)|(((0xcc>>(7-x%8))&1)<<1)]
            value=lut[k];data.extend((((value>>s)&31)<<3)|(((value>>s)&31)>>2) for s in [0,5,10])
    data.extend(bytes(8*256*3));return bytes(data)
def main():
    global CAPTURED
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--mesen',type=Path,required=True);p.add_argument('--pixels',type=Path);a=p.parse_args()
    assert not a.out.exists();a.out.mkdir(parents=True)
    if a.pixels:
        CAPTURED={}
        for line in a.pixels.read_text().splitlines():
            y,x,value=line.split();key=(int(y),int(x));assert key not in CAPTURED;CAPTURED[key]=int(value,16)
        assert sorted(CAPTURED)==[(y,x) for y in ROWS for x in range(256)]
    negative=0
    for bad in [[(224,bytes(256))],[(0,bytes(255))],[(0,bytes([64])*256)],[(2,bytes(256)),(1,bytes(256))],[(1,bytes(256))]*2,[(i,bytes(256)) for i in range(8)]]:
        try:encode(bad,0)
        except ValueError:negative+=1
        else:raise AssertionError('invalid rows accepted')
    result=build(a.out)
    (a.out/'capture.lua').write_text('local OUT_DIR='+json.dumps(a.out.as_posix())+'\n'+(ROOT/'snes/video_probe/capture_native_commands165.lua').read_text(),encoding='utf8')
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    with (a.out/'mesen.log').open('wb') as f:r=subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.out/'native.sfc'),'--timeout=40','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0,(a.out/'mesen.log').read_text(errors='replace')[-2000:]
    for phase in range(2):
        gold=expected(phase);(a.out/f'expected-{phase+1}.rgb').write_bytes(gold)
        actual=(a.out/f'frame-{phase+1}.rgb').read_bytes()
        assert actual==gold,(phase,len(actual),len(gold),sum(x!=y for x,y in zip(actual,gold)))
    result.update(passed=True,full_images=2,visible_pixels=2*224*256,patch_rows_per_image=7,rejected_inputs=negative,mesen_sha256=H(a.mesen),integrated_client=False,hardware=False,rtl_capture_input_sha256=H(a.pixels) if a.pixels else None,
        public_sources={n:H(ROOT/n) for n in ['tools/nes_patch181.py','tools/test_nes_patch181_snes.py','snes/video_probe/capture_native_commands165.lua','tools/build_nes_game164.py','tools/build_nes_trace_replay.py']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
