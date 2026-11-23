"""Compare linked packet decoders on aligned, unaligned, end-of-page and truncated blocks."""
import json
import sys
from pathlib import Path
from check_nes_game478 import Machine
from check_nes_sram897 import TRACE
from nes_head939 import work as base
from nes_input940 import work
from nes_raw506 import sha


def check(mode):
    arm=work(mode)
    old,new=[Machine(p/'link/src',bytes(128)) for p in (base('tile'),arm)]
    size=old.layout['nes_native165']['size']
    assert old.layout['nes_native165']==new.layout['nes_native165']
    for m in (old,new):
        m.u.mem_map(0x21000000,4096)
    blocks=[]
    for tx,rx in json.loads(TRACE.read_bytes())['transactions']:
        if bytes.fromhex(tx)[0]==0xd3:break
        if bytes.fromhex(tx)[0]==0xd1:blocks.append(bytes.fromhex(rx)[1:-2])
    normal=truncated=0
    for align in range(5):
        for m in (old,new):
            m.call('nes_native165_reset',[m.state])
        for token,block in enumerate(blocks):
            ptr=0x21000000+align if align<4 else 0x21001000-len(block)
            before=bytes(old.u.mem_read(old.state,size))
            for m in (old,new):m.u.mem_write(ptr,block)
            for length in (len(block)-1,len(block)):
                result=[]
                for m in (old,new):
                    m.u.mem_write(m.state,before)
                    ok=m.call('nes_native165_packet',[m.state,token,ptr,length])
                    result.append((ok,bytes(m.u.mem_read(m.state,size))))
                assert result[0]==result[1],(align,token,length)
                if length==len(block):
                    assert result[0][0]==1
                    normal+=1
                else:
                    assert not result[0][0]
                    truncated+=1
        assert old.state_value()==new.state_value()==2
    report=dict(firmware=sha(arm/'link/src/obj-nes-100/firmware.stm'),source=sha(TRACE),
                valid=normal,truncated=truncated,geometry_state_bytes=size)
    (arm/'decode940.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report)


if __name__=='__main__':check(sys.argv[1])
