# SPDX-License-Identifier: MIT
"""Validate fixed fills against the held packet, independently of the CPU cursor."""
from nes_raw506 import once


def observe(source):
    source = once(source, 'local function loaded()', """local fillBytes545,fillServiced545=0,false
local function uniform545()
 return packet and pb(1)==5 and ((pb(0)==4 and pw(14)>=64 and pw(12)==2 and pb(16)==pb(17))
   or (pb(0)==5 and pw(16)==0))
end
local function loaded()""")
    source = once(source, 'if a==0x6001 then', """if a==0x6001 then
  if uniform545() then fillServiced545=true;sample516('fill_service545',fillBytes545) end""")
    source = once(source, 'pb(0)==5 and pb(1)==5 and pw(16)==0 and n>0 and n<=64',
                  'uniform545() and fillServiced545 and n==math.min(64,pw(14)-fillBytes545) and n>0')
    source = once(source, "sample516('zero_dma',n)", """fillBytes545=fillBytes545+n;fillServiced545=false
   sample516('zero_dma',n)""")
    return once(source, 'lastStatus=ack[1];sample516("ack",lastStatus)', """if uniform545() then
   assert(fillBytes545==pw(14) and fillServiced545,'fill ACK before completion/service')
   local address=0x10000+word(0x1020)+0x6500+pw(10)
   for j=0,fillBytes545-1 do assert(rd(address+j)==pb(16),'fixed fill WRAM') end
  end
  fillBytes545=0;fillServiced545=false
  lastStatus=ack[1];sample516("ack",lastStatus)""")
