"""Measure the 959 OBJ reader with every packet arrival fixed to the original phase."""
import argparse
import json
from pathlib import Path
from analyze_nes_map830 import window
from nes_bulk889 import BASE
from nes_raw506 import once
from replay_nes_bulk889 import packet_override
from test_nes_word873_idle import run_consumer


def run(temp,phase,local):
    src=temp/f'nes-tile821-demo-jointmirror-p{phase}-888-word'
    out=temp/f'nes-bulk889-tile-p{phase}-{int(local)}'
    out.mkdir()
    ops=[]
    for line in (src/'packets.jsonl').read_text().splitlines():
        _,clock,h,bulk=json.loads(line)
        b=bytes.fromhex(h)
        ops.append((clock,'PUSH',h,bulk))
        if b[0]==3 and int.from_bytes(b[8:10],'little')==959:
            break
    labels=json.loads((BASE/'client02/labels.json').read_bytes())
    def attach(lua):
        if local:
            lua=packet_override(lua)
        code="local times889=assert(io.open(ROOT..'/reader.csv','w'))\n"
        for k in ('bulk194','data'):
            code+=f"""
checkedMem527(function()
 if packet and pw(8)==959 and pb(0)==7 and pb(1)==1 and pw(10)==416 then
  times889:write('{k},'..emu.getState().masterClock..'\\n');times889:flush()
 end
end,emu.callbackType.exec,{labels[k]})
"""
        return once(lua,'local function loaded()',code+'local function loaded()')
    run_consumer(temp,src,out,ops,55,attach)
    if not local:
        original=[r for r in window(src) if r['g']<=959]
        assert window(out)==original


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int)
    p.add_argument('--local',action='store_true')
    run(**vars(p.parse_args()))
