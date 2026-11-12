# SPDX-License-Identifier: MIT
"""Isolate nine-slot admission on the original 727 and separately priced 742 arrivals."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
import replay_nes_map527 as runner
import trace_nes_owner739 as owner
import replay_nes_beam741 as beam
from build_nes_bitmap743 import assemble, codec
from nes_raw506 import once
from replay_nes_receipt742 import observe_bulk, retime


def run(a):
    def observe(script):
        script=observe_bulk(script,a.client)
        if a.save_quiet:
            script=once(script,'then quiet739=true end',"""then
 if not quiet739 then
  local f=assert(io.open(ROOT..'/aborted-banks.bin','wb'))
  for i=0x1280,0x144f do f:write(string.char(rd(i))) end
  for i=0x14d0,0x14d7 do f:write(string.char(rd(i))) end
  f:close()
 end
 quiet739=true end""")
        if a.restore_quiet:
            snapshot=a.restore_quiet.read_bytes()
            assert len(snapshot)==472 and any(snapshot[:464])
            hook=f"""local saved743={{{','.join(map(str,snapshot))}}}
checkedMem527(function()
 for i,v in ipairs(saved743) do
  local a=i<=464 and 0x1280+i-1 or 0x14d0+i-465
  emu.write(a,v,emu.memType.snesWorkRam)
 end
end,emu.callbackType.exec,0x7e2000)
"""
            script=once(script,'local function loaded()',hook+'local function loaded()')
        if a.baseline:
            return script
        # Inject only on the last OBJ: the boot and all earlier sends, CPU
        # events and pixels stay identical to the calendar's unmodified control.
        labels=json.loads((a.client/'labels.json').read_text())
        original=(a.client/'body.bin').read_bytes()
        cave=0x3a00
        body,_=assemble(original,labels,entry=cave)
        hook=labels['obj_unit212'] & 65535
        sites={hook:body[hook-codec.DEST:hook-codec.DEST+3],cave:body[len(original):]}
        install='\n'.join(f" for i,v in ipairs({{{','.join(map(str,b))}}}) do emu.write({at}+i-1,v,emu.memType.snesWorkRam) end"
                          for at,b in sites.items())
        return once(script,'if pb(0)==7 then tile=tilePayload[index]else tile=nil end',
                    'if pw(8)==957 and pb(0)==7 and pb(1)==1 and pw(10)==2720 and pw(14)==288 then\n'+install+
                    '\n end\n if pb(0)==7 then tile=tilePayload[index]else tile=nil end')
    if a.calendar=='early':
        a.calendar='first'
        a.variant='budget'
        a.feedback=None
        a.lag_nops=0
        beam.run(a,observe_script=observe,adjust_arrivals=lambda folder,base,plan:
                 retime(folder,base,plan,'poll',a.scroll,pulse_folder=a.pulse_folder))
        return
    real=runner.run
    def replay(args, *, edit_script):
        def compare(before,after):
            assert [r for r in before if int(r['g'])<957]==[r for r in after if int(r['g'])<957]
            def ids(rows):
                return [(r['g'],r['index'],r['event'],r['op'],r['section'],r['value']) for r in rows
                        if r['event'] in ('load','ack','reveal')]
            assert ids(before)==ids(after)
            if a.baseline:
                assert before==after
            return {'prefix_events':sum(int(r['g'])<957 for r in before)}
        real(args,edit_script=lambda s:observe(edit_script(s)),compare_trace=compare)
    with patch.object(runner,'run',replay):
        owner.run(a)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('client','trace','out','mesen'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--calendar',choices=('727','early'),default='727')
    p.add_argument('--scroll',choices=('original','first'),default='original')
    p.add_argument('--pulse-folder',type=Path)
    p.add_argument('--phase',choices=(1,2),type=int,required=True)
    p.add_argument('--inject',choices=('none','head','before_bg','during_obj'),default='none')
    p.add_argument('--save-quiet',action='store_true')
    p.add_argument('--restore-quiet',type=Path)
    p.add_argument('--baseline',action='store_true')
    p.add_argument('--mode',choices=('trace','stop','stale'),default='trace')
    run(p.parse_args())
