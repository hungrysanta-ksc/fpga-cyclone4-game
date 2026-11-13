"""Reject changed manifest and bulk identity before granting parser-owned DMA."""
import argparse,json
from pathlib import Path
from test_nes_seal538_stop import exercise
from nes_raw506 import once,sha

def run(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    labels=json.loads((a.client/'labels.json').read_text());rows=[]
    for gen in (906,907):
        for name in ('bad_version','bad_count','bad_length','descriptor'):
            def edit(s):
                s=once(s,'@MODE@',json.dumps(name))
                if name=='descriptor':
                    s=once(s,'return d[a-0x6040+1]',"if pw(8)==FAULT and a==0x6046 then return d[7]~1 end;return d[a-0x6040+1]")
                    s=once(s,"if pb(0)==7 then assert(lastStatus==0 and reads==#tile,'early bulk ACK')end",
                        "if pb(0)==7 then if pw(8)==FAULT then assert(lastStatus==224 and reads==0,'bad descriptor consumed')else assert(lastStatus==0 and reads==#tile,'early bulk ACK')end end")
                    s+=f"\nemu.addMemoryCallback(function()assert(not packet or pw(8)~=FAULT,'bad descriptor entered DMA arbitration')end,emu.callbackType.exec,{labels['owned_bulk725']})\n"
                return s
            rows.append(dict(case=name,**exercise(a,gen,name,edit_packet_case=edit,reject_status=224)))
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,cases=rows,client=sha(a.client/'sink165.sfc'),scope=__doc__),indent=2)+'\n')
    print('PASS725 independent packet/descriptor rejects',len(rows))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('client','trace','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
