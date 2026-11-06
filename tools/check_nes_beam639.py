# SPDX-License-Identifier: MIT
"""Align the idle caller, then measure the original 65816 from entry to STOP."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from check_nes_head637 import head_fixture
from test_nes_tile532_edges import width
from test_nes_map526_priority import map_fixture
from test_nes_idle524_priority import case
from nes_raw506 import once,sha


def attempt(a, name, line, h, fault='late_stop'):
    dest=a.out/name
    dest.mkdir()
    sub=SimpleNamespace(out=dest,client=a.client,mesen=a.mesen,trace=a.trace)
    image=(a.client/'body.bin').read_bytes()
    labels=json.loads((a.client/'labels.json').read_bytes())
    prefix=labels['prefix523']
    entry=bytes([0x20])+(prefix&65535).to_bytes(2,'little')
    assert image.count(entry)==1
    site=0x2000+image.index(entry)
    scratch=0x3900
    assert 0x2000+len(image)<scratch<0x4000-3
    def inject(script,symbols):
        script=head_fixture(width(map_fixture(script,symbols),1152))
        script=once(script,'and mapTail() then','and mapTail() and word(0x4004+word(0x1252))>=1152 then')
        # Only the calling JSR operand temporarily points at this test wait loop.
        # JMP changes no registers or flags. At production entry the original
        # caller, all code bytes and the scratch bytes are restored and checked.
        folder=dest/f'906-{fault}'
        (folder/'original-body.bin').write_bytes(image)
        script=once(script,'local function loaded()',f"""
local saved=nil;local entering=false;local original=file('original-body.bin')
local ram=emu.memType.snesWorkRam
local function put(addr,v) emu.write(addr,v,ram) end
local function redirect(addr,target) put(addr+1,target&255);put(addr+2,target>>8) end
local function stamp(tag)
 local st=emu.getState()
 local f=assert(io.open(ROOT..'/beam.tsv','a'))
 f:write(tag,' ',st.masterClock,' ',st['ppu.scanline'],' ',st['memoryManager.hClock'],' ',st.frameCount,'\\n');f:close()
end
emu.addMemoryCallback(function()
 local st=emu.getState()
 if st['ppu.scanline']=={line} and st['memoryManager.hClock']>={h} then
  redirect({site},{prefix&65535});redirect({scratch},{prefix&65535});entering=true
 end
end,emu.callbackType.exec,{0x7e0000+scratch})
emu.addMemoryCallback(function()
 if entering then
  for j=0,2 do put({scratch}+j,saved[j+1]) end
  entering=false
  for j=1,#original do assert(rd(0x1fff+j)==original:byte(j),'WRAM program mismatch')end
  stamp('entry')
 end
end,emu.callbackType.exec,{prefix})
emu.addMemoryCallback(function()if held and index==held and not armed then stamp('latch') end end,emu.callbackType.read,0x2137)
emu.addMemoryCallback(function()if targetedGrant and index==held then stamp('mdma') end end,emu.callbackType.write,0x420b)
local function loaded()""")
        script=once(script,'held=index;initial=word(0x1252);',f"""assert(rd({site})==0x20 and word({site}+1)=={prefix&65535})
  saved={{rd({scratch}),rd({scratch}+1),rd({scratch}+2)}}
  put({scratch},0x4c);redirect({scratch},{scratch});redirect({site},{scratch})
  held=index;initial=word(0x1252);""")
        script=once(script,'mid=true;released=true;firstClock=tick();',"stamp('first');mid=true;released=true;firstClock=tick();")
        return once(script,'lastWrite=true;lastClock=tick();',"stamp('last');lastWrite=true;lastClock=tick();")
    result=case(sub,906,fault,edit_fixture=inject)
    stamps={}
    for row in (dest/f'906-{fault}'/'beam.tsv').read_text().splitlines():
        event,clock,scan,hpos,frame=row.split()
        stamps.setdefault(event,[]).append(dict(clock=int(clock),line=int(scan),h=int(hpos),frame=int(frame)))
    beam={k:items[0] for k,items in stamps.items()}
    assert len(stamps['entry'])==1 and beam['entry']['clock']<=beam['latch']['clock']
    if fault=='late_stop':
        assert all(len(stamps[k])==1 for k in ('mdma','first','last'))
        assert result['size']==1152 and result['next_head_ACK']==0
        assert beam['mdma']['clock']<beam['first']['clock']==result['first_write']<result['last_write']==beam['last']['clock']<result['quiet']
        assert 225<=beam['mdma']['line']<=beam['last']['line']<262
        assert beam['entry']['frame']==beam['last']['frame']
    return dict(beam=beam, race=result)


def main(a):
    a.out.mkdir(parents=True,exist_ok=False)
    cal=attempt(a,'calibration',251,200)
    b=cal['beam']
    rows={}
    for event in ('mdma','latch'):
        # Aim inside the late range; each real scanline is 1364 clocks here.
        offset=b[event]['clock']-b['entry']['clock']
        line,h=divmod(252*1364+1120-offset,1364)
        result=attempt(a,event,line,h)
        for key in (('mdma','first') if event=='mdma' else ('latch',)):
            e=result['beam'][key]
            assert e['line']==252 and 1000<e['h']<1364,(event,key,e)
        rows[event]=result
    for fault in ('both','head'):
        r=attempt(a,fault,line,h,fault)
        assert r['race']['size']==0 and 'mdma' not in r['beam']
        rows[fault]=r
    report=dict(client=sha(a.client/'sink165.sfc'),body=sha(a.client/'body.bin'),calibration=cal,cases=rows,
                scope='Test-only caller phase alignment; original complete WRAM program verified on entry. Real beam, MDMA and VRAM writes.')
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('client','mesen','trace','out'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
