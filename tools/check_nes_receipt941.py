"""Fault the final 906 OBJ admission, last read and the 912 VBlank grant."""
import argparse
import json
from unittest.mock import patch

import analyze_nes_obj923
import check_nes_chain935
import nes_obj923
import nes_return920
from analyze_nes_palette921 import directory
from guard_nes_output852 import run
from nes_raw506 import once
from nes_receipt941 import ARM, image


def packet(b,g):
    return g==906 and b[:2]==bytes((7,1)) and int.from_bytes(b[16:20],'little')==6


def faults(temp,mode):
    target=image(mode)
    trial=directory(temp,1,'941'+mode,'warm')
    data={}
    for bit in (0,15,17,None):
        stop=bit is None
        name='last-byte' if stop else f'duplicate-{bit}'
        def adapt(lua,labels):
            if stop:
                lua=once(lua,'if not injected852 then','if false and not injected852 then')
                lua=once(lua,'local i=a-0x400800;',"""local i=a-0x400800;
 if packet and pw(8)==906 and pw(16)==6 and i==575 then injected852=true;stop852=true end;""")
            else:
                addr=0x1300+bit//8
                hook=f"""local injected852=false
checkedMem527(function()
 if packet and pw(8)==906 and pb(0)==7 and pw(16)==6 then
  injected852=true;emu.write({addr},rd({addr})|{1<<(bit%8)},emu.memType.snesWorkRam)
 end
end,emu.callbackType.exec,{labels['bulk194']})
"""
                lua=once(lua,'local function loaded()',hook+'local function loaded()')
            expected='lastStatus==228 and reads==576' if stop else 'lastStatus==224 and reads==0'
            old="if pb(0)==7 then assert(lastStatus==0 and reads==#tile,'early bulk ACK')end"
            lua=once(lua,old,f'if injected852 then assert({expected}) else {old} end')
            lua=once(lua,'consumed[#consumed+1]=',"assert(not injected852,'invalid OBJ returned');consumed[#consumed+1]=")
            return once(lua,'  assert(captured==commits)','  assert(injected852);assert(captured==commits)')
        attempt=1
        while (trial/f'guard-941-{name}-{attempt}').exists():attempt+=1
        data[name]=run(temp,trial,'stop' if stop else 'duplicate',column_client=target,
                       select_packet=packet,adapt_lua=adapt,output_name=f'941-{name}-{attempt}')
    (target/'faults941.json').write_text(json.dumps(data)+'\n')


def guards(temp,mode):
    target=image(mode)
    tag='941'+mode
    with patch.object(nes_return920,'client',lambda _:target),patch.object(nes_obj923,'client',lambda _:target):
        nes_return920.guards(temp,'first',tag=tag,destination=target/'final-guards.json')
        nes_obj923.obj_stops(temp,'first',tag=tag,destination=target/'final-stops.json')
    with patch.object(analyze_nes_obj923,'client',lambda _:target):
        result=analyze_nes_obj923.recovery('final',target,trial=ARM)
    (target/'recovery941.json').write_text(json.dumps(result)+'\n')


if __name__=='__main__':
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('faults','guards','edges'))
    p.add_argument('temp',type=Path)
    p.add_argument('mode')
    a=p.parse_args()
    if a.action=='edges':
        # Call for candidates which grant the 32B tail in both cold schedules.
        with patch.object(check_nes_chain935,'output',lambda _:image(a.mode)):
            for ph in (1,2):
                for case in ('head','stop'):
                    check_nes_chain935.run(a.temp,'bounded',ph,case,tag='941'+a.mode)
    else:
        (faults if a.action=='faults' else guards)(a.temp,a.mode)
