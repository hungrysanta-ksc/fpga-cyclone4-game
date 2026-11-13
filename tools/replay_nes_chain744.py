# SPDX-License-Identifier: MIT
"""Execute a short OBJ continuation after a synchronous long map DMA."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_beam741 as beam
import replay_nes_bitmap743 as bitmap
from build_nes_trace_replay import Code
from nes_raw506 import once, sha


def code(labels, base=0x3b00):
    c = Code(0x7e0000 + base)
    c.labels.update(labels)
    # At the whole nonempty retirement, A holds the advancing head. X/Y
    # are 16 bit and the saved source kind is still on the stack.
    c.absolute(0x8d,0x1252)                 # replaced STA on nonempty whole retirement
    c.emit(0xc0,0,6)                         # CPY #1536
    c.branch(0xf0,'long744')
    c.jump('retired526')
    c.label('long744')
    c.emit(0x68,0xc9,0,0x50)                # PLA / CMP #map
    c.branch(0xf0,'map744')
    c.jump('no_event680')
    c.label('map744')
    c.emit(0xe2,0x20,0xa9,0xa5)
    c.absolute(0x8d,0x601d)                 # publish map-done before checking the queue
    c.emit(0xc2,0x20)
    # service clears the autojoy latch in blank and samples no pad there.
    # Keep its full path on deferral, and both STOP tests on a fast grant.
    c.absolute(0xae,0x1252)
    c.emit(0x8a,0x18,0x69,8,0)
    c.absolute(0xcd,0x1250)                 # the sole remaining accepted descriptor
    c.branch(0xd0,'slow744')
    c.long(0xbf,0x7e4000)
    c.emit(0xa8,0x29,0,0x70,0xc9,0,0x40)   # Y retains the complete OBJ source
    c.branch(0xd0,'slow744')
    c.long(0xbf,0x7e4004)
    c.emit(0xc9,0x20,1)                     # nine admitted 32-byte slots
    c.branch(0xf0,'obj744')
    c.label('slow744')
    c.jump('no_event680')                    # normal service and selector
    c.label('obj744')
    c.absolute(0x8c,0x4302)
    c.long(0xbf,0x7e4002)
    c.emit(0x4a)
    c.absolute(0x8d,0x2116)
    c.emit(0xa0,64,0)
    c.absolute(0x8c,0x4305)
    # Channel 0 mode/destination port, source bank and VMAIN were set by
    # this map. No packet handler or other channel-0 DMA can run in between.
    c.emit(0xe2,0x20)
    c.absolute(0xad,0x4212)
    c.branch(0x10,'skip744')
    for _ in range(2): c.absolute(0xad,0x213f)
    c.emit(0x89,0x40)
    c.branch(0xd0,'skip744')
    c.absolute(0xad,0x2137)
    c.absolute(0xad,0x213f)
    c.emit(0x89,0x40)
    c.branch(0xf0,'skip744')
    c.absolute(0xad,0x213d)
    c.emit(0xeb)
    c.absolute(0xad,0x213d)
    c.emit(0x29,1)
    c.branch(0xf0,'low744')
    c.emit(0xeb,0xc9,2)                     # lines 256 and 257
    c.branch(0x90,'blank744')
    c.branch(0x80,'skip744')
    c.label('low744')
    c.emit(0xeb,0xc9,225)
    c.branch(0x90,'skip744')
    c.label('blank744')
    c.absolute(0xad,0x4212)
    c.branch(0x10,'skip744')
    c.absolute(0x9c,0x1238)                 # service's blanking action, M=8
    c.absolute(0xad,0x1236)
    c.branch(0xd0,'skip744')
    c.jump('priority524')                    # live STOP, then new head, then MDMAEN
    c.label('skip744')
    c.emit(0xc2,0x20)
    c.jump('no_event680')
    return c.finish()


def run(a):
    labels=json.loads((a.client/'labels.json').read_text())
    extra=code(labels)
    original_edits=beam.replacements
    observer=bitmap.observe_bulk
    def install(script,client):
        script=observer(script,client)
        body=(client/'body.bin').read_bytes()
        assert sha(client/'body.bin')=='f7973584dbd091976de76808f1444c25c770da5005f3426bc22b69ac5700b74d'
        ptr=(labels['whole526']&65535)+10
        assert body[ptr-8192:ptr-8192+5]==bytes.fromhex('8d5212800e')
        # Bind the same independent post-DMA byte oracle to both retirement
        # points. The new dispatch has already stored the advancing head.
        marker="checkedMem527(verify526(function()\n if tile532 then"
        script=once(script,marker,"local function verifyRetirement744()\n if tile532 then")
        end=f"end),emu.callbackType.exec,{labels['retired526']})"
        script=once(script,end,f"end\ncheckedMem527(verify526(verifyRetirement744),emu.callbackType.exec,{labels['retired526']})\ncheckedMem527(verify526(verifyRetirement744),emu.callbackType.exec,0x7e3b00+3)")

        hook=f"""local watch744=false
local vmain744=nil
checkedMem527(function(_,v)vmain744=v end,emu.callbackType.write,0x2115)
local stream744=assert(io.open(ROOT..'/chain744.csv','w'))
stream744:write('event,clock,line,h,head,tail,source,bytes,addr,value\\n')
local function log744(event,a,v)
 local st=emu.getState();local head=word(0x1252)
 stream744:write(string.format('%s,%d,%d,%d,%d,%d,%d,%d,%d,%d\\n',event,st.masterClock,st['ppu.scanline'],
    st['memoryManager.hClock'],head,word(0x1250),word(0x4000+head),word(0x4004+head),a or 0,v or 0));stream744:flush()
end
checkedMem527(function(_,v)
 if word(0x1226)==957 and regs[0x4305]+256*regs[0x4306]==1536 and regs[0x4302]+256*regs[0x4303]==22528 then
  watch744=true;log744('map_start')
  @INSTALL@
 elseif watch744 then
  if regs[0x4302]+256*regs[0x4303]==19104 and regs[0x4305]==64 then
   assert(v==1 and regs[0x4300]==1 and regs[0x4301]==24 and regs[0x4304]==127 and vmain744==128)
  end
  log744('DMA')
 end
end,emu.callbackType.write,0x420b)
checkedMem527(function()if watch744 then log744('retire') end end,emu.callbackType.exec,{labels['retired526']})
checkedMem527(function(a,v)if watch744 then log744('read',a,v) end end,emu.callbackType.read,0x7e4000,0x7e40ff)
checkedMem527(function(a,v)if watch744 then log744('set',a,v) end end,emu.callbackType.write,0x4300,0x4306)
checkedMem527(function(a,v)if watch744 then log744('new_head',a,v);watch744=false end end,emu.callbackType.exec,{labels['head524']})
"""
        insert='' if a.control else f"""for i,v in ipairs({{{','.join(map(str,extra))}}}) do emu.write(0x3b00+i-1,v,emu.memType.snesWorkRam) end
  for i,v in ipairs({{76,0,59}}) do emu.write({ptr}+i-1,v,emu.memType.snesWorkRam) end"""
        if (a.calendar=='727' or a.stock) and not a.control:
            # The stock partial-map continuation subtracts a fixed 1152.
            # Advance either kind by the actual synchronous MDMAEN count in Y.
            at=(labels['dma_continue680']&65535)+9
            partial=original_edits(client,'fragment')[at]
            insert+="\n for i,v in ipairs({"+','.join(map(str,partial))+f"}}) do emu.write({at}+i-1,v,emu.memType.snesWorkRam) end"
        script=once(script,'local function loaded()',hook.replace('@INSTALL@',insert)+'local function loaded()')
        if a.fault=='none':
            return script
        if a.fault=='head':
            action="""assert(target522>st.masterClock and b522~='FINISH' and unhex(b522):byte(2)==5)
  target522=st.masterClock;rpc()"""
            at=labels['ready524']
        else:
            action="stop739=true"
            at=labels['priority524']
        fault=f"""local fired744=false
checkedMem527(function()
 if watch744 and not fired744 and regs[0x4302]+256*regs[0x4303]==19104 and regs[0x4305]==64 then
  fired744=true;local st=emu.getState();log744('fault');{action}
 end
end,emu.callbackType.exec,{at})
"""
        return once(script,'local finished522=false',fault+'local finished522=false')
    if a.calendar=='727':
        # This control must use the unmodified CPU at admission as well.
        # bitmap.baseline also checks identical cycle counts, which a real
        # successor test cannot require after its dispatch.
        from trace_nes_owner739 import run as original_run
        from replay_nes_map527 import run as original_replay
        def replay(args,*,edit_script):
            def compare(before,after):
                assert [r for r in before if int(r['g'])<957]==[r for r in after if int(r['g'])<957]
                if a.control: assert before==after
                return dict(prefix_events=sum(int(r['g'])<957 for r in after))
            return original_replay(args,edit_script=lambda s:install(edit_script(s),a.client),compare_trace=compare)
        with patch.object(bitmap.runner,'run',replay):
            original_run(a)
    elif a.stock:
        a.calendar='first'
        a.variant='budget'
        a.feedback=None
        a.lag_nops=0
        with patch.object(beam,'replacements',lambda client,variant:{}):
            beam.run(a,observe_script=lambda s:install(s,a.client),
                     adjust_arrivals=lambda folder,base,plan:bitmap.retime(folder,base,plan,'poll',a.scroll,pulse_folder=a.pulse_folder))
    else:
        with patch.object(bitmap,'observe_bulk',install):
            bitmap.run(a)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('client','trace','out','mesen'):
        p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--phase',type=int,choices=(1,2),required=True)
    p.add_argument('--scroll',choices=('original','first'),default='original')
    p.add_argument('--pulse-folder',type=Path)
    p.add_argument('--inject',choices=('none','head','during_obj'),default='none')
    p.add_argument('--mode',choices=('trace','stale','stop'),default='trace')
    p.add_argument('--calendar',choices=('727','early'),default='early')
    p.add_argument('--fault',choices=('none','head','prestop'),default='none')
    p.add_argument('--stock',action='store_true',help='Use the stock consumer on the priced early offers')
    p.add_argument('--control',action='store_true')
    p.set_defaults(baseline=False,save_quiet=False,restore_quiet=None)
    run(p.parse_args())
