"""Drive real M4/SNES across FFFE,FFFF,0000 using three unchanged scene fixtures.

Only fixture identifiers and endpoint wire identities are rebound. Actual M4
input/plan/output/ACK code and the SNES program are unmodified. Source/ROM/queue
remain the existing timing model; this is a wrap functional test, not timing.
"""
import inspect,json,runpy,struct,subprocess,textwrap
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import test_nes_raw506_joint as joint
import test_nes_tile532 as tile
import test_nes_sender652 as sender
from nes_direct653 import encode
from nes_raw506 import once
from test_nes_longrun694 import call

BASE=joint.Link
def wire(g):return (g-905+65534)&65535

def edited(fn,old,new):
    s=textwrap.dedent(inspect.getsource(fn));s=once(s,old,new)
    ns=joint.__dict__;ns['wire694']=wire
    exec(compile(s,'wrap694-fixture','exec'),ns)
    return ns.pop(fn.__name__)

def main():
    begin=edited(joint.Runtime.begin_input,')(geom,raw,g)',')(geom,raw,wire694(g))')
    accept=edited(BASE.accept,"struct.pack('<H',self.generation)","struct.pack('<H',wire694(self.generation))")
    plan=joint.wire_plan;response=BASE.response;schedule=tile.run_schedule;gates=sender.gates;launch=subprocess.Popen
    def wire_plan(q):return plan(struct.pack('<H',wire(struct.unpack_from('<H',q)[0]))+q[2:])
    def reply(self,tx):
        r=bytearray(response(self,tx))
        if tx[0]==0xe8 and r[6]:
            r[12:14]=struct.pack('<H',wire(struct.unpack_from('<H',r,12)[0]));r[19]=joint.crc(r[1:19],8,7,0)
        return bytes(r)
    def short(a,instrument,link_type,frames):return schedule(a,instrument,link_type,3)
    def rebound(rows,board_owner):
        rows={k:v for k,v in json.loads(json.dumps(rows)).items() if 905<=int(k)<=907}
        # Preserve source allocation, replace only generation-bearing wire
        # fixtures with the real encoder's new identity. Not fresh RTL time.
        data=Path('../probes/nes-delta231/test07')
        for g in (905,906,907):
            packets,_,_=encode((data/f'frame{g}.geometry').read_bytes(),(data/f'frame{g}.raw').read_bytes(),wire(g))
            assert len(packets)==len(rows[str(g)])
            for p,r in zip(packets,rows[str(g)]):assert len(p)==len(bytes.fromhex(r['wire']));r['wire']=p.hex()
        return gates(rows,board_owner)
    def popen(args,*pargs,**kwargs):
        if '--testRunner' in args:
            f=Path(args[args.index('--testRunner')+1]);s=f.read_text(encoding='utf8')
            if f.name=='capture.lua':
                # Normalize oracle filenames/statistics only, never bytes
                # returned to the CPU or exact ACK identity comparisons.
                s='local function logical694(g)return ((g-65534)&65535)+905 end\n'+s
                s=once(s,'local g=requests[sent]:byte(9)+256*requests[sent]:byte(10)',
                    'local g=logical694(requests[sent]:byte(9)+256*requests[sent]:byte(10))')
                s=s.replace('pw(8)','logical694(pw(8))').replace('word(0x1226)','logical694(word(0x1226))')
                f.write_text(s,encoding='utf8',newline='\n')
        return launch(args,*pargs,**kwargs)
    with ExitStack() as st:
        for obj,name,value in ((joint.Runtime,'begin_input',begin),(BASE,'accept',accept),
            (BASE,'response',reply),(joint,'wire_plan',wire_plan),(tile,'run_schedule',short),
            (sender,'gates',rebound),(subprocess,'Popen',popen),(joint.Runtime,'call',call)):
            st.enter_context(patch.object(obj,name,value))
        runpy.run_module('test_nes_status689',run_name='__main__')

if __name__=='__main__':main()
