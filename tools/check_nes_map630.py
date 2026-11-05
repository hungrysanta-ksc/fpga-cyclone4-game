# SPDX-License-Identifier: MIT
"""Reject damaged row descriptors before DMA and cancel after one complete map row."""
import argparse
import json
from pathlib import Path
from nes_raw506 import once
from test_nes_seal538_stop import exercise
from check_nes_group628 import SAVE_MAPS, recover

def run(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    pc=json.loads((a.client/'labels.json').read_text())['row630']
    cases={'length':"packet=packet:sub(1,12)..string.pack('<I2',107)..packet:sub(15,-2)",
           'span':"packet=packet:sub(1,14)..string.pack('<I2',128)..packet:sub(17)",
           'address':"packet=packet:sub(1,10)..string.pack('<I2',4032)..packet:sub(13)",
           'zero':"packet=packet:sub(1,89)..string.char(1)..packet:sub(91)",'stop':''}
    rows=[]
    for kind,fault in cases.items():
        stop=kind=='stop'
        def inject(s):
            s=once(s,'local function loaded()',f"""local chosen=nil;local chunks=0;local started=0
emu.addMemoryCallback(function()if index==chosen then chunks=chunks+1 end end,emu.callbackType.exec,{pc})
emu.addMemoryCallback(function()if index==chosen then started=started+1 end end,emu.callbackType.write,0x420b)
local function loaded()""")
            s=once(s," if pb(0)==7 then tile=file",f""" if pw(8)==FAULT and pb(0)==2 and pb(1)==2 and pw(10)==2048 then
  chosen=index;local orig=packet;local t={{string.char(9)..orig:sub(2,12)..string.pack('<I2I2',108,192)}}
  for row=0,2 do local pos=17+64*row
   assert(orig:sub(pos+34,pos+63)==string.rep(string.char(0),30))
   t[#t+1]=string.char(34,0)..orig:sub(pos,pos+33)
  end
  packet=table.concat(t);{fault}
 end
 if pb(0)==7 then tile=file""")
            s=once(s,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",'')
            if stop:
                s=once(s,'if a==0x6001 then','if a==0x6001 then if index==chosen and chunks==2 then return 128 end')
            return once(s,"assert(lastStatus==0xe4,'STOP status')",
                        f"assert(chosen and lastStatus=={228 if stop else 224} and started=={2 if stop else 0},'invalid DMA or status')"+(SAVE_MAPS if stop else ''))
        rows.append(exercise(a,951,kind,edit_packet_case=inject,reject_status=228 if stop else 224))
    def cold(s):
        s=once(s,' if pb(0)==7 then tile=file',""" if pw(8)==FAULT and pb(0)==2 and pb(1)==2 then
 packet=string.char(9)..packet:sub(2) end
 if pb(0)==7 then tile=file""")
        s=once(s,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",'')
        return once(s,"assert(lastStatus==0xe4,'STOP status')","assert(lastStatus==224,'bad cold map accepted')")
    rows.append(exercise(a,906,'cold',edit_packet_case=cold,reject_status=224))
    a.generation=951
    (a.out/'guards.json').write_text(json.dumps(dict(cases=rows,restart=recover(a,receipt_tags=False)),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
