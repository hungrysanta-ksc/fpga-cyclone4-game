"""Reject descriptor, transport and alignment errors before tile DMA in the final ROM."""
import argparse
import json
from pathlib import Path
from check_nes_strip869 import guards
from guard_nes_output852 import run
from nes_bulk889 import WORK
from nes_raw506 import once


def verify(temp,tag='889-reader'):
    trial=temp/f'nes-tile821-demo-jointmirror-p1-{tag}'
    results=guards(temp,WORK,tag,'client03')
    faults={}
    # A WRAM header or a separately read FPGA descriptor may be corrupt.
    # Matching invalid length/offset pairs reach the actual bound/alignment checks.
    cases=[('size',1,12,3,None),('section',1,1,2,None),
           ('zero',1,14,0,(2,0)),('large',1,14,2080,(2,2080)),
           ('obj_align',1,10,16,(4,16)),('bg_align',0,10,8,(4,8))]
    cases.extend((f'desc_{i}',1,None,None,(i,None)) for i in (0,2,4,6,8,10))
    for name,section,field,value,descriptor in cases:
        def adapt(lua,labels):
            write=''
            if field is not None:
                write=f'emu.write({0x1200+field},{value&255},emu.memType.snesWorkRam)'
                if field!=1:
                    write+=f';emu.write({0x1201+field},{value>>8},emu.memType.snesWorkRam)'
            hook=f"""
local hit889=false
checkedMem527(function()
 if packet and pw(8)==907 and pb(1)=={section} then hit889=true;{write} end
end,emu.callbackType.exec,{labels['bulk194']})
checkedMem527(function()
 if hit889 then error('invalid bulk reached DMA') end
end,emu.callbackType.exec,{labels['data']})
"""
            lua=once(lua,'local function loaded()',hook+'local function loaded()')
            success="if pb(0)==7 then assert(lastStatus==0 and reads==#tile,'early bulk ACK')end"
            lua=once(lua,success,"if hit889 then assert(lastStatus==224 and reads==0,'bulk reject') else "+success+" end")
            lua=once(lua,'  assert(captured==commits)','  assert(hit889);assert(captured==commits)')
            if descriptor:
                at,v=descriptor
                set_value=(f'd[{at+1}]=d[{at+1}]~1' if v is None else
                           f'd[{at+1}]={v&255};d[{at+2}]={v>>8}')
                needle='return d[a-0x6040+1]'
                lua=once(lua,needle,'if hit889 then '+set_value+' end;'+needle)
            return lua
        faults[name]=run(temp,trial,'bulk889-'+name,column_client=WORK/'client03',
                         select_packet=lambda b,g:g==907 and b[:2]==bytes([7,section]),adapt_lua=adapt)
    results['bad_tiles']=faults
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('--tag',default='889-reader')
    args=p.parse_args()
    (WORK/'guards.json').write_text(json.dumps(verify(args.temp,args.tag),indent=2)+'\n')
