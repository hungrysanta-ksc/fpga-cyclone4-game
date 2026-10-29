# SPDX-License-Identifier: MIT
"""Linked485 M4 plan/window/bulk ownership guards with an independent endpoint.

Endpoint models descriptor production and delayed consumption/ACK. Instruction
counts are not hardware time; no physical IRQ/ROM/VBlank proof in this test.
"""
import argparse
import json
from pathlib import Path
import struct
from check_nes_game478 import Machine, ELFFile, crc, sha
from unicorn import UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_PC, UC_ARM_REG_LR


class Endpoint:
    def __init__(self, mode='normal'):
        self.mode=mode;self.accepted=self.sent=self.retired=0;self.calls=[];self.jobs=[]
        self.pending=[];self.last=bytes(12);self.token=0;self.end=False;self.bulk=0
        self.stale=None;self.stale_reads=0;self.stopped=False;self.plans=[];self.rearmed=False;self.generation=907
    def advance(self, clock):
        while self.pending and self.pending[0][0]<=clock:
            _,b=self.pending.pop(0)
            assert b[0]==7
            assert int.from_bytes(b[16:20],'little')==self.jobs[0][3]
            self.stale=self.descriptor();self.stale_reads=2
            self.jobs.pop(0);self.retired+=1
            self.last=bytes([0,7])+b[2:10]+b'\x65\x9a'
    def descriptor(self):
        kind,slot,n,token=self.jobs[0]
        return bytes([1,kind])+struct.pack('<HHHI',n,slot,self.generation,token)
    def exchange(self, tx, clock):
        self.advance(clock);self.calls.append(tx.hex());op=tx[0]
        if op==0xe8:
            r=bytearray(20);r[1:3]=b'\xd7\x04';r[4:6]=self.accepted.to_bytes(2,'big')
            d=None
            if self.stale_reads:d=self.stale;self.stale_reads-=1
            elif self.jobs:d=self.descriptor()
            if d:
                if self.mode=='wrong_generation':d=d[:6]+b'\x01\x00'+d[8:]
                if self.mode=='same_token_mutation' and self.bulk:d=d[:2]+b'\x20\x00'+d[4:]
                if self.mode=='old_token' and self.bulk>=2:d=d[:8]+bytes(4)
                r[6:18]=d
            else:r[3]=2 if self.end else 1
            r[19]=crc(r[1:19],8,7,0)
            if self.mode=='bad_E8_CRC':r[19]^=1
            return bytes(r)
        if op==0xe9:
            n=int.from_bytes(tx[1:3],'little');assert len(tx)==n+8 and tx[-1]==0xa5
            assert crc(tx[:n+6],8,7,0)==tx[n+6] and crc(tx[4:4+n],16,0x1021,65535)==int.from_bytes(tx[n+4:n+6],'big')
            assert not self.jobs
            at=4;count=0
            while at<4+n:
                kind=tx[at]&3;assert tx[at]&0xfc==0x80
                gen=int.from_bytes(tx[at+1:at+3],'little');assert gen==self.generation
                if kind==3:self.end=True;at+=3
                else:
                    if kind==2:slot=0;tag=0;size=16;at+=3;kind=0
                    else:
                        slot=int.from_bytes(tx[at+3:at+5],'little');tag=int.from_bytes(tx[at+5:at+7],'little')
                        size=32 if kind else 16;at+=8 if kind else 7
                    self.jobs.append((kind,slot*size,size,self.token));self.token+=1
                    self.plans.append((kind,slot,tag))
                count+=1
            assert at==4+n and count==tx[3]
            self.accepted+=1;return bytes(len(tx))
        if op==0xe1:
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            b=tx[1:-2];assert b[0]==7 and len(b)==20
            assert b[2:4]==self.sent.to_bytes(2,'little') and b[8:10]==struct.pack('<H',self.generation)
            assert int.from_bytes(b[16:20],'little')==self.jobs[0][3]
            assert self.sent-self.retired<4
            self.sent+=1;self.bulk+=1;self.pending.append((clock+12000,b))
            return bytes(len(tx))
        if op==0xe0:
            r=bytearray(20);r[1]=0xf7
            used=self.sent-self.retired;r[2]=int(used!=0)|(2 if self.retired else 0)|(4 if used==4 else 0)
            r[3:7]=struct.pack('>HH',self.sent,self.retired);r[7:19]=self.last
            if self.mode=='bad_ACK' and self.retired:r[9]^=1
            if self.mode=='bad_accepted' and self.sent:r[4]^=1
            r[19]=crc(r[1:19],8,7,0);return bytes(r)
        if op==0xea:
            assert self.end and not self.jobs and self.sent==self.retired
            assert tx[1:3]==struct.pack('<H',self.generation) and int.from_bytes(tx[3:5],'big')==self.accepted
            self.accepted=0;self.end=False;self.rearmed=True;return bytes(len(tx))
        raise AssertionError(tx.hex())


class ARM(Machine):
    def __init__(self, src, mode):
        self.endpoint=Endpoint(mode);self.guard485=0x0807ffc0
        super().__init__(src,bytes(128))
        self.u.mem_map(0xe0001000,0x1000)
        def dwt_read(u,access,address,size,value,user):
            if address==0xe0001004:u.mem_write(address,struct.pack('<I',self.instructions&0xffffffff))
        self.u.hook_add(UC_HOOK_MEM_READ,dwt_read,begin=0xe0001000,end=0xe0001fff)
        self.data_symbols={}
        with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
            elf=ELFFile(f)
            self.data_symbols={s.name:s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']=='STT_OBJECT'}
            for cu in elf.get_dwarf_info().iter_CUs():
                for d in cu.iter_DIEs():
                    if d.tag!='DW_TAG_structure_type' or not d.attributes.get('DW_AT_name') or not d.attributes.get('DW_AT_byte_size'):continue
                    name=d.attributes['DW_AT_name'].value.decode()
                    if name not in ['nes_plan200','nes_native_sink165','nes_sink_window184']:continue
                    item={'size':d.attributes['DW_AT_byte_size'].value}
                    for c in d.iter_children():
                        if c.tag!='DW_TAG_member':continue
                        off=c.attributes['DW_AT_data_member_location'].value
                        if not isinstance(off,int):
                            assert off[0]==0x23
                            value=shift=0
                            for b in off[1:]:
                                value|=(b&127)<<shift
                                if b<128:break
                                shift+=7
                            off=value
                        item[c.attributes['DW_AT_name'].value.decode()]=off
                    if name in self.layout:assert self.layout[name]==item
                    self.layout[name]=item
        self.p,self.w,self.s,self.q=0x20001000,0x20001800,0x20001c00,0x20002000
    def put(self,addr,kind,name,value,n):
        self.u.mem_write(addr+self.layout[kind][name],value.to_bytes(n,'little'))
    def get(self,addr,kind,name,n=1):
        return int.from_bytes(self.u.mem_read(addr+self.layout[kind][name],n),'little')
    def hook(self,u,at,size,user):
        if at==getattr(self,'syms',{}).get('nes_cost471_now',0):
            # Test clock for executing the real128us guard loop, not a hardware
            # cycle model or IRQ cost. The endpoint also uses instructions.
            u.reg_write(UC_ARM_REG_R0,self.instructions&0xffffffff)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if at==self.guard485:
            ok=not ((self.endpoint.mode=='STOP_after_E9' and self.endpoint.accepted) or
                    (self.endpoint.mode=='STOP_after_bulk' and self.endpoint.bulk))
            u.reg_write(UC_ARM_REG_R0,int(ok));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        if at==getattr(self,'spi',0):
            n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n))
            rx=self.endpoint.exchange(tx,self.instructions)
            u.mem_write(u.reg_read(UC_ARM_REG_R2),rx)
            ok=not(self.endpoint.mode=='ambiguous_E1' and tx[0]==0xe1)
            u.reg_write(UC_ARM_REG_R0,int(ok));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)
    def setup(self):
        assert self.call('nes_window184_init',[self.w,self.spi|1,self.guard485|1,0,256])==1
        self.put(self.w,'nes_sink_window184','wait',self.syms['nes_cost474_pause']|1,4)
        self.u.mem_write(self.data_symbols['nes_cost471_available'],struct.pack('<I',1))
        self.call('nes_sink165_reset',[self.s,self.syms['nes_window184_barrier']|1,self.w])
        for key,value,n in [('enqueue',self.syms['nes_window184_enqueue']|1,4),('serial',1,4),('generation',907,2),('state',1,1)]:
            self.put(self.s,'nes_native_sink165',key,value,n)
        for key,value in [('transfer',self.spi|1),('guard',self.guard485|1),('sink',self.s),('window',self.w),('poll_limit',256)]:
            self.put(self.p,'nes_plan200',key,value,4)
    def emit(self,kind,slot,tag):
        q=struct.pack('<HHHBB',self.endpoint.generation,slot,tag,kind,255 if kind==0 else 3 if kind==1 else 0)+(bytes(i//2 for i in range(16)) if kind<2 else bytes(16))+b'\xff'*16
        self.u.mem_write(self.q,q);return self.call('nes_plan200_emit',[self.p,self.q])


def run(src,mode):
    m=ARM(src,mode);m.setup();ok=True;prefix=[]
    for kind,slot,tag in [(2,0,0),(0,1,4),(0,2,7),(1,0,8),(1,1,9)]:
        if not m.emit(kind,slot,tag):ok=False;break
        prefix.append({'accepted_E9':m.endpoint.accepted,'bulk':m.endpoint.bulk,'retired':m.endpoint.retired})
    if ok:ok=bool(m.call('nes_plan200_finish',[m.p]))
    e=m.endpoint
    positive=['normal','normal_final_grant','normal_two_frames']
    if mode in positive:
        assert ok and e.sent==e.retired==5 and len(e.plans)==5 and not e.jobs
        assert prefix[0]['accepted_E9']==0 and prefix[1]['accepted_E9']==1 and any(q['bulk'] for q in prefix[2:])
        assert not m.get(m.s,'nes_native_sink165','displayed')
        assert not m.get(m.p,'nes_plan200','bulk_pending')
        if mode=='normal':
            # No final ACK has been presented. Retirement must fail before EA.
            assert m.call('nes_plan200_retire',[m.p])==0 and not e.rearmed
        else:
            # Explicit model grant, not an independently proven display ACK.
            for key,value,n in [('state',0,1),('displayed',1,1),('last_generation',907,2)]:m.put(m.s,'nes_native_sink165',key,value,n)
            assert m.call('nes_plan200_retire',[m.p])==1 and e.rearmed
            assert not m.get(m.p,'nes_plan200','early') and not m.get(m.p,'nes_plan200','bulk_valid')
            if mode=='normal_two_frames':
                # Exercise plan-owner rearm with live window counters/tokens.
                # Sink BEGIN/display permission is modeled here, not a new
                # independent full-display proof; actual BEGIN is in live RTL.
                e.generation=908;e.rearmed=False
                for key,value,n in [('generation',908,2),('state',1,1),('serial',2,4)]:m.put(m.s,'nes_native_sink165',key,value,n)
                assert m.emit(2,0,0) and m.emit(0,1,6) and m.call('nes_plan200_finish',[m.p])==1
                assert e.sent==e.retired==7 and not e.jobs
                for key,value,n in [('state',0,1),('displayed',1,1),('last_generation',908,2)]:m.put(m.s,'nes_native_sink165',key,value,n)
                assert m.call('nes_plan200_retire',[m.p])==1 and e.rearmed
    else:
        assert not ok,mode
        before=len(e.calls);assert m.emit(0,3,10)==0 and len(e.calls)==before
    return {'mode':mode,'expected_rejection':mode not in positive,'bulk_submissions':e.bulk,'accepted_E9':e.accepted,
            'during_emit':prefix,'retire_requires_final_grant':mode in positive,
            'E0':sum(bytes.fromhex(v)[0]==0xe0 for v in e.calls),'E8':sum(bytes.fromhex(v)[0]==0xe8 for v in e.calls),
            'plan_error':m.get(m.p,'nes_plan200','error'),'window_error':m.get(m.w,'nes_sink_window184','error'),
            'instructions':m.instructions,'SPI_bytes':sum(len(bytes.fromhex(v)) for v in e.calls)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    rows=[run(a.arm,n) for n in ['normal','normal_final_grant','normal_two_frames','bad_E8_CRC','wrong_generation','same_token_mutation','old_token','bad_ACK','bad_accepted','STOP_after_E9','STOP_after_bulk','ambiguous_E1']]
    r={'passed':True,'scope':__doc__,'firmware_SHA256':sha(a.arm/'obj-nes-100/firmware.stm'),'rows':rows,
       'actual_M4':True,'hardware_time':False,'full_IRQ_ROM_VBlank':False}
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps(r))
