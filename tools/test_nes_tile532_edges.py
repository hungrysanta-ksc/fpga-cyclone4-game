# SPDX-License-Identifier: MIT
"""Exercise map-pair and interior variants at real beam edges with the production client image."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once
from test_nes_idle524_priority import case
from test_nes_map526_priority import map_fixture,rejected_edge


def width(s,limit=128):
    s=once(s,'for i=0,63 do',f'for i=0,math.min(length,{limit})-1 do')
    for old,new in [('offset+64)', 'offset+math.min(length,128))'),('if length>64 then','if length>128 then'),
                    ('==source+64','==source+128'),('==dest+64','==dest+128'),('==length-64','==length-128'),
                    ('assert(issuedSize==64)','assert(issuedSize==math.min(length,128))'),
                    ('issuedSize==0 or issuedSize==64','issuedSize==0 or issuedSize==math.min(length,128)')]:
        s=once(s,old,new.replace('128',str(limit)))
    return s


def gate(s,l,line,kind,read_pc,limit=128):
    # Hold the empty poll's VBlank flag LOW until the first half of the
    # requested real line. Never fabricate a VBlank or a latched coordinate.
    if line==254:
        s=width(map_fixture(s,l),limit)
        s=once(s,'and mapTail() then',f'and mapTail() and word(0x4004+word(0x1250)-8)>={limit} then')
    else:
        s=rejected_edge(s,l,tile=kind=='tile')
        if kind=='map':s=width(s,limit)
        s=once(s,'if held and index==held and not armed then\n  local line=',
               'if held and index==held and not armed and tried532 then\n  local line=')
        # The interior variant can reject a high beam bit at its near return.
        if 'no_beam532' in l and line in (233,256):
            pc=l['skip_scan532' if line==233 else 'no_beam532']
            s=once(s,f"exec,{l['defer_beam']})",f"exec,{pc})")
    s=once(s,'local held,initial,owner','local tried532,first532=false,false\nlocal held,initial,owner')
    s=once(s,'local pacedLine=@PACED@',f'local pacedLine={line}')
    return once(s,'local function loaded()',f"""emu.addMemoryCallback(function()first532=true end,emu.callbackType.exec,{read_pc})
emu.addMemoryCallback(function()first532=false end,emu.callbackType.exec,{read_pc+3})
emu.addMemoryCallback(function(a,v)
 if not first532 or not held or index~=held or armed or packet then return end
 local st=emu.getState()
 local h=st['memoryManager.hClock'] or st['ppu.hClock']
 if not h then for k,t in pairs(st) do if k:lower():match('%.hclock$') then h=t;break end end end
 tried532=false
 if st['ppu.scanline']~={line} or assert(h)>640 then return v&127 end
 tried532=true
 local f=assert(io.open(ROOT..'/beam-attempt.txt','w'));f:write(st['ppu.scanline'],',',h,',',v);f:close()
end,emu.callbackType.read,0x4212)
local function loaded()""")


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('trace','client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    labels=json.loads((a.client/'labels.json').read_text())
    limit=json.loads((a.client/'build.json').read_text())['map_chunk_B']
    assert limit in (128,256)
    body=(a.client/'body.bin').read_bytes()
    read_pc=0x7e2000+body.index(bytes.fromhex('ad1242'),labels['prefix523']-0x7e2000)
    rows=[]
    for line,kind in ((254,'map'),(255,'map'),(256,'map'),(233,'tile')):
        sub=argparse.Namespace(**vars(a));sub.out=a.out/f'line{line}';sub.out.mkdir()
        name='late_stop' if line==254 else 'stop'
        r=case(sub,906,name,edit_fixture=lambda s,l:gate(s,l,line,kind,read_pc,limit))
        assert r['size']==(limit if line==254 else 0)
        if r['grant']:assert line<=r['start_line']<=line+2
        rows.append(dict(line=line,kind=kind,**r))
    (a.out/'edges.json').write_text(json.dumps(rows,indent=2)+'\n')
