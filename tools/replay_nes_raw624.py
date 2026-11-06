# SPDX-License-Identifier: MIT
"""Compare the 619 and 624 consumers at identical 905..922 PUSH times."""
import argparse
import json
from functools import partial
from pathlib import Path
from unittest.mock import patch

import observe_nes_repeat545
from replay_nes_quiet608 import focus, frontier, replay
from test_nes_quiet608 import observe
from nes_raw506 import once


def checkpoints(rows):
    seal = [r for r in rows if r['g']=='922' and r['op']=='3']
    return {event:{k:int(row[k]) for k in ('clock','frame','line')}
            for row in seal for event in [row['event']]
            if event in ('load','validate181','final212','reveal','ack')}


def isolate(args):
    """Install the measured hot path at 922 dispatch, preserving the original prefix."""
    old=json.loads((args.client/'labels.json').read_text())
    new=json.loads((args.later/'labels.json').read_text())
    body=(args.later/'body.bin').read_bytes()
    def extract(first,last):
        return body[new[first]-0x7e2000:new[last]-0x7e2000]
    def addr(value):
        return (value&65535).to_bytes(2,'little')
    entry=extract('raw_dma489','generic624')
    code=extract('pairs624','raw_boot489')
    target=0x3500
    assert len((args.client/'body.bin').read_bytes())+0x2000<target
    assert entry==bytes.fromhex('a478c01500d0034c')+addr(new['pairs624'])
    entry=entry[:-2]+addr(target)
    for label,opcode,count in [('service',0x20,3),('raw_stop489',0x4c,2),('raw_return489',0x4c,1)]:
        old_operand=bytes([opcode])+addr(new[label])
        assert code.count(old_operand)==count
        code=code.replace(old_operand,bytes([opcode])+addr(old[label]))
    # The relaxed third STOP edge is relative. Supply its trampoline outside
    # the normal path, before the fixed program's header/vector reservation.
    stop_offset=new['raw_stop489']-new['pairs624']
    assert len(code)<stop_offset and target+stop_offset+3<0x2000+6144-160
    def write(where,data):
        return '\n'.join(f'emu.write({where+i},{v},emu.memType.snesWorkRam)' for i,v in enumerate(data))
    def instrument(source):
        arrivals=args.out/'arrivals.tsv'
        lines=arrivals.read_text().splitlines()
        assert lines[-1].split('\t')[1]=='FINISH'
        # Total packet count is known once the last SEAL is delivered, even
        # when the new consumer displays before the old finish marker.
        lines[-1]=str(int(lines[-2].split('\t')[0])+1)+'\tFINISH\t'
        arrivals.write_text('\n'.join(lines)+'\n',newline='\n')
        hook=f"""local switched624=false
emu.addMemoryCallback(function()
 if not switched624 and packet and pw(8)==922 then
  assert(word(0x78)==21 and word(0x1240)==2 and word(0x125c)==1)
  {write(target,code)}
  {write(target+stop_offset,bytes([0x4c])+addr(old['raw_stop489']))}
  {write(old['raw_dma489']&65535,entry)}
  switched624=true
  local f=assert(io.open(ROOT..'/switch.txt','w'));f:write(emu.getState().masterClock);f:close()
 end
end,emu.callbackType.exec,{old['raw_dispatch489']})
"""
        source=once(source,'local function loaded()',hook+'local function loaded()')
        # The generic 547 observer sees loop PCs; the unrolled path instead
        # proves each issue from actual DMA channel registers at MDMAEN.
        anchor='if a==0x420b and v==1 and regs[0x4301]==0x18 then vramDMA='
        return once(source,anchor,"""if switched624 and active547 and a==0x420b and v==1 and regs[0x4301]==0x18 then
   local row=active547.row+2
   local pair=(row-1)//2
   local src=regs[0x4302]+256*regs[0x4303]
   local dst=regs[0x2116]+256*regs[0x2117]
   assert(src==word(0x1020)+0x6961+64*row and regs[0x4304]==0x7f)
   assert(dst==(active547.bank==0 and 0x2800 or 0x4800)+1+8*pair)
   assert(regs[0x4305]==64 and regs[0x4306]==0)
   active547.row=row;write547()
  end
  """+anchor)
    def compare(before,after):
        cutoff=int((args.out/'switch.txt').read_text())
        prefix=lambda rows:[r for r in rows if int(r['clock'])<=cutoff]
        assert prefix(before)==prefix(after)
        return dict(reference=checkpoints(before),candidate=checkpoints(after),matched_prefix=len(prefix(before)),switch=cutoff)
    return instrument,compare


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','client','later','mesen','out'):
        p.add_argument('--'+key,type=Path,required=True)
    args=p.parse_args()
    args.frames=18
    with patch.object(frontier,'tile_observer',partial(frontier.tile_observer,map_limit='1152')), \
         patch.object(replay,'observer',partial(focus,generation=922)), \
         patch.object(observe_nes_repeat545,'observe',observe):
        edit,compare=isolate(args)
        replay.run(args,edit_script=edit,compare_trace=compare)
