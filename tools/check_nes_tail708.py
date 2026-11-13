"""Linked packet byte-definedness with poisoned stack and failure ACK checks.

Isolated M4 packet boundary, mocked callbacks and128KiB unit RAM, not timing,
physical RAM budget, SPI/IRQ or SNES proof. Full linked schedule is separate.
"""
import argparse,json,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,sha
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
from unicorn import UC_HOOK_MEM_WRITE

class Packet(ARM):
    def __init__(self,src):
        self.written=set();self.output=[];self.inject='normal';self.monitor=False
        super().__init__(src,'normal');self.setup()
        def wrote(u,access,address,size,value,user):
            if self.monitor:self.written.update(range(address,address+size))
        self.u.hook_add(UC_HOOK_MEM_WRITE,wrote,begin=0x2001c000,end=0x2001efff)
    def hook(self,u,pc,size,user):
        if pc==getattr(self,'syms',{}).get('packet_wire',-1):self.written=set();self.monitor=True
        if pc in [getattr(self,'syms',{}).get(n,-1) for n in ('nes_window184_enqueue','nes_window184_barrier')]:
            at=u.reg_read(UC_ARM_REG_R1);n=u.reg_read(UC_ARM_REG_R2)
            missing=[i for i in range(n) if at+i not in self.written]
            assert not missing,('undefined packet bytes',missing)
            b=bytes(u.mem_read(at,n));self.output.append(b)
            if pc==self.syms['nes_window184_barrier']:
                ack=u.reg_read(UC_ARM_REG_R3)
                assert bytes(u.mem_read(ack,12))==bytes(12),'failure ACK must start zero'
                if self.inject!='failure':
                    a=bytearray([1 if b[0]==3 else 0,b[0]])+b[2:10]+b'\x65\x9a'
                    if self.inject=='bad_ACK':a[2]^=1
                    u.mem_write(ack,bytes(a))
            u.reg_write(UC_ARM_REG_R0,int(self.inject!='failure'));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,pc,size,user)
    def test(self,op,section,offset,data,expanded,inject):
        self.monitor=False;self.output=[];self.inject=inject
        self.u.mem_write(0x2001c000,b'\xa5'*0x3000)
        self.u.mem_write(self.q,data or b'\xcc')
        for k,v,n in [('state',1,1),('error',0,1),('sequence',0,2),('plan',0,4)]:self.put(self.s,'nes_native_sink165',k,v,n)
        before=self.instructions
        ok=bool(self.call('packet_wire',[self.s,op,section,offset,self.q,len(data),expanded]))
        count=self.instructions-before;assert len(self.output)==1
        b=self.output[0];actualop=7 if op==23 else 2 if op==24 else op
        n=len(data);expected_data=data;ex=expanded
        if actualop==2 and n>=4 and not n%2 and all(data[i]==data[i%2] for i in range(n)):
            actualop=4;ex=n;expected_data=data[:2]
        expected=bytes([actualop,section])+struct.pack('<HIHHHH',0,1,907,offset,len(expected_data),ex)+expected_data
        assert b==expected,(op,section,len(data),b.hex(),expected.hex())
        assert ok==(inject=='normal')
        if not ok:assert self.get(self.s,'nes_native_sink165','error') in (2,3)
        return dict(op=op,section=section,n=len(data),expanded=expanded,inject=inject,passed=True,packet=b.hex(),instructions=count)

def run(a):
    cases=[]
    for n in (0,1,2,3,4,21,64,192,240):
        for repeat in (False,True):cases.append((2,2,128,bytes((i%2 if repeat else i*37+13)&255 for i in range(n)),0,'normal'))
    for op,sec,off,n,exp in ((1,0,0,12,0),(3,0,0,168,0),(5,5,21,2,1100),(6,2,256,2,256),(7,0,0,4,16),(23,1,32,4,32),(24,2,128,192,0),(8,4,112,4,400),(9,4,0,116,0)):
        cases.append((op,sec,off,bytes(i&255 for i in range(n)),exp,'normal'))
    for inject in ('failure','bad_ACK'):cases.append((3,0,0,bytes(range(168)),0,inject))
    result={}
    for name,src in [('base',a.base),('candidate',a.arm)]:
        m=Packet(src);rows=[m.test(*c) for c in cases];result[name]=dict(firmware=sha(src/'obj-nes-100/firmware.stm'),cases=rows)
    for x,y in zip(result['base']['cases'],result['candidate']['cases'],strict=True):assert x['packet']==y['packet']
    r=dict(passed=True,scope=__doc__,runs=result,cases=len(cases),per_case_instruction_delta=[y['instructions']-x['instructions'] for x,y in zip(result['base']['cases'],result['candidate']['cases'])])
    a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS708',len(cases),'poisoned stack/defined bytes and failed ACK cases',r['per_case_instruction_delta'])

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','arm','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
