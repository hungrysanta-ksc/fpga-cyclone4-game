# SPDX-License-Identifier: MIT
"""Independently certify a whole row from one received packet at each bank's final ACK."""
import argparse
from pathlib import Path
from nes_raw506 import once
from replay_nes_header546 import observer as headers
from replay_nes_history547 import history
import replay_nes_map527 as replay


def receipt(source,labels):
    s=history(source,labels)
    s=once(s,'local saved547={}',"""local saved547={}
local pending548={}
local function accepted548()
 if lastStatus~=0 then return end
 if pb(0)==1 then pending548={};return end
 if pb(1)~=5 or (pb(0)~=4 and pb(0)~=5) then return end
 assert(pw(12)==2)
 local value=pb(16)
 if value~=pb(17) or not ALLOWED548 then return end
 for r=0,5 do
  local start=1121+64*r
  if pw(10)<=start and start+64<=pw(10)+pw(14) then
   assert(pending548[r]==nil,'overlapping certificate')
   pending548[r]=value
  end
 end
end""".replace('ALLOWED548','(true)' if 'generic548' in labels else '(value==0 or (pb(0)==4 and value==255))'))
    s=once(s,'local equal=warm','local equal=warm and pending548[row]~=nil and old.values[row]==pending548[row]')
    s=once(s,"if rd(0x16961+0x8000*bank+row*64+b)~=live then equal=false end",
           """local incoming=rd(0x16961+0x8000*bank+row*64+b)
   if pending548[row]~=nil then assert(incoming==pending548[row],'fill destination value') end
   if equal then assert(incoming==live and live==old.image[row*64+b],'receipt/actual VRAM mismatch') end""")
    if 'generic548' in labels:
        verify="""for row=0,5 do
  local value=pending548[row] and pending548[row]+1 or 0
  assert(word(0x14a0+2*row)==value and word(0x14ac+a.bank*12+2*row)==value)
 end"""
    else:
        verify="""local bits=0
 for row,value in pairs(pending548) do bits=bits|(1<<(row+(value==255 and 8 or 0))) end
 assert(word(0x14a0)==bits and word(0x14a2+a.bank*2)==bits)"""
    s=once(s,'for b=0,383 do assert(rd(0x6961+0x8000*a.bank+b)==rd(0x16961+0x8000*a.bank+b)) end',verify)
    s=once(s,'saved547[bank]={g=pw(8),mode=rd(0x125a+bank),image=image}',
           """local prior=saved547[bank]
 local values=active547 and pending548 or (prior and prior.values or {})
 saved547[bank]={g=pw(8),mode=rd(0x125a+bank),image=image,values=values}""")
    return once(s,'if lastStatus==1 then publish547()', 'accepted548();if lastStatus==1 then publish547()')


def observe(source,labels):
    source=receipt(headers(source,labels),labels)
    return once(source,'local function loaded()',f"""for _,base in ipairs({{0x7e6961,0x7ee961}})do
 for _,event in ipairs({{emu.callbackType.read,emu.callbackType.write}})do
  emu.addMemoryCallback(verify526(function()error('obsolete raw shadow accessed')end),event,base,base+383)
 end
end
local started548=nil
local costs548=assert(io.open(ROOT..'/fill548.csv','w'))
costs548:write('g,index,offset,span,value,start,finish\\n')
emu.addMemoryCallback(verify526(function()
 assert(packet and started548==nil)
 started548=emu.getState().masterClock
end),emu.callbackType.exec,{labels['fill_receipt548']})
emu.addMemoryCallback(verify526(function()
 if started548 then
  costs548:write(string.format('%d,%d,%d,%d,%d,%d,%d\\n',pw(8),index,pw(10),pw(14),pb(16),started548,emu.getState().masterClock))
  started548=nil
 end
end),emu.callbackType.exec,{labels['accepted']})
local function loaded()""")


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('trace','client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--frames',type=int,default=53)
    args=p.parse_args();replay.observer=observe;replay.run(args)
