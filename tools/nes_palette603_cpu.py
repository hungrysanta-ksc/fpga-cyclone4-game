"""65816 diagnostic kernel: rebuild an inactive 512-byte CGRAM image from current NES color IDs."""
import binascii
import json
import os
import struct
import subprocess

from build_nes_trace_replay import Asm, Code

BODY, LENGTH, STOP, STATUS, DEST = 0x1000, 0x1080, 0x1082, 0x1084, 0x1800


def image(lut):
    c=Code(0x7e3000)
    op=c.absolute
    def reject_if(branch):
        c.emit(branch^0x20,3)
        c.jump('reject')
    def check_stop():
        op(0xad,STOP)
        reject_if(0xd0)
    c.label('gate')
    op(0xad,0x1086)
    c.branch(0xf0,'gate')
    c.label('start')
    check_stop()
    op(0xad,BODY);op(0x29,255);op(0xc9,4);reject_if(0xb0)
    op(0x29,1);c.branch(0xf0,'one')
    op(0xa9,64);c.branch(0x80,'size')
    c.label('one');op(0xa9,32)
    c.label('size');op(0x8d,2)
    c.emit(0x18);op(0x69,3);op(0xcd,LENGTH);reject_if(0xd0)
    # Two palette epochs must agree on the universal background color.
    op(0xad,2);op(0xc9,64);c.branch(0xd0,'clear')
    op(0xad,BODY+3);op(0x4d,BODY+35);op(0x29,255);reject_if(0xd0)
    c.label('clear')
    op(0xa2,510);op(0xa9,0)
    c.label('zero');op(0x9d,DEST);c.emit(0xca,0xca);c.branch(0x10,'zero')
    op(0xad,BODY);op(0x29,2);c.branch(0xf0,'colors')
    op(0xa2,126)
    c.label('raw');op(0xbd,0xb000);op(0x9d,DEST+128);c.emit(0xca,0xca);c.branch(0x10,'raw')
    c.label('colors');op(0xa2,0)
    c.label('color')
    op(0xbd,BODY+3);op(0x29,255);op(0xc9,64);reject_if(0xb0)
    c.emit(0x0a,0xa8);op(0xb9,0xb000);c.emit(0x48,0x8a,0x0a,0xa8)
    op(0xb9,0xb080);c.emit(0xa8,0x68);op(0x99,DEST);c.emit(0xe8)
    op(0xec,2);c.branch(0xd0,'color')
    c.label('verify');op(0xa9,65535);op(0x8d,0)
    op(0xa2,0)
    c.label('chunk');check_stop()
    c.label('byte')
    c.emit(0xa5,0,0xeb,0x85,4)
    op(0x5d,DEST);op(0x29,255);c.emit(0x0a,0xa8,0xa5,4)
    op(0x29,0xff00);op(0x59,0xb200);c.emit(0x85,0,0xe8,0x8a)
    op(0x29,63);c.branch(0xd0,'byte')
    op(0xe0,512);c.branch(0xd0,'chunk')
    c.emit(0xa5,0);op(0xcd,BODY+1);reject_if(0xd0)
    check_stop()
    op(0xa9,1);c.branch(0x80,'status')
    c.label('reject');op(0xa9,2)
    c.label('status');op(0x8d,STATUS)
    c.label('done');c.jump('done')
    code=c.finish()
    boot=Asm(0x8000)
    boot.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a)
    boot.absolute(0xa9,len(code)-1);boot.absolute(0xa2,0x8100);boot.absolute(0xa0,0x3000)
    boot.emit(0x54,0x7e,0,0xa9,0,0,0x48,0xab,0xab)
    boot.absolute(0x9c,0x1086);boot.long(0x5c,c.base)
    rom=bytearray([255])*32768
    rom[:len(boot.data)]=boot.finish()
    rom[256:256+len(code)]=code
    rom[0x3000:0x3080]=lut
    for i in range(64):
        epoch,slot=divmod(i,32)
        dest=epoch*16+slot if slot<16 else 128+64*epoch+16*((slot-16)//4)+slot%4
        struct.pack_into('<H',rom,0x3080+i*2,2*dest)
    for i in range(256):
        struct.pack_into('<H',rom,0x3200+i*2,binascii.crc_hqx(bytes([i]),0))
    rom[0x7fc0:0x7fd5]=b'PALETTE603'.ljust(21,b' ')
    rom[0x7fd5:0x7fe0]=bytes([32,0,5,0,1,0,0,255,255,0,0])
    for i in range(0x7fe0,0x8000,2):struct.pack_into('<H',rom,i,0x8000)
    h=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,h^65535,h)
    return rom,c.labels,len(code)


def simulate(folder,mesen,lut,body,expected,target,fault='normal'):
    folder.mkdir()
    rom,labels,code_size=image(lut)
    (folder/'probe.sfc').write_bytes(rom)
    (folder/'body.bin').write_bytes(body)
    (folder/'oracle.bin').write_bytes(expected)
    lua=r'''
local wr=emu.memType.snesWorkRam
local function read(f) local s=assert(io.open(dir..'/'..f,'rb'));local b=s:read('*a');s:close();return b end
local b,oracle=read('body.bin'),read('oracle.bin')
local armed=false
local times={}
local hooked=false
emu.addEventCallback(function()
 if hooked or emu.getState().masterClock+400000<target then return end
 hooked=true
 emu.addMemoryCallback(function()
 if armed or emu.getState().masterClock<target then return end
 armed=true
 for i=1,#b do emu.write(0xfff+i,b:byte(i),wr) end
 for i=0,511 do emu.write(0x1800+i,0xa7,wr) end
 emu.write(0x1080,#b,wr);emu.write(0x1081,0,wr)
 emu.write(0x1082,0,wr);emu.write(0x1083,0,wr);emu.write(0x1086,1,wr)
end,emu.callbackType.exec,labels.gate)
end,emu.eventType.endFrame)
emu.addMemoryCallback(function() times.start=emu.getState().masterClock end,emu.callbackType.exec,labels.start)
emu.addMemoryCallback(function()
 times.verify=emu.getState().masterClock
 if fault=='memory' then emu.write(0x1890,emu.read(0x1890,wr)~1,wr) end
end,emu.callbackType.exec,labels.verify)
local n=0
emu.addMemoryCallback(function()
 n=n+1;if n==2 and fault=='stop' then emu.write(0x1082,1,wr) end
end,emu.callbackType.exec,labels.chunk)
local finished=false
emu.addMemoryCallback(function()
 if finished then return end
 finished=true
 local mismatches=0
 for i=1,512 do if emu.read(0x17ff+i,wr)~=oracle:byte(i) then mismatches=mismatches+1 end end
 local f=assert(io.open(dir..'/result.txt','w'));f:write(string.format('%d %d %d %d %d',emu.read(0x1084,wr),mismatches,times.start,times.verify or 0,emu.getState().masterClock));f:close();emu.stop()
end,emu.callbackType.exec,labels.done)
'''
    setup='local dir='+json.dumps(folder.as_posix(),ensure_ascii=False)+'\nlocal target='+str(target)+'\nlocal fault='+json.dumps(fault)+'\n'
    setup+='local labels={'+','.join(k+'='+str(v) for k,v in labels.items())+'}\n'
    (folder/'run.lua').write_text(setup+lua,encoding='utf8')
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    with (folder/'mesen.log').open('wb') as log:
        subprocess.run([str(mesen),'--testRunner',str(folder/'run.lua'),str(folder/'probe.sfc'),'--timeout=40',
                        '--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],
                       cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=55,creationflags=subprocess.CREATE_NO_WINDOW)
    status,wrong,start,mid,end=map(int,(folder/'result.txt').read_text().split())
    assert target<=start<target+256 and status==(1 if fault=='normal' else 2)
    if status==1:assert wrong==0
    return dict(status=status,mismatches=wrong,start=start,verified=end,restore_clocks=mid-start if mid else None,
                total_clocks=end-start,code_B=code_size)
