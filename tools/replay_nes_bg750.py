# SPDX-License-Identifier: MIT
"""Replay fixed 749 page offers on the 694 receiver. Only switch the measured routine after E8."""
import json
import argparse
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
import trace_nes_owner739 as owner
from build_nes_trace_replay import Code
from nes_raw506 import once
from replay_nes_beam741 import replacements
from replay_nes_chain744 import code as continue_obj


def edits(client, variant):
    if variant == 'control':
        return {}
    if variant == 'bg':
        return replacements(client,'direct')
    if variant=='tail':
        out=edits(client,'compact')
        labels=json.loads((client/'labels.json').read_text())
        site,entry=next((at,code) for at,code in out.items() if code.startswith(bytes.fromhex('f0034c')))
        original=entry[-3:]
        base=max(at+len(data) for at,data in out.items())
        c=Code(0x7e0000+base)
        c.labels.update(labels)
        # The continuation already serviced STOP and sampled the new packet bit.
        # A just-finished 48B tile may expose a map tail behind the OBJ.
        c.emit(0xc0,48,0);c.branch(0xd0,'normal750')
        c.absolute(0xae,0x1252);c.absolute(0xec,0x1250);c.branch(0xf0,'normal750')
        c.jump('tail532')
        c.label('normal750');c.emit(*original)
        out[site]=entry[:-3]+bytes([0x4c])+base.to_bytes(2,'little')
        out[base]=c.finish()
        return out
    if variant=='compact':
        out=replacements(client,'direct')
        labels=json.loads((client/'labels.json').read_text())
        body=(client/'body.bin').read_bytes()
        normal=labels['no_event680']&65535
        site=normal-9
        assert body[site-8192:normal-8192]==bytes.fromhex('e220a9a58d1d60c220')
        base=max(at+len(data) for at,data in out.items())
        c=Code(0x7e0000+base)
        c.labels.update(labels)
        # This branch is reached only after a synchronous map DMA retirement.
        # Publish its progress exactly once, including on every slow path.
        c.emit(*body[site-8192:normal-8192])
        c.emit(0xc0,0,6);c.branch(0xd0,'slow750')
        c.absolute(0xae,0x1252);c.absolute(0xec,0x1250);c.branch(0xb0,'slow750')
        c.long(0xbf,0x7e4000);c.emit(0xa8,0x29,0,0x70,0xc9,0,0x40)
        c.branch(0xd0,'slow750')
        c.long(0xbf,0x7e4004);c.emit(0xc9,0x20,1);c.branch(0xd0,'slow750')
        c.absolute(0x8d,0x4305);c.absolute(0x8c,0x4302);c.emit(0xa8)
        c.long(0xbf,0x7e4002);c.emit(0x4a);c.absolute(0x8d,0x2116)
        # Channel mode/bank and VMAIN still belong to the preceding map.
        # Preserve the latch acknowledgement and both bytes of the beam.
        c.emit(0xe2,0x20)
        for _ in range(2):c.absolute(0xad,0x213f)
        c.emit(0x89,0x40);c.branch(0xd0,'skip750')
        c.absolute(0xad,0x2137);c.absolute(0xad,0x213f)
        c.emit(0x89,0x40);c.branch(0xf0,'skip750')
        c.absolute(0xad,0x213d);c.emit(0xeb);c.absolute(0xad,0x213d)
        c.emit(0x29,1,0xeb,0xc2,0x20,0x38,0xe9,225,0,0xc9,33,0,0xe2,0x20)
        c.branch(0xb0,'skip750')
        c.absolute(0xad,0x4212);c.branch(0x10,'skip750')
        c.absolute(0x9c,0x1238);c.absolute(0xad,0x1236);c.branch(0xd0,'skip750')
        c.jump('priority524')  # live STOP and new-head tests before MDMAEN
        c.label('skip750');c.emit(0xc2,0x20)
        c.label('slow750');c.jump('no_event680')
        out[base]=c.finish()
        out[site]=bytes([0x4c])+base.to_bytes(2,'little')
        return out
    if variant=='chain':
        out=replacements(client,'direct')
        labels=json.loads((client/'labels.json').read_text())
        original=(client/'body.bin').read_bytes()
        retire=labels['retired526']&65535
        dispatch=original[retire-8192:retire-8192+3]
        assert dispatch[0]==0x4c
        labels['retired526']=0x7e0000+int.from_bytes(dispatch[1:],'little')
        base=max(at+len(data) for at,data in out.items())
        # Head or tail retirement has already updated the list. The shared
        # post-DMA boundary still owns Y (actual length) and the saved kind.
        block=continue_obj(labels,base-3)[3:]
        assert block.count(bytes.fromhex('a04000'))==1
        out[base]=block.replace(bytes.fromhex('a04000'),bytes.fromhex('a02001'))
        out[retire]=b'\x4c'+base.to_bytes(2,'little')
        return out
    # Allow a complete, accepted OBJ of up to 288 B in the extended beam window.
    # Keep the 16-bit size check and the existing live STOP and packet arbitration.
    out=replacements(client,'fragment')
    site,code=max(out.items())
    cap=bytes.fromhex('c041009003a04000')
    assert code.count(cap)==1
    out[site]=code.replace(cap,bytes.fromhex('c021019003a02001'))
    return out


def install_hook(script, client, variant):
    changes=edits(client,variant)
    install='\n'.join(f" for i,v in ipairs({{{','.join(map(str,code))}}}) do emu.write({site}+i-1,v,emu.memType.snesWorkRam) end"
                      for site,code in changes.items())
    if ' if pw(8)==957 and pb(0)==7 and pb(1)==1 and pw(14)==288 then' in script:
        # A live-schedule capture already contains the executed receiver.
        assert install and install in script and variant=='tail'
        return script
    anchor=' if pb(0)==7 then tile=tilePayload'
    script=once(script,anchor,' if pw(8)==957 and pb(0)==7 and pb(1)==1 and pw(14)==288 then\n'+install+'\n end\n'+anchor)
    if variant in ('full','chain','compact','tail'):
        script=once(script,'(i<tail or n<=160)','(i<tail or n<=160 or (word(0x1226)==957 and src==19104 and n==288))')
    return script


def run(args):
    def hook(script):
        script=install_hook(script,args.client,args.variant)
        if args.inject=='none':
            return script
        labels=json.loads((args.client/'labels.json').read_text())
        address=labels['priority524']
        event=f'emu.callbackType.exec,{address}'
        if args.inject=='during':
            event='emu.callbackType.write,0x2118'
        if args.inject=='head':
            assert args.mode=='trace'
            action="""rpc()
 if sent==retired then
  assert(b522~='FINISH' and target522>st.masterClock)
  target522=st.masterClock;rpc()
 end
 assert(sent>retired and not packet)
 f:write(' ',index,' ',requests[index]:byte(1),' ',requests[index]:byte(2))"""
        else:
            assert args.mode=='stop'
            script=once(script,'if pw(8)==957 and pb(0)==9 then stop739=true end','')
            action='stop739=true'
        watch=f"""local fired750=false
checkedMem527(function()
 if fired750 or word(0x1226)~=957 or packet or regs[0x4302]+256*regs[0x4303]~=19104 or
     regs[0x4305]+256*regs[0x4306]~=288 then return end
 fired750=true
 local st=emu.getState();local f=assert(io.open(ROOT..'/guard750.txt','w'))
 f:write(st.masterClock)
 {action}
 f:close()
end,{event})
"""
        return once(script,'local finished522=false',watch+'local finished522=false')
    fixed=replay.run
    def replay_fixed(a,*,edit_script):
        def compare(old,new):
            prefix=lambda rows:[r for r in rows if int(r['g'])<957]
            assert prefix(old)==prefix(new)
            if args.variant=='control':
                assert old==new
            return {'prefix_events':len(prefix(old))}
        return fixed(a,edit_script=lambda s:hook(edit_script(s)),compare_trace=compare)
    with patch.object(replay,'run',replay_fixed):
        owner.run(args)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trace','out','client','mesen'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--variant',choices=('control','bg','full','chain','compact','tail'),required=True)
    p.add_argument('--mode',choices=('trace','stop','stale'),default='trace')
    p.add_argument('--inject',choices=('none','head','before','during'),default='none')
    run(p.parse_args())
