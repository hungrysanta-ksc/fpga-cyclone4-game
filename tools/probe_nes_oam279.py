# SPDX-License-Identifier: MIT
"""Measure STOP-aware ROM-to-WRAM OAM pattern fill on actual65816.

Same admitted ARM274 packets and generic fallback; no target WRAM preload.
This isolated forced-blank CPU measurement is not a retimed whole RTL path.
"""
import inspect,json,shutil,sys
from pathlib import Path
import probe_nes_ordinary268 as base
import probe_nes_ordinary269 as stopped
from nes_delta231 import once


def rom(d, mode):
    source = inspect.getsource(base.rom)
    source = once(source, " c.label('pattern')", """ c.label('pattern')
 # Only the exact four-byte hidden-object pattern uses ROM DMA.
 c.emit(0xe2,0x20);lda(0x1101);c.emit(0xc9,4);cond(0xd0,'old_pattern')
 lda(0x1100);c.emit(0xc9,8);cond(0xd0,'old_pattern')
 c.emit(0xc2,0x20);lda(0x110c);c.emit(0xc9,4,0);cond(0xd0,'old_pattern')
 lda(0x1110);c.emit(0xc9,0,0xf0);cond(0xd0,'old_pattern')
 lda(0x1112);cond(0xd0,'old_pattern')
 lda(0x24);cond(0xf0,'old_pattern');c.emit(0xc9,1,2);cond(0xb0,'old_pattern')
 c.emit(0x29,3,0);cond(0xd0,'old_pattern')
 c.label('oam_fill279');lda(0x40);sta(0x2181);lda(0x24);sta(0x4305);c.emit(0xe2,0x20)
 template_fix={}
 for a,v in [(0x2183,1),(0x4300,0),(0x4301,0x80),(0x4302,0),(0x4303,0),(0x4304,0),(0x420b,1)]:
  if a in (0x4302,0x4303):template_fix[a]=len(c.data)+1
  c.store(a,v)
 c.jump('copied')
 c.label('old_pattern')""")
    source = once(source, " r=bytearray([255])*32768;",
        """ template_source=zero_source+1;c.labels['template_source']=template_source
 assert template_source+512<=0x8fc0
 body[template_fix[0x4302]]=template_source&255;body[template_fix[0x4303]]=template_source>>8
 r=bytearray([255])*32768;r[len(body)+1:len(body)+513]=bytes([0,240,0,0])*128;""")
    stop_source = inspect.getsource(stopped.rom)
    stop_source = once(stop_source, "s=inspect.getsource(old.rom)", "s=SOURCE279")
    namespace = dict(stopped.__dict__)
    namespace.update(old=base, SOURCE279=source)
    exec(compile(stop_source, "stop-oam279", "exec"), namespace)
    return namespace["rom"](d, mode)


def main():
    lua = once(base.LUA, "if a==0x6000 then return",
               "if a==0x6001 then return event(0,a,0) elseif a==0x6000 then return")
    lua = once(lua, "local shadow={}", """local shadow={}
local template_live=false;local template_reads=0;local template_writes=0
local template_fills=0;local template_total=0
emu.addMemoryCallback(function()
 template_live=true;template_reads=0;template_writes=0;template_fills=template_fills+1
end,emu.callbackType.exec,OAM_FILL279)
emu.addMemoryCallback(function(a,v)
 if template_live then
  assert(a==TEMPLATE279+template_reads,'template sequential read')
  assert(v==((template_reads%4==1)and 240 or 0),'template data')
  template_reads=template_reads+1
 end
end,emu.callbackType.read,TEMPLATE279,TEMPLATE279+511)
emu.addMemoryCallback(function(a,v)if template_live then template_writes=template_writes+1 end end,
 emu.callbackType.write,0x2180)
emu.addMemoryCallback(function()
 if template_live then
  local n=cases[at][15]+256*cases[at][16]
  assert(template_reads==n and template_writes==n,'template DMA length')
  template_total=template_total+template_reads;template_live=false
 end
end,emu.callbackType.exec,COPIED279)
""")
    lua = once(lua, "emu.stop(0)", """local t=assert(io.open(OUT..'/template-result.json','w'))
 t:write(string.format('{"fills":%d,"bytes":%d}',template_fills,template_total));t:close();emu.stop(0)""")
    ns = dict(base.__dict__)
    ns.update(rom=rom, LUA=lua, __file__=__file__, __doc__=__doc__)
    source = inspect.getsource(base.main)
    source = once(source, "probes/nes-joint264/arm01/frame",
                  "probes/nes-joint274/arm01/frame")
    source = once(source, " lua='local GUARDS='",
        """ lua='local OAM_FILL279='+str(labels['oam_fill279'])+'\\nlocal COPIED279='+str(labels['copied'])+'\\nlocal TEMPLATE279='+str(labels['template_source'])+'\\n'
 lua+='local GUARDS='""")
    exec(compile(source, "oam279-main", "exec"), ns)
    ns["main"]()
    d=Path(sys.argv[sys.argv.index('--out')+1])
    result=json.loads((d/'result.json').read_text())
    template=json.loads((d/'template-result.json').read_text())
    assert template['fills']==71
    result.update(template=template,template_bytes=512,
                  ROM_used_bytes=result['rom_body_bytes']+513)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(__file__,d/Path(__file__).name)


if __name__ == "__main__":
    main()
