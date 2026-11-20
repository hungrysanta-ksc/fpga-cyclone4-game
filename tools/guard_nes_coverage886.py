"""Corrupt one required WRAM receipt in each lane of the six-word 65816 loop."""
import argparse
import json
from pathlib import Path
from check_nes_strip869 import guards
from guard_nes_output852 import run
from nes_coverage886 import WORK
from nes_raw506 import once


def verify(temp):
    tag='886-static'
    trial=temp/f'nes-tile821-demo-jointmirror-p1-{tag}'
    results=guards(temp,WORK,tag)
    faults={}
    for i in (0,13,26,39,52,71):
        gen=906+i%2
        bit=1<<(15 if i%2 else 0)
        def edit(packet,g,case):
            if g==gen:
                n=40+2*i
                assert len(packet)==184
                packet[n:n+2]=(int.from_bytes(packet[n:n+2],'little')|bit).to_bytes(2,'little')
            return packet,g==gen
        def inject(lua,labels):
            hook=f"""
local hit886=false
checkedMem527(function()
 if packet and pw(8)=={gen} and pb(0)==3 then
  local a=0x1320+word(0x1254)+{2*i+(bit>255)}
  emu.write(a,rd(a)&(255~{128 if bit>255 else 1}),emu.memType.snesWorkRam)
 end
end,emu.callbackType.exec,{labels['coverage212']})
checkedMem527(function()
 assert(packet and pw(8)=={gen} and not hit886)
 hit886=true
 local f=assert(io.open(ROOT..'/rejected886.txt','w'))
 f:write(tostring(word(0x1254)));f:close()
end,emu.callbackType.exec,{labels['missing619']})
"""
            return once(lua,'local function loaded()',hook+'local function loaded()')
        case=f'missing886-{i}'
        row=run(temp,trial,case,column_client=WORK/'client02',edit_seal=edit,adapt_lua=inject)
        row.update(word=i,bit=bit,bank_offset=int((trial/f'guard-{case}'/'rejected886.txt').read_text()))
        faults[case]=row
    assert len({r['bank_offset'] for r in faults.values()})==2
    results['missing_receipts']=faults
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    args=p.parse_args()
    (WORK/'guards.json').write_text(json.dumps(verify(args.temp),indent=2)+'\n')
