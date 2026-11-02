# SPDX-License-Identifier: MIT
"""Cancel a warm comparison or actual raw write, then restore from that exact partial bank."""
import argparse
import csv
import json
from pathlib import Path
from types import SimpleNamespace
import replay_nes_map527 as replay
from nes_raw506 import once
from replay_nes_history547 import observe
from test_nes_seal538_stop import exercise


def cancel(source,labels,partial):
    label='advance547' if partial else 'row547'
    source=once(source,'local function loaded()',f"""local writes547,rows547,stop547=0,0,false
emu.addMemoryCallback(function()
 if packet and pb(0)==3 and pw(8)==FAULT then writes547=writes547+1 end
end,emu.callbackType.exec,{labels['write547']})
emu.addMemoryCallback(function()
 if packet and pb(0)==3 and pw(8)==FAULT then
  rows547=rows547+1
  if {('writes547==1' if partial else 'rows547==4')} then stop547=true end
 end
end,emu.callbackType.exec,{labels[label]})
local function loaded()""")
    source=once(source,'if a==0x6001 then','if a==0x6001 then if stop547 then return 128 end')
    source=once(source,"assert(lastStatus==0xe4,'STOP status')", """assert(stop547 and lastStatus==0xe4 and rd(0x125a+word(0x1034))==0,'published partial bank')
   local bank=word(0x1034)
   local f=assert(io.open(ROOT..'/partial.bin','wb'))
   for i=0,383 do f:write(string.char(rd(0x6961+0x8000*bank+i))) end
   for i=0,2047 do f:write(string.char(emu.read((bank==0 and 0x5000 or 0x9000)+i,emu.memType.snesVideoRam))) end
   f:write(string.char(rd(0x125a+bank),writes547));f:close()""")
    return source


def restore(args,fault,gen,partial):
    name='after-write' if partial else 'mid-compare'
    path=fault/f'{gen}-{name}'/'partial.bin'
    data=path.read_bytes()
    assert len(data)==2434 and data[-2:]==bytes([0,int(partial)])
    # Restore exactly the stopped physical bank before this generation's
    # decoder, with its invalid tag. The subsequent full transfer must repair it.
    def edit(s):
        return once(s,'local function loaded()',f"""emu.addMemoryCallback(verify526(function()
 if not packet or pw(8)~={gen} then return end
 local f=assert(io.open({json.dumps(path.resolve().as_posix())},'rb'));local b=f:read('*a');f:close()
 local bank=word(0x1034);assert(rd(0x125a+bank)==2)
 for i=0,383 do emu.write(0x6961+bank*0x8000+i,b:byte(i+1),emu.memType.snesWorkRam) end
 for i=0,2047 do emu.write((bank==0 and 0x5000 or 0x9000)+i,b:byte(385+i),emu.memType.snesVideoRam) end
 emu.write(0x125a+bank,b:byte(2433),emu.memType.snesWorkRam)
end),emu.callbackType.exec,{args.labels['compact_rows489']})
local function loaded()""")
    sub=SimpleNamespace(trace=args.trace,client=args.client,mesen=args.mesen,out=args.out/f'restore-{gen}-{name}',frames=gen-904)
    replay.observer=observe
    replay.run(sub,edit_script=edit,compare_trace=lambda _,actual:dict(recovered_events=len(actual)))
    with (sub.out/'history547.csv').open() as f:rows=list(csv.DictReader(f))
    row,=[r for r in rows if int(r['g'])==gen]
    assert int(row['prior'])==-1 and int(row['writes'])==6 and int(row['omitted'])==0
    return dict(g=gen,case=name,status=228,writes_before_fault=data[-1],writes_after_recovery=6)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('trace','client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args()
    args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=False)
    args.labels=json.loads((args.client/'labels.json').read_text());rows=[]
    for g in (907,908):
        for partial in (False,True):
            exercise(args,g,'after-write' if partial else 'mid-compare',
                     edit_packet_case=lambda s:cancel(s,args.labels,partial))
            rows.append(restore(args,args.out,g,partial))
    (args.out/'result.json').write_text(json.dumps(rows,indent=2)+'\n')
