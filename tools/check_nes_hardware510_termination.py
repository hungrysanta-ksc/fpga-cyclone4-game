# SPDX-License-Identifier: MIT
"""Linked509 ordinary-credit deadline; modeled SPI/ticks, not physical-instant replay."""
import argparse,json,struct,re,shutil
from pathlib import Path
from check_nes_hardware503_termination import GuardDeadline,sha
from check_nes_supply485_arm import crc
from analyze_nes_supply485_hardware import analyse,fields
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
ROOT=Path(__file__).resolve().parents[1]
class CreditDeadline(GuardDeadline):
    def __init__(self,src,mode):
        self.armed=False;self.polls=0;self.new_writes=0
        super().__init__(src,mode)
        p=self.rt+self.layout['nes_native_runtime165']['plan']
        for k,v,n in [('started',1,1),('ending',1,1),('finished',1,1),('generation',857,2)]:self.put(p,'nes_plan200',k,v,n)
        for k,v,n in [('serial',771,4),('generation',857,2),('sequence',17,2)]:self.put(self.s,'nes_native_sink165',k,v,n)
        self.put(self.rt,'nes_native_runtime165','frames',770,4)
        for k,v,n in [('sent',18879,2),('retired',18875,2),('ever_sent',1,1)]:self.put(self.w,'nes_sink_window184',k,v,n)
        self.last_header=bytes([2,5])+struct.pack('<HIH',16,771,857)
        self.u.mem_write(self.w+self.layout['nes_sink_window184']['last'],self.last_header)
        self.payload=0x20002300;self.u.mem_write(self.payload,bytes(range(81)));self.armed=True
    def hook(self,u,at,size,user):
        if self.armed and at==self.spi:
            n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n));self.calls.append(tx.hex());rx=bytearray(n);ok=1
            if tx[0]==0xe1:self.new_writes+=1
            else:
                assert tx[0]==0xe0 and n==20;self.polls+=1;self.seal_polls+=1
                full=self.polls==1 or self.mode!='normal';used=4 if full else 3
                rx[1]=0xf7;rx[2]=7 if full else 3;rx[3:7]=struct.pack('>HH',18879,18879-used)
                header=bytearray(self.last_header);header[2:4]=struct.pack('<H',16-used)
                rx[7:19]=bytes([0,header[0]])+header[2:10]+b'\x65\x9a';rx[19]=crc(rx[1:19],8,7,0)
                if self.polls==2:
                    if self.mode=='deadline':self.expired=True
                    if self.mode=='IO_fault':ok=0
                    if self.mode=='bad_CRC':rx[19]^=1
            u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(rx));u.reg_write(UC_ARM_REG_R0,ok);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)
def run(src,mode):
    m=CreditDeadline(src,mode);args=[m.s,2,5,1505,m.payload,81,0];ok=m.call('packet_wire',args)
    r=dict(mode=mode,ok=ok,runtime=m.get(m.rt,'nes_native_runtime165','result'),window=m.get(m.w,'nes_sink_window184','error'),sink=m.get(m.s,'nes_native_sink165','error'),frames=m.get(m.rt,'nes_native_runtime165','frames',4),pending=m.get(m.w,'nes_sink_window184','sent',2)-m.get(m.w,'nes_sink_window184','retired',2),flags=m.get(m.w,'nes_sink_window184','status_flags'),new_E1=m.new_writes,displayed=m.get(m.s,'nes_native_sink165','displayed'),resident_displayed=m.get(m.resident,'nes_resident211','displayed'))
    assert r['frames']==770 and r['displayed']==r['resident_displayed']==0
    if mode=='normal':assert ok and r['new_E1']==1 and r['runtime']==r['window']==r['sink']==0
    else:
        expected={'guard_deadline':(1,2,2),'deadline':(1,3,2),'IO_fault':(3,3,2),'bad_CRC':(0,4,2)}[mode]
        assert not ok and (r['runtime'],r['window'],r['sink'])==expected,r
        assert r['pending']==4 and r['flags']==7 and r['new_E1']==0,r
        trace=bytes(m.u.mem_read(m.data_symbols['nes_sink_trace168'],32));assert trace[:4]==b'\x01\0\0\0'and trace[4:20].hex()=='02051100030300005903e10551000000'and trace[20:]==bytes(12)
        before=len(m.calls);assert m.call('packet_wire',args)==0 and len(m.calls)==before
    return r
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['arm','raw','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    firmware=sha(a.arm/'obj-nes-100/firmware.stm');assert firmware==json.loads((ROOT/'analysis/service509-release.json').read_text())['firmware_SHA256']
    rows=[run(a.arm,m)for m in ['normal','guard_deadline','deadline','IO_fault','bad_CRC']]
    assert analyse(a.raw,509)['termination_class']=='deadline_during_ordinary_credit_signature'
    mutations={'native_result':'3','native_video_error':'14','native_receiver_error':'1','native_sink_error':'3','sink_window_error':'3','plan_error':'2','plan_sent':'0','plan_end':'0','trace_aborts':'1','trace_commits':'770','fault_context_valid':'1','sink_trace_ack_valid':'1','sink_trace_mismatch_hex':'01','sink_window_flags':'3','sink_window_retired':'18876','trace_generation':'858','profile_last_display_tick':'3000','sink_trace_request_hex':'03001100030300005903e10551000000'}
    for key,value in mutations.items():
        dst=a.out/key;dst.mkdir()
        for f in a.raw.glob('*.txt'):shutil.copy2(f,dst/f.name)
        f=dst/'nes-game-last-mmc509.txt';s,count=re.subn(r'^'+key+r'=.*$',key+'='+value,f.read_text(),flags=re.M);assert count==1;f.write_text(s)
        try:analyse(dst,509)
        except AssertionError:pass
        else:raise AssertionError('Accepted invalid signature '+key)
    r=dict(passed=True,firmware_SHA256=firmware,scope=__doc__,cases=rows,negative_signatures=len(mutations),physical_instant_replayed=False)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(r))
