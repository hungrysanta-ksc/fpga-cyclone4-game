# SPDX-License-Identifier: MIT
"""Actual 65816 descriptor/staging consumer, isolated from full RTL schedule.

Retains STOP-aware zero reuse and OAM ROM DMA. This kernel does not prove
VBlank or the new RTL ordinary adapter; those require a coupled run.
"""
import inspect
import probe_nes_oam279 as oam
import probe_nes_ordinary268 as base
from nes_delta231 import once


def descriptor(s):
    a=s.index("lda(0x6000);cond(0xf0,'next');")
    b=s.index(" c.label('execute');",a)
    s=s[:a]+'''lda(0x6000);cond(0xf0,'next')
 # Normalized descriptor: op/domain/start/encoded/span/bank, no wire header.
 for src,dst in [(0x6060,0x1100),(0x6061,0x1101),(0x6062,0x110a),(0x6063,0x110b),
                 (0x6064,0x110c),(0x6065,0x110d),(0x6066,0x110e),(0x6067,0x110f)]:
  lda(src);sta(dst)
 lda(0x6068);c.emit(0x1a);sta(0x1104);c.store(0x1105,0)
 for i in range(4):lda(0x6048+i);sta(0x60+i)
 check_stop();c.emit(0xc2,0x20);lda(0x110c);sta(0x4305);c.emit(0xe2,0x20)
 for a,v in [(0x2181,0x10),(0x2182,0x11),(0x2183,0),(0x4300,0),(0x4301,0x80),
             (0x4302,0),(0x4303,8),(0x4304,0x40),(0x420b,1)]:c.store(a,v)
'''+s[b:]
    a=s.index(" c.label('ack');");b=s.index(" c.label('stop');",a)
    s=s[:a]+''' c.label('ack');check_stop()
 for i in range(4):lda(0x60+i);sta(0x604c+i)
 c.store(0x6059,0xa5);c.jump('next')
'''+s[b:]
    return s


def rom(d,mode):
    s=inspect.getsource(oam.rom)
    s=once(s,'stop_source = inspect.getsource(stopped.rom)', '''stop_source = inspect.getsource(stopped.rom)
    stop_source=once(stop_source," ns=dict(old.__dict__);", " s=descriptor(s)\\n ns=dict(old.__dict__);")''')
    s=once(s,'namespace.update(old=base, SOURCE279=source)', 'namespace.update(old=base, SOURCE279=source, descriptor=descriptor)')
    ns=dict(oam.__dict__);ns['descriptor']=descriptor
    exec(compile(s,'descriptor313-rom','exec'),ns)
    return ns['rom'](d,mode)


def main():
    lua=base.LUA
    a=lua.index('emu.addMemoryCallback(function(a,v)if a==0x6000')
    b=lua.index('emu.addMemoryCallback(function()execute=',a)
    lua=lua[:a]+'''local descriptor_reads=0
emu.addMemoryCallback(function(a,v)
 if a==0x6001 then return event(0,a,0) end
 if a==0x6000 then return event(0,a,1) end
 if a>=0x6048 and a<=0x604b then
  local token=at
  return event(0,a,math.floor(token/2^(8*(a-0x6048)))%256)
 end
 local offsets={0,1,10,11,12,13,14,15}
 local i=a-0x6060;assert(i==descriptor_reads,'descriptor read order')
 descriptor_reads=descriptor_reads+1;first=first or clock()
 return event(0,a,i==8 and ((word(4)-1)%2) or p(offsets[i+1]))
end,emu.callbackType.read,0x6000,0x6068)
emu.addMemoryCallback(function(a,v)
 local i=a-0x400800;assert(i==reads,'staging read order')
 lastread=clock();reads=reads+1;return event(0,a,p(16+i))
end,emu.callbackType.read,0x400800,0x4008ff)
'''+lua[b:]
    a=lua.index(' if a~=0x601c');b=lua.index(' local count=p(0)',a)
    lua=lua[:a]+''' if a~=0x6059 then ack[a-0x604c]=v;return end
 if zero_live then assert(zero_reads==1100 and zero_writes==1100,'fixed ROM DMA count');zero_live=false;zero_bytes=zero_bytes+zero_writes end
 assert(v==0xa5 and reads==word(12) and descriptor_reads==9,'consume coverage')
 local token=at
 for i=0,3 do assert(ack[i]==math.floor(token/2^(8*i))%256,'consume token')end
'''+lua[b:]
    lua=once(lua,'at=at+1;reads=0;', 'at=at+1;descriptor_reads=0;reads=0;')
    lua=once(lua,'end,emu.callbackType.write,0x6010,0x601c)', 'end,emu.callbackType.write,0x604c,0x6059)')
    ns=dict(base.__dict__);ns.update(rom=rom,LUA=lua,__file__=__file__,__doc__=__doc__)
    source=once(inspect.getsource(base.main),'probes/nes-joint264/arm01/frame',
                'probes/nes-joint274/arm01/frame')
    exec(compile(source,'consumer313-main','exec'),ns)
    ns['main']()


if __name__=='__main__':main()
