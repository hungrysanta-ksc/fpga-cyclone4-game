# SPDX-License-Identifier: MIT
"""Exercise a linked M4 with the complete 744 WRAM body and live consumer feedback."""
import argparse
import json
import runpy
import subprocess
from pathlib import Path
from unittest.mock import patch
from build_nes_bitmap743 import assemble, codec
from nes_raw506 import once
from replay_nes_beam741 import replacements
from replay_nes_chain744 import code


def image(client):
    original=(client/'body.bin').read_bytes()
    labels=json.loads((client/'labels.json').read_text())
    body=bytearray(original)
    for address,data in sorted(replacements(client,'budget').items()):
        at=address-codec.DEST
        assert at<=len(body)
        body[at:at+len(data)]=data
    body=bytearray(assemble(bytes(body),labels)[0])
    target=codec.DEST+len(body)
    site=(labels['whole526']&65535)+10-codec.DEST
    assert body[site:site+3]==bytes.fromhex('8d5212')
    body[site:site+3]=bytes([0x4c])+target.to_bytes(2,'little')
    body.extend(code(labels,target))
    assert len(body)==6362 and codec.DEST+len(body)<0x4000
    return original,body,target,labels


def instrument(script,client):
    original,body,target,labels=image(client)
    # Only the image loader is substituted. All scheduling, descriptor selection and
    # receipt code below executes on the 65816; no packet timestamps are replaced.
    diff={i:b for i,b in enumerate(body) if i>=len(original) or original[i]!=b}
    checks=','.join('{%d,%d}'%(i+codec.DEST,b) for i,b in diff.items())
    hook=f"""local installed745=false
checkedMem527(function()
 if not installed745 then
  for _,p in ipairs({{{checks}}}) do emu.write(p[1],p[2],emu.memType.snesWorkRam) end
  installed745=true
 end
end,emu.callbackType.exec,0x7e2000)
local beam745=assert(io.open(ROOT..'/dma745.csv','w'))
beam745:write('g,clock,line,h,src,n,head,endp,nextsrc,nextbytes\\n')
checkedMem527(function(_,v)
 if v~=1 then return end
 local g=word(0x1226)
 if g<951 or g>957 or not regs[0x4305] then return end
 local head=word(0x1252);local tail=word(0x1250);local st=emu.getState()
 beam745:write(string.format('%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\\n',g,st.masterClock,st['ppu.scanline'],st['memoryManager.hClock'],
  regs[0x4302]+256*regs[0x4303],regs[0x4305]+256*regs[0x4306],head,tail,
  head+8<tail and word(0x4000+head+8) or -1,head+8<tail and word(0x4004+head+8) or -1));beam745:flush()
end,emu.callbackType.write,0x420b)
"""
    s=once(script,'local function loaded()',hook+'local function loaded()')
    s=once(s,'(i<tail or n<=160)','(i<tail or n<=288)')
    s=once(s,'n==word(0x4004+i) and n<=2048',
           '(n==word(0x4004+i) or (n==64 and word(0x4004+i)>64 and (src&0x7000)==0x4000)) and n<=2048')
    s=once(s,'beam685.line<=248 and length<=1536',
           '(beam685.line<=249 or (beam685.line==250 and beam685.h<512)) and length<=1536')
    s=once(s,'checkedMem527(verify526(function()\n if tile532 then','local function retire745()\n if tile532 then')
    addr=labels['retired526']
    return once(s,f'end),emu.callbackType.exec,{addr})',f'end\ncheckedMem527(verify526(retire745),emu.callbackType.exec,{addr})\ncheckedMem527(verify526(retire745),emu.callbackType.exec,{0x7e0000+target+3})')


def run():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--client',type=Path,required=True)
    a,_=parser.parse_known_args()
    popen=subprocess.Popen.__init__
    def launch(proc,args,*pos,**kw):
        if isinstance(args,(list,tuple)) and '--testRunner' in args:
            path=Path(args[args.index('--testRunner')+1])
            if path.name=='capture.lua':
                path.write_text(instrument(path.read_text(encoding='utf8'),a.client),encoding='utf8',newline='\n')
        popen(proc,args,*pos,**kw)
    with patch.object(subprocess.Popen,'__init__',launch):
        runpy.run_module('test_nes_observer717',run_name='__main__')


if __name__=='__main__':run()
