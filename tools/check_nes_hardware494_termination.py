# SPDX-License-Identifier: MIT
"""Execute linked493 SEAL/window/runtime post-transfer deadline propagation.

Minimal manually admitted SEAL fixture; SPI ACK/ticks/service are modeled.
Not a replay of the physical final instant or a pixel/timing/IRQ proof.
"""
import argparse,json,re,shutil,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,ELFFile,sha,crc
from analyze_nes_supply485_hardware import analyse
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR

ROOT=Path(__file__).resolve().parents[1]
def member_offset(c):
    v=c.attributes['DW_AT_data_member_location'].value
    if isinstance(v,int):return v
    assert v[0]==0x23
    value=shift=0
    for b in v[1:]:
        value|=(b&127)<<shift
        if b<128:return value
        shift+=7
    raise AssertionError('Invalid ULEB member offset')
class SealDeadline(ARM):
    def __init__(self,src,mode):
        self.mode=mode;self.expired=False;self.accepted=0;self.last=None;self.seal_polls=0;self.calls=[]
        super().__init__(src,'normal');self.rt=0x20003000;self.ticks_cb=0x0807ffa0;self.service_cb=0x0807ffb0
        with (src/'obj-nes-100/sd2snes.elf').open('rb')as f:
            elf=ELFFile(f)
            for cu in elf.get_dwarf_info().iter_CUs():
                for d in cu.iter_DIEs():
                    if d.tag!='DW_TAG_structure_type' or not d.attributes.get('DW_AT_byte_size') or d.attributes.get('DW_AT_name',None) is None:continue
                    if d.attributes['DW_AT_name'].value!=b'nes_native_runtime165':continue
                    self.layout['nes_native_runtime165']={'size':d.attributes['DW_AT_byte_size'].value,**{c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children()if c.tag=='DW_TAG_member'}}
        assert self.rt+self.layout['nes_native_runtime165']['size']<self.state
        assert self.call('nes_runtime165_begin',[self.rt,self.state,self.video,self.lut,self.spi|1,self.ticks_cb|1,self.service_cb|1,0,10,self.resident,1,1])==1
        self.s=self.rt+self.layout['nes_native_runtime165']['sink'];self.w=self.rt+self.layout['nes_native_runtime165']['transport']
        for name,value,n in [('serial',1,4),('generation',907,2),('state',1,1)]:self.put(self.s,'nes_native_sink165',name,value,n)
        for name,value,n in [('serial',1,4),('generation',907,2),('open',1,1),('prepared',1,1)]:self.put(self.resident,'nes_resident211',name,value,n)
        for name,value,n in [('valid',1,1),('generation',907,2),('bg_count',1,2),('hdma_size',1,2),('display_mask',0x1e,1)]:self.put(self.video,'nes_native_video165',name,value,n)
    def hook(self,u,at,size,user):
        def ret(value):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        if at==getattr(self,'ticks_cb',0):ret(10 if self.expired else 0);return
        if at==getattr(self,'service_cb',0):ret(1);return
        if at==getattr(self,'spi',0):
            n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n));self.calls.append(tx.hex());rx=bytearray(n);ok=1
            if tx[0]==0xe1:
                self.accepted+=1;self.last=tx[1:-2]
            else:
                assert tx[0]==0xe0 and n==20
                pending=False
                if self.last and self.last[0]==3:
                    self.seal_polls+=1;pending=self.mode!='normal'
                    if self.seal_polls==2:
                        if self.mode=='deadline':self.expired=True
                        elif self.mode=='IO_fault':ok=0
                retired=self.accepted-int(pending)
                rx[1]=0xf7;rx[2]=(int(pending)|2)if self.last else 0
                rx[3:7]=struct.pack('>HH',self.accepted,retired)
                if self.last:rx[7:19]=bytes([int(self.last[0]==3),self.last[0]])+self.last[2:10]+b'\x65\x9a'
                rx[19]=crc(rx[1:19],8,7,0)
            u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(rx));ret(ok);return
        super().hook(u,at,size,user)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','raw','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    expected=json.loads((ROOT/'analysis/boot493-package.json').read_text())['firmware_SHA256']
    assert sha(a.arm/'obj-nes-100/firmware.stm')==expected
    rows=[]
    for mode in ['normal','deadline','IO_fault']:
        m=SealDeadline(a.arm,mode);ok=m.call('nes_sink212_seal',[m.s,m.video,m.resident])
        row={'mode':mode,'ok':ok,'runtime_result':m.get(m.rt,'nes_native_runtime165','result'),'window_error':m.get(m.w,'nes_sink_window184','error'),'sink_error':m.get(m.s,'nes_native_sink165','error'),'displayed':bool(m.get(m.s,'nes_native_sink165','displayed')),'resident_displayed':bool(m.get(m.resident,'nes_resident211','displayed')),'pending':m.get(m.w,'nes_sink_window184','sent',2)-m.get(m.w,'nes_sink_window184','retired',2),'flags':m.get(m.w,'nes_sink_window184','status_flags')}
        if mode=='normal':assert ok and row['displayed'] and row['resident_displayed'] and row['runtime_result']==row['window_error']==row['sink_error']==0
        else:
            assert not ok and row['runtime_result']==(1 if mode=='deadline'else 3) and row['window_error']==3 and row['sink_error']==2
            assert not row['displayed'] and not row['resident_displayed'] and row['pending']==1 and row['flags']==3
            before=len(m.calls);assert m.call('nes_sink212_seal',[m.s,m.video,m.resident])==0 and len(m.calls)==before
        rows.append(row)
    assert analyse(a.raw,493)['termination_class']=='deadline_during_SEAL_status_postguard_signature'
    negatives=[]
    cases=[('native_result','3'),('native_video_error','14'),('native_receiver_error','1'),('native_sink_error','3'),('sink_window_error','4'),('plan_error','2'),('plan_sent','0'),('plan_end','0'),('trace_aborts','1'),('trace_commits','575'),('fault_context_valid','1'),('sink_trace_ack_valid','1'),('sink_trace_request_hex','02001b00400200006e030000a8000000'),('sink_window_flags','2'),('sink_window_retired','14484'),('trace_generation','879')]
    for key,value in cases:
        d=a.out/key;d.mkdir()
        for q in a.raw.glob('*.txt'):shutil.copyfile(q,d/q.name)
        q=d/'nes-game-last-mmc493.txt';s=q.read_text();s,n=re.subn(rf'(?m)^{key}=.*$',f'{key}={value}',s);assert n==1;q.write_text(s)
        try:analyse(d,493)
        except AssertionError:negatives.append(key)
        else:raise AssertionError('Fault accepted:'+key)
    r={'passed':True,'scope':__doc__,'firmware_SHA256':expected,'rows':rows,'negative_log_cases':negatives,'physical_failure_instant_replayed':False}
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'rows':rows,'negative_cases':len(negatives)}))
