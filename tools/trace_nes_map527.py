# SPDX-License-Identifier: MIT
"""Timestamp the last BG map write, immutable BG boundary, plan END and the map enqueue on the linked MCU."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_MEM_WRITE

import test_nes_raw506_joint as joint
from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from test_nes_trim514_schedule import run_schedule
from trace_nes_obj518 import ObjLink
from test_nes_idle524_schedule import observe
from test_nes_map526_schedule import observer
from nes_raw506 import once


class CheckedLink(ObjLink):
    def exchange(self,seq,target,operation,args):
        reply=super().exchange(seq,target,operation,args)
        if len(reply)!=5 or any(len(x.split(':'))!=3 for x in reply[4].split(';') if x):
            (self.a.out/'bad-reply.json').write_text(json.dumps([seq,target,operation,reply]))
            raise ValueError('invalid simulator reply; saved bad-reply.json')
        return reply


def observed(s,args):
    s=observe(s,args,observer) if args.map526 else observe(s,args)
    s=once(s,"rpc=function()\n if finished then return end","""local inRpc527=false
local lastPush527=0
rpc=function()
 if finished or inRpc527 then return end
 inRpc527=true""")
    s=once(s,"assert(sent-retired<4,'queue overflow');sent=sent+1","""assert(sequence>lastPush527,'duplicate PUSH '..sequence)
   lastPush527=sequence
   assert(sent-retired<4,string.format('queue overflow PUSH %d sent %d retired %d',sequence,sent,retired));sent=sent+1""")
    s=once(s,'nextCommand();now=emu.getState().masterClock\n end\nend',
           'nextCommand();now=emu.getState().masterClock\n end\n inRpc527=false\nend')
    # Save any Lua assertion at the point of failure, including nested bus callbacks.
    s=s.replace('emu.addMemoryCallback(', 'checkedMem527(').replace('emu.addEventCallback(', 'checkedEvent527(')
    return once(s,'local function file(name)',"""local failed527=false
local function wrap527(fn)
 return function(...)
  if failed527 then return end
  local ok,v=pcall(fn,...);if ok then return v end
  failed527=true
  local f=assert(io.open(ROOT..'/callback-error.txt','w'));f:write(tostring(v));f:close();emu.stop(1)
 end
end
local function checkedMem527(cb,...)return emu.addMemoryCallback(wrap527(cb),...)end
local function checkedEvent527(cb,...)return emu.addEventCallback(wrap527(cb),...)end
local function file(name)""")


class MapRuntime(joint.Runtime):
    def __init__(self,a,link):
        super().__init__(a,link)
        regs=(UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)
        video=self.layout['nes_native_video165']
        resident=self.layout['nes_resident211']
        def record(event,**fields):
            self.events.append(dict(generation=self.generation,event=event,clock=self.clock,**fields))
        self.groups={}
        def map_word(u,pc,size,user):
            row=u.reg_read(regs[1])//64
            self.groups[row]=self.clock
        def bg_done(u,pc,size,user):
            if u.reg_read(regs[0])!=self.video+video['oam'] or u.reg_read(regs[2])!=544:
                return
            bank=u.mem_read(self.resident+resident['target'],1)[0]
            stale=int.from_bytes(u.mem_read(self.resident+resident['map_stale']+8*bank,8),'little')
            dirty=int.from_bytes(u.mem_read(self.video+video['map_dirty'],8),'little')
            mask=stale|dirty
            first=(mask&-mask).bit_length()-1 if mask else None
            n=0
            if first is not None:
                while n<3 and (mask>>(first+n))&1:n+=1
            data=bytes(u.mem_read(self.video+video['map'],4096))
            record('bg_map_frozen',first=first,rows=n,sha256=hashlib.sha256(data).hexdigest(),
                   first_span_last_writer=max((self.groups.get(i,0) for i in range(first,first+n)),default=0) if n else None)
            self.groups.clear()
        def packet(u,pc,size,user):
            if u.reg_read(regs[1]) in (2,24) and u.reg_read(regs[2])==2:
                record('map_packet_enter',offset=u.reg_read(regs[3]),early=u.reg_read(regs[1])==24)
        def enqueue(u,pc,size,user):
            hdr=bytes(u.mem_read(u.reg_read(regs[1]),16))
            if hdr[1]==2 and hdr[0] in (2,4):
                record('map_enqueue',offset=struct.unpack_from('<H',hdr,10)[0])
        for name,fn in [('memset',bg_done),('map_word185',map_word),('packet_wire',packet),
                        ('nes_window184_enqueue',enqueue),('nes_plan200_end',lambda *x:record('end_enter')),
                        ('nes_resident211_prepare',lambda *x:record('prepare_enter'))]:
            if name=='map_word185' and name not in self.syms:
                # The split planner can inline its single map writer. Observe
                # actual stores rather than changing target code to keep a symbol.
                start=self.video+video['map']
                def stored(u,access,address,size,value,user):
                    for at in range(max(address,start),min(address+size,start+4096)):
                        self.groups[(at-start)//64]=self.clock
                self.u.hook_add(UC_HOOK_MEM_WRITE,stored,begin=start,end=start+4095)
                continue
            pc=self.syms[name]
            self.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)
        if 'nes_plan527_map_credit' in self.syms:
            def attempt(u,pc,size,user):
                layout=self.layout['nes_native_runtime165'];window=self.rt+layout['transport']
                def counter(field):
                    return int.from_bytes(u.mem_read(window+self.layout['nes_sink_window184'][field],2),'little')
                record('map_credit_attempt',outstanding=(counter('sent')-counter('retired'))&65535)
            pc=self.syms['nes_plan527_map_credit']
            self.u.hook_add(UC_HOOK_CODE,attempt,begin=pc,end=pc)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','data','fixture','plans','client','mesen','out','calendar','driver503','capture'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--start-clock',type=int,required=True)
    p.add_argument('--map526',action='store_true')
    a=p.parse_args()
    joint.Runtime=MapRuntime
    run_schedule(a,observed,CheckedLink,frames=53)
