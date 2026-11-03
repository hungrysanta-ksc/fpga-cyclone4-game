# SPDX-License-Identifier: MIT
"""Execute linked577/584 M4 transport boundaries, not a retimed game simulation.

Source is a four-packet producer, output a four-credit queue with delayed modeled
consumption. Real capture951/954 and selected actual plans are used. No real FPGA,
65816, ROM grants, IRQ or display timing is implied by the service clock.
"""
import argparse,collections,json,re,struct
from pathlib import Path
from check_nes_supply485_arm import ARM, Endpoint, ELFFile, crc, sha
from check_nes_game478 import Machine
from check_nes_hardware494_termination import member_offset
from nes_transfer512 import legacy_packets
from nes_progress583 import snapshot
from unicorn.arm_const import *

ROOT=Path(__file__).resolve().parents[1]

class Output(Endpoint):
    def __init__(self,delay):
        super().__init__();self.delay=delay;self.max_used=0;self.active_serial=0;self.active_gen=0
    def advance(self,t):
        while self.pending and self.pending[0][0]<=t:
            _,b=self.pending.pop(0)
            if b[0]==7:
                assert self.jobs and int.from_bytes(b[16:20],'little')==self.jobs[0][3]
                self.jobs.pop(0)
            self.retired+=1;self.last=bytes([int(b[0]==3),b[0]])+b[2:10]+b'\x65\x9a'
    def exchange(self,tx,t):
        self.advance(t)
        if tx[0]==0xe1:
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            b=tx[1:-2];assert int.from_bytes(b[2:4],'little')==self.sent and self.sent-self.retired<4
            if b[0]==7:
                assert self.jobs and int.from_bytes(b[16:20],'little')==self.jobs[0][3]
                assert not any(p[1][0]==7 for p in self.pending)
                self.bulk+=1
            if b[0]==1:self.active_serial=int.from_bytes(b[4:8],'little');self.active_gen=int.from_bytes(b[8:10],'little')
            self.sent+=1;self.max_used=max(self.max_used,self.sent-self.retired)
            due=max(t,self.pending[-1][0] if self.pending else t)+self.delay
            self.pending.append((due,b));return bytes(len(tx))
        if tx[0]==0xea:assert self.last[:2]==b'\x01\x03','EA without final ACK'
        return super().exchange(tx,t)

class Probe(ARM):
    def __init__(self,src,new,delay,fault='none'):
        self.active=False;self.new=new;self.fault=fault;self.inject=False;self.cancelled=False
        self.calls=[];self.cache_reads=collections.Counter();self.wire_clock=0;self.low_sp=0x2000ff00;self.source_delay=delay
        self.ep=Output(delay);self.snapseq=65530;self.release=None;self.confirm=0;self.body_lease=False
        super().__init__(src,'normal')
        with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
            e=ELFFile(f)
            end=max(s['p_vaddr']+s['p_memsz'] for s in e.iter_segments() if s['p_type']=='PT_LOAD' and 0x20000000<=s['p_vaddr']<0x20020000)
            for cu in e.get_dwarf_info().iter_CUs():
                for d in cu.iter_DIEs():
                    if d.tag!='DW_TAG_structure_type' or not d.attributes.get('DW_AT_name') or not d.attributes.get('DW_AT_byte_size'):continue
                    name=d.attributes['DW_AT_name'].value.decode()
                    if name in ('nes_native_runtime165','nes_ingress584'):
                        self.layout[name]={'size':d.attributes['DW_AT_byte_size'].value,**{c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'}}
        at=(end+15)&~15
        for name,kind in [('state','nes_native165'),('video','nes_native_video165'),('resident','nes_resident211'),('rt','nes_native_runtime165')]:
            setattr(self,name,at);at=(at+self.layout[kind]['size']+7)&~7
        self.lut=at;self.q=at+128;self.workspace_end=self.q+256;assert self.workspace_end<0x2000fe00
        self.u.mem_write(self.lut,bytes(128));self.ticks_cb=0x0807ffa0;self.service_cb=0x0807ffb0
        self.active=True
        assert self.call('nes_runtime165_begin',[self.rt,self.state,self.video,self.lut,self.spi|1,self.ticks_cb|1,self.service_cb|1,0,6000,self.resident,1,1])
        for name,field in [('p','plan'),('w','transport'),('s','sink')]:setattr(self,name,self.rt+self.layout['nes_native_runtime165'][field])
        self.fn=self.get(self.w,'nes_sink_window184','transfer',4)
        if new:self.ingress=self.rt+self.layout['nes_native_runtime165']['ingress584']

    @property
    def now(self):return self.instructions+self.wire_clock

    def call(self,name,args):
        if not self.active:return Machine.call(self,name,args)
        stack=0x2000ff00
        for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):self.u.reg_write(reg,v)
        for i,v in enumerate(args[4:]):self.u.mem_write(stack+4*i,struct.pack('<I',v))
        self.u.reg_write(UC_ARM_REG_SP,stack);self.u.reg_write(UC_ARM_REG_LR,self.end|1);self.u.reg_write(UC_ARM_REG_XPSR,0x01000000)
        self.u.emu_start(self.syms[name]|1,self.end+2,count=12000000)
        assert self.u.reg_read(UC_ARM_REG_PC)==self.end,(name,'watchdog')
        return self.u.reg_read(UC_ARM_REG_R0)

    def produce(self):
        end=len(self.packets) if self.prepared else len(self.packets)-1
        while self.produced<end and self.produced-self.index<4 and self.producer_at<=self.now:
            self.produced+=1;self.producer_at+=self.source_delay
            self.max_ring=max(self.max_ring,self.produced-self.index)
    def ready(self):self.produce();return self.index<self.produced
    def pop(self,tok):
        assert tok==((self.start_token+self.index)&65535) and self.ready()
        self.index+=1
        if self.index==len(self.packets):self.release=self.now
    def old_status(self):
        ready=self.ready();r=bytearray(8);r[1]=0xd6;r[2]=int(ready)|(2 if self.state_value()>=2 else 0)
        r[3:5]=((self.start_token+self.index)&65535).to_bytes(2,'big')
        if ready:r[5:7]=len(self.packets[self.index]).to_bytes(2,'big')
        r[7]=crc(r[1:7],8,7,0);return bytes(r)
    def input_exchange(self,tx):
        op=tx[0];n=len(tx)
        if op==0xd0:return self.old_status()
        if op==0xd1:
            assert self.ready();b=self.packets[self.index];assert n==len(b)+3
            return b'\0'+b+crc(b,16,0x1021,65535).to_bytes(2,'big')
        if op==0xd2:r=self.old_status();self.pop(int.from_bytes(tx[2:4],'big'));return r
        if op==0xd3:r=self.old_status();self.prepared=True;return r
        if op in (0xdc,0xde,0xdf):
            assert n==36 and crc(tx[:14],16,0x1021,65535)==int.from_bytes(tx[14:16],'little')
            assert int.from_bytes(tx[2:6],'little')==1 and int.from_bytes(tx[6:10],'little')==1
            if tx[1]:self.pop(int.from_bytes(tx[10:12],'little'))
            assert int.from_bytes(tx[12:14],'little')==((self.start_token+self.index)&65535)
            if op==0xde:
                assert self.index==len(self.packets)-1
                self.prepared=True;self.confirm+=1
            ready=self.ready();length=len(self.packets[self.index]) if ready else 0
            flags=int(ready)|(4 if self.prepared else 2 if self.index==len(self.packets)-1 else 0)
            if op==0xdf:assert self.index==len(self.packets);flags=0
            h=struct.pack('<BBHIIHH',0x84,flags,self.generation,1,1,(self.start_token+self.index)&65535,length)
            self.body_lease=ready
            return bytes(18)+h+crc(h,16,0x1021,65535).to_bytes(2,'little')
        assert op==0xdd and self.ready() and self.body_lease
        tok=(self.start_token+self.index)&65535;assert int.from_bytes(tx[1:3],'little')==tok
        b=tok.to_bytes(2,'little')+self.packets[self.index];assert n==len(b)+3
        self.body_lease=False
        return b'\0'+b+crc(b,16,0x1021,65535).to_bytes(2,'little')

    def output_exchange(self,tx):
        op=tx[0];self.ep.advance(self.now)
        if not self.new:return self.ep.exchange(tx,self.now)
        assert op in (0xe1,0xe9,0xea,0xec),'legacy output poll escaped'
        if op==0xea:return self.ep.exchange(tx,self.now)
        e0=self.ep.exchange(bytes([0xe0])+bytes(19),self.now)
        e8=self.ep.exchange(bytes([0xe8])+bytes(19),self.now)
        flags=(1 if self.ep.retired else 0)|(2 if e8[6] else 0)|(4 if e8[3]&1 else 0)|(8 if e8[3]&2 else 0)
        self.snapseq=(self.snapseq+1)&65535
        b=snapshot(serial=self.ep.active_serial,generation=self.ep.active_gen,sequence=self.snapseq,
                   accepted=self.ep.sent,retired=self.ep.retired,plan=self.ep.accepted,flags=flags,
                   ack=e0[7:19],bulk=e8[6:18])
        r=bytearray(len(tx));r[2:52]=b
        if self.inject and self.fault in ('snapshot_crc','snapshot_epoch','snapshot_generation','snapshot_sequence','future_credit','wrong_ACK'):
            b=bytearray(b)
            if self.fault=='snapshot_crc':b[-1]^=1
            else:
                offset={'snapshot_epoch':4,'snapshot_generation':12,'snapshot_sequence':14,'future_credit':16,'wrong_ACK':26}[self.fault]
                if self.fault=='snapshot_sequence':b[14:16]=((self.snapseq-1)&65535).to_bytes(2,'little')
                else:b[offset]^=1
                b[-2:]=crc(b[:-2],16,0x1021,65535).to_bytes(2,'little')
            r[2:52]=b
        if op in (0xe1,0xe9):
            real=(19+int.from_bytes(tx[13:15],'little')) if op==0xe1 else 8+int.from_bytes(tx[1:3],'little')
            assert not any(tx[real:]),'nonzero padded outbound bytes'
            self.ep.exchange(tx[:real],self.now)
        return bytes(r)

    def hook(self,u,at,size,user):
        if not self.active:return super().hook(u,at,size,user)
        def ret(v):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        if at==self.end:u.emu_stop();return
        self.low_sp=min(self.low_sp,u.reg_read(UC_ARM_REG_SP));assert self.low_sp>=self.workspace_end
        if self.new and at==self.syms.get('progress584'):
            owner=u.reg_read(UC_ARM_REG_R2)
            fresh=self.get(self.rt,'nes_native_runtime165','fresh584')
            self.cache_reads[f'owner{owner}_'+('hit' if fresh&(1<<owner) else 'miss')]+=1
        if at==self.ticks_cb:ret(int(self.now//420000));return
        if at==self.service_cb:ret(not self.cancelled);return
        if at==self.spi:
            n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n));op=tx[0]
            before=self.now
            # Mirror the unchanged board driver's actual count guard. This is
            # not an execution of GPIO/SPI/DMA or its clock-fault protection.
            if n>259:
                assert self.fault in ('driver_length255','driver_length256')
                self.calls.append(dict(op=hex(op),bytes=n,start=before,end=before,driver_rejected=True))
                ret(False);return
            ok=True
            if op<0xe0:
                if self.inject and self.fault=='early_COMMIT' and op==0xde:ok=False;r=bytes(n)
                else:r=self.input_exchange(tx)
                if self.inject and self.fault in ('source_crc','source_epoch','source_token'):
                    r=bytearray(r)
                    if self.fault=='source_crc' and op==0xdd:r[-1]^=1
                    if op==0xdc and self.fault!='source_crc':
                        r[22 if self.fault=='source_epoch' else 30]^=1
                        r[34:36]=crc(r[18:34],16,0x1021,65535).to_bytes(2,'little')
                    r=bytes(r)
            else:r=self.output_exchange(tx)
            self.wire_clock+=round(n*128)  #84MHz/CPI2,2.625MHz wire; not real cycles
            self.calls.append(dict(op=hex(op),bytes=n,start=before,end=self.now))
            if self.inject and ((self.fault=='STOP_after_header' and op==0xdc) or
                                (self.fault=='STOP_after_body' and op==0xdd) or
                                (self.fault=='STOP_after_E1' and op==0xe1) or
                                (self.fault=='STOP_after_E9' and op==0xe9)):
                self.cancelled=True
            if self.inject and self.fault=='ambiguous_E1' and op==0xe1:ok=False
            assert len(r)==n;u.mem_write(u.reg_read(UC_ARM_REG_R2),r);ret(ok);return
        super().hook(u,at,size,user)

    def source(self,data,g):
        self.generation=g;self.start_token=65520;self.index=self.produced=0;self.prepared=False;self.max_ring=0
        self.producer_at=self.now+self.source_delay;self.release=None;self.body_lease=False
        geom=(data/f'frame{g}.geometry').read_bytes();raw=(data/f'frame{g}.raw').read_bytes()
        self.packets,counts,arrays=legacy_packets(geom,raw,g)
        if self.fault.startswith('driver_length'):
            self.packets[0]=bytes(int(self.fault.removeprefix('driver_length')))
        if self.new:self.put(self.ingress,'nes_ingress584','next',self.start_token,2)
        self.inject=self.fault.startswith(('source','STOP_after_','early'))
        ok=True
        for i in range(2048):
            state=self.state_value()
            if state==4:break
            fn='nes_native165_prepare' if state==2 else 'nes_native165_poll'
            args=[self.state,1,self.fn,self.rt] if state==2 else [self.state,self.fn,self.rt]
            if self.new:args.append(self.ingress)
            if not self.call(fn,args):ok=False;break
        else:raise AssertionError('source watchdog')
        if ok:
            assert self.state_value()==4 and self.index==len(self.packets) and self.release is not None
            off=0
            for field,n,w,cap in zip(('maps','rows','objects','exceptions','raster','palette'),counts,(2,1,8,4,8,1),(1056,224,128,128,224,64)):
                assert bytes(self.u.mem_read(self.state+self.layout['nes_native165'][field],n*w))==geom[off:off+n*w],field
                off+=cap*w
            assert bytes(self.u.mem_read(self.state+self.layout['nes_native165']['raw_pixels'],len(raw)))==raw
        else:
            before=len(self.calls)
            args=[self.state,self.fn,self.rt]+([self.ingress] if self.new else [])
            assert not self.call('nes_native165_poll',args) and len(self.calls)==before
        return ok

    def output(self,plans,g):
        self.inject=False;self.ep.generation=g
        assert self.call('nes_resident211_begin',[self.resident,1,1,g,self.writer|1,0])
        assert self.call('nes_sink212_begin',[self.s,self.resident])
        selected=[bytes.fromhex(q) for _,q in json.loads((plans/f'frame{g}/plans.json').read_text())]
        prefix=[q for q in selected if q[6]!=1][:5]
        selected=prefix+[q for q in selected if q[6]==1][:7-len(prefix)]
        assert len(selected)==7
        self.inject=True;ok=True
        for q in selected:
            self.u.mem_write(self.q,q)
            if not self.call('nes_plan200_emit',[self.p,self.q]):ok=False;break
        if ok:ok=bool(self.call('nes_plan200_end',[self.p]))
        if ok:ok=bool(self.call('nes_plan200_progress',[self.p,1]))
        if ok and self.fault=='no_final_ACK':
            assert not self.call('nes_plan200_retire',[self.p]);assert not self.ep.rearmed
            return False
        if ok:
            assert not self.ep.jobs and self.ep.sent==self.ep.retired
            # Deliberate endpoint final-display grant, not a pixel/VBlank proof.
            b=bytearray(16);b[0]=3;b[2:4]=self.ep.sent.to_bytes(2,'little');b[4:8]=(1).to_bytes(4,'little');b[8:10]=g.to_bytes(2,'little')
            self.u.mem_write(self.q,bytes(b))
            ok=bool(self.call('nes_window184_barrier',[self.w,self.q,16,self.q+64]))
            if ok:
                for key,v,n in [('state',0,1),('displayed',1,1),('last_generation',g,2)]:self.put(self.s,'nes_native_sink165',key,v,n)
                ok=bool(self.call('nes_plan200_retire',[self.p]))
        if not ok:
            assert not self.ep.rearmed
            # Let the endpoint finish an already accepted transaction after the
            # caller has failed. Late completion must not cause another SPI/EA.
            self.ep.advance(self.now+10000000)
            before=len(self.calls);self.u.mem_write(self.q,selected[0]);assert not self.call('nes_plan200_emit',[self.p,self.q])
            assert len(self.calls)==before
        return ok

    def pressure(self,trace,g):
        self.ep.generation=g
        assert self.call('nes_resident211_begin',[self.resident,1,1,g,self.writer|1,0])
        assert self.call('nes_sink212_begin',[self.s,self.resident])
        packets=[]
        for line in trace.read_text().splitlines():
            b=bytes.fromhex(json.loads(line)[2])
            if int.from_bytes(b[8:10],'little')==g and b[0] in (2,4,5,8) and b[1]>=2:packets.append(b)
        assert len(packets)>=5
        self.ep.delay=1000000
        for i,raw in enumerate(packets[:5]):
            b=bytearray(raw);b[2:4]=self.ep.sent.to_bytes(2,'little');b[4:8]=(1).to_bytes(4,'little')
            self.u.mem_write(self.q,bytes(b))
            assert self.call('nes_window184_enqueue',[self.w,self.q,len(b)])
            if i==3:assert self.ep.sent-self.ep.retired==4
        assert self.ep.max_used==4 and self.ep.sent-self.ep.retired<=4
        assert self.call('nes_window184_drain',[self.w,self.q+192])
        assert self.ep.sent==self.ep.retired and not self.ep.rearmed

def result(m):
    return dict(calls=dict(collections.Counter(x['op'] for x in m.calls)),wire_B=sum(x['bytes'] for x in m.calls),
        instructions=m.instructions,observed_stack_B=0x2000ff00-m.low_sp,workspace_B=m.workspace_end-0x20000000,
        remaining_stack_gap_B=m.low_sp-m.workspace_end,source_ring_max=getattr(m,'max_ring',0),
        output_queue_max=m.ep.max_used,progress_cache_entry_counts=dict(m.cache_reads),
        final_ACK_model=m.ep.last[:2]==b'\x01\x03',EA=m.ep.rearmed)

def run(a):
    a.out.mkdir(parents=True,exist_ok=False);rows=[]
    evidence=json.loads((ROOT/'analysis/body581-verification.json').read_text())
    for g in (951,954):
        for ext in ('geometry','raw'):
            p=a.data/f'frame{g}.{ext}';assert sha(p)==evidence['inputs'][p.name]
        for delay in (128,12000):
            pair={}
            for label,src,new in [('577',a.base,False),('584',a.arm,True)]:
                m=Probe(src,new,delay);before=len(m.calls);assert m.source(a.data,g)
                source_result=result(m);source_calls=m.calls[before:]
                assert m.output(a.plans,g), (g,label,m.get(m.rt,'nes_native_runtime165','result'),m.get(m.p,'nes_plan200','error'),m.get(m.w,'nes_sink_window184','error'))
                pair[label]=dict(source=source_result,total=result(m),source_calls=len(source_calls),
                    plans=m.ep.plans,source_release_before_EA=m.release<next(c['start'] for c in m.calls if c['op']=='0xea'))
                (a.out/f'{g}-{delay}-{label}-calls.json').write_text(json.dumps(m.calls,indent=2)+'\n')
            assert pair['577']['plans']==pair['584']['plans']
            for x in pair.values():x.pop('plans')
            rows.append(dict(generation=g,modeled_service_delay=delay,comparison=pair))
    pressure=[]
    for label,src,new in [('577',a.base,False),('584',a.arm,True)]:
        m=Probe(src,new,128);assert m.source(a.data,951);m.pressure(a.trace,951)
        pressure.append(dict(build=label,**result(m)))
    faults=[]
    for fault in ('source_crc','source_epoch','source_token','STOP_after_header','STOP_after_body','early_COMMIT',
                  'snapshot_crc','snapshot_epoch','snapshot_generation','snapshot_sequence','future_credit',
                  'wrong_ACK','STOP_after_E9','STOP_after_E1','ambiguous_E1','no_final_ACK',
                  'driver_length255','driver_length256'):
        m=Probe(a.arm,True,12000,fault);ok=m.source(a.data,951)
        if ok:ok=m.output(a.plans,951)
        assert not ok,fault
        if fault.startswith('driver_length'):assert any(c.get('driver_rejected') for c in m.calls)
        faults.append(dict(fault=fault,rejected=True,**result(m)))
    report=dict(stage=584,passed=True,scope=__doc__,rows=rows,faults=faults,pressure=pressure,
        baseline_firmware_SHA256=sha(a.base/'obj-nes-100/firmware.stm'),firmware_SHA256=sha(a.arm/'obj-nes-100/firmware.stm'),
        baseline_firmware_B=(a.base/'obj-nes-100/firmware.stm').stat().st_size,firmware_B=(a.arm/'obj-nes-100/firmware.stm').stat().st_size,
        deployment_capacity_B=212992,checker_SHA256=sha(Path(__file__)),R3_selected=False,
        evidence=dict(trace_SHA256=sha(a.trace),plans={str(g):sha(a.plans/f'frame{g}/plans.json') for g in (951,954)}),
        limits=['Current577 record compression retained;583 row codec not integrated',
                'Seven selected real plans per capture, not full951/954 workload or two staging-slot RTL',
                'Consumption and final-display grant are endpoint models; no65816/VBlank/pixel proof',
                'No actual IRQ/ROM/CDC or source timing; delay units are deterministic service sensitivities',
                'Next-generation receive/COMMIT concurrency remains untested; source/input and display identities kept separate',
                'Board259B count guard mirrored, peripherals not executed; candidate255/256B payload needs260/261B and is rejected, so ABI is not generally compatible'])
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,rows=len(rows),faults=len(faults),firmware_B=report['firmware_B'])))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','arm','data','plans','trace','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
