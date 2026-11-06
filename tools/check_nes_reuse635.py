# SPDX-License-Identifier: MIT
"""Exercise receipt, retained WRAM and cancellation faults in the actual CPU."""
import argparse
import json
from pathlib import Path
from check_nes_group628 import SAVE_MAPS, recover
from check_nes_tail631 import SAVE_REGIONS, cold_script
from test_nes_seal538_stop import exercise
from nes_raw506 import once
from replay_nes_bank633 import packets, target


def run(a):
    a.out=a.out.resolve()
    a.out.mkdir(parents=True,exist_ok=False)
    a.generation=951
    lines=[]
    count=0
    head=bytes.fromhex(json.loads(a.arm_result.read_text())['head'])
    for line in (a.trace/'packets.jsonl').read_text().splitlines():
        _,clock,data,bulk=json.loads(line)
        h=bytes.fromhex(data)
        gen=int.from_bytes(h[8:10],'little')
        if gen>951:break
        if gen==951:
            seq=int.from_bytes(h[2:4],'little')
            if seq in (13,14,15,16,18,19):continue
            h=head if seq==17 else h[:2]+count.to_bytes(2,'little')+h[4:]
            assert int.from_bytes(h[2:4],'little')==count
            line=json.dumps([0,clock,h.hex(),bulk])
            count+=1
        lines.append(line)
    assert count==24
    stream=a.out/'packets.jsonl';stream.write_text('\n'.join(lines)+'\n')
    labels=json.loads((a.client/'labels.json').read_text())
    idle='compare635' in labels
    # Corrupt the very last omitted byte in each region, independently.
    def flip(pos):
        return f"local at=0x16000+((pb(4)-1)%2)*0x8000+{pos};emu.write(at,rd(at)~1,emu.memType.snesWorkRam)"
    cases={'wrong_bank_serial':"packet=packet:sub(1,128)..string.pack('<I4',46)",
           'short':"packet=packet:sub(1,12)..string.pack('<I2',115)..packet:sub(15,-2)",
           'palette':flip(511),'tail':flip(1055),
           'partial':"emu.write(0x1088,1,emu.memType.snesWorkRam)",
           'cold':"packet=string.char(9,4)..packet:sub(3,10)..string.pack('<I2I2I2',0,116,0)..string.rep(string.char(0),112)..string.pack('<I4',45)",
           'stop':"emu.write(0x14da,0x70,emu.memType.snesWorkRam);emu.write(0x14db,2,emu.memType.snesWorkRam)" if idle else ''}
    results=[]
    for name,action in cases.items():
        stop=name=='stop'
        status=228 if stop else 224
        condition='pb(0)==2 and pb(1)==2' if name=='cold' else ('pb(0)==1' if idle and name in ('palette','tail') else 'pb(0)==9')
        def inject(s):
            s=once(s,'local function loaded()',f"""local chosen=nil;local interrupted=false
emu.addMemoryCallback(function()if chosen and index==chosen then interrupted=true end end,emu.callbackType.exec,{labels['compare635' if idle else 'tail635']})
local function loaded()""")
            s=once(s,' if pb(0)==7 then tile=file',f''' if pw(8)==FAULT and not chosen and {condition} then chosen=index;{action} end
 if pb(0)==7 then tile=file''')
            s=once(s,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",'')
            if stop:s=once(s,'if a==0x6001 then','if a==0x6001 then if interrupted then return 128 end')
            checks=f"""assert(chosen and lastStatus=={status},'fault status')
 for i=0,8,2 do assert(word(0x14d0+i)==0,'uncleared receipt')end"""
            if stop:checks+=SAVE_MAPS+SAVE_REGIONS
            return once(s,"assert(lastStatus==0xe4,'STOP status')",checks)
        results.append(exercise(a,906 if name=='cold' else 951,name,edit_packet_case=inject,reject_status=status,packet_trace=stream))
    results.append(exercise(a,951,'final212',packet_trace=stream))
    # Exercise the same successful command on bank 1 (950), then interrupt
    # bank 0's final upload. The retained RGB must still be the original 950.
    commands=packets(a.trace)
    alternate=[];seq=0
    for line in lines:
        _,clock,data,bulk=json.loads(line);h=bytes.fromhex(data)
        if int.from_bytes(h[8:10],'little')==950:
            if h[1]==3 or (h[1]==4 and int.from_bytes(h[10:12],'little')!=0):continue
            if h[1]==4:
                h=bytes((9,4))+h[2:10]+bytes((0,0,116,0,0,0))+target(commands[950],4)[:112]+(44).to_bytes(4,'little')
            h=h[:2]+seq.to_bytes(2,'little')+h[4:];seq+=1
            line=json.dumps([0,clock,h.hex(),bulk])
        alternate.append(line)
    both=a.out/'both-banks.jsonl';both.write_text('\n'.join(alternate)+'\n')
    def both_stop(s):
        (a.out/'951-bothbank'/'expected635.bin').write_bytes(target(commands[950],3)+target(commands[950],4))
        s=once(s,'local function loaded()',f"""local bank1=false;local armed=false
emu.addMemoryCallback(function()if packet and pb(0)==3 and pw(8)==951 then armed=true end end,emu.callbackType.exec,{labels['final212']})
local function loaded()""")
        s=once(s,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end","if armed then return 128 end")
        s=once(s,'  lastStatus=ack[1]',"""  if pb(0)==9 and pw(8)==950 then
   assert(ack[1]==0 and word(0x1020)==0x8000)
   local expected=file('expected635.bin')
   for j=0,1055 do assert(rd(0x1e000+j)==expected:byte(j+1),'bank1 byte')end
   bank1=true
  end
  lastStatus=ack[1];""")
        return once(s,"assert(lastStatus==0xe4,'STOP status')","assert(bank1 and armed and lastStatus==0xe4,'bank1 reuse then STOP')")
    results.append(exercise(a,951,'bothbank',edit_packet_case=both_stop,packet_trace=both))
    cold=recover(a,prepare_script=lambda out,s:cold_script(out,s,a.trace))
    (a.out/'guards.json').write_text(json.dumps(dict(cases=results,cold=cold),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','client','arm-result','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
