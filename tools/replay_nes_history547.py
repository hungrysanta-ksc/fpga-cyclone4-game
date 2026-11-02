# SPDX-License-Identifier: MIT
"""Prove skipped rows from the last display ACK and actual inactive VRAM bytes."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once
from replay_nes_header546 import observer as headers
import replay_nes_map527 as replay


def observe(source,labels):
    return history(headers(source,labels),labels)


def history(source,labels):
    hooks="""local saved547={}
local active547=nil
local log547=assert(io.open(ROOT..'/history547.csv','w'))
log547:write('g,bank,prior,mask,writes,omitted,prepare,finish\\n')
local function sample547(bank,row,b)
 local at=(bank==0 and 0x5000 or 0x9000)+(b//2)*64+(row//2)*16+(row%2)*2+b%2
 return emu.read(at,emu.memType.snesVideoRam)
end
local function prepare547()
 if word(0x1258)~=384 then return end
 local bank=word(0x1034);local old=saved547[bank];local mask=0
 local warm=word(0x125c)==1
 if warm then assert(old and old.mode==2,'uncommitted history') end
 for row=0,5 do
  local equal=warm
  for b=0,63 do
   local live=sample547(bank,row,b)
   if warm then assert(live==old.image[row*64+b]) end
   if rd(0x16961+0x8000*bank+row*64+b)~=live then equal=false end
  end
  if equal then mask=mask|(1<<row) end
 end
 active547={bank=bank,mask=mask,prior=warm and old.g or -1,row=-1,issued=0,n=0,prepare=emu.getState().masterClock}
end
local function prepared547()
 local a=active547
 if not a then return end
 assert(rd(0x125a+a.bank)==0 and (word(0x78)&63)==a.mask)
 for b=0,383 do assert(rd(0x6961+0x8000*a.bank+b)==rd(0x16961+0x8000*a.bank+b)) end
 a.finish=emu.getState().masterClock
end
local function row547()
 if active547 then active547.row=active547.row+1 end
end
local function write547()
 local a=active547
 if a then
  assert(a.row>=0 and a.row<=5 and a.mask&(1<<a.row)==0)
  a.issued=a.issued|(1<<a.row);a.n=a.n+1
 end
end
local function publish547()
 local bank=word(0x1034);local image={}
 for row=0,5 do for b=0,63 do image[row*64+b]=sample547(bank,row,b) end end
 saved547[bank]={g=pw(8),mode=rd(0x125a+bank),image=image}
 local a=active547
 if a then
  assert(a.bank==bank and a.row==5 and a.issued==(63~a.mask) and saved547[bank].mode==2)
  log547:write(string.format('%d,%d,%d,%d,%d,%d,%d,%d\\n',pw(8),bank,a.prior,a.mask,a.n,6-a.n,a.prepare,a.finish))
  active547=nil
 end
end
"""
    for label,fn in [('prepare547','prepare547'),('exit547','prepared547'),('raw_row489','row547'),('write547','write547')]:
        hooks+=f"emu.addMemoryCallback(verify526({fn}),emu.callbackType.exec,{labels[label]})\n"
    source=once(source,'local function loaded()',hooks+'local function loaded()')
    return once(source,'if lastStatus==1 then','if lastStatus==1 then publish547()')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('trace','client','mesen','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--frames',type=int,default=53)
    args=parser.parse_args()
    replay.observer=observe
    replay.run(args)
