# SPDX-License-Identifier: MIT
"""506 real linked M4 runtime /489 CPU rendezvous with explicit hardware models.

SPI wire, finite queues and ROM qualified windows share Mesen master time.
Unicorn instruction CPI and ROM safe-slot density are sensitivity parameters,
not measured cycles or an execution of the NES/PSRAM RTL. Fixed captures and
tile bytes are replayed; outer SD/menu/controller hardware is not emulated.
"""
import argparse,json,math,os,re,shutil,struct,subprocess,time
from pathlib import Path
from check_nes_game478 import Machine,encode as old_encode,crc,sha,ELFFile
from check_nes_supply485_arm import ARM
from check_nes_hardware494_termination import member_offset
from nes_raw506 import encode
from test_nes_output489_snes import LUA
from unicorn import UC_HOOK_MEM_READ
from unicorn.arm_const import *

MASTER=21477272
PERIOD=341*262*4
ARM_HZ=84000000

def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def lua_rpc(a):
    s=replace(LUA,"local bundle=file('requests.bin');local pos=1",'local tilePayload={};local lastAck=string.rep(string.char(0),12);local consumed={};local retiredEvents={};local rpc;local sourceRelease={}\nlocal bundle=\'\';local pos=1')
    start=s.index('for i=1,TOTAL do local n=')
    end=s.index('local function rd',start)
    s=s[:start]+s[end:]
    start=s.index('local function fill()');end=s.index('local function pb',start)
    s=s[:start]+s[end:]
    s=replace(s,'fill();local st=emu.getState()\n if st.masterClock<ready[index]then return end',"local st=emu.getState()\n if not requests[index]then return end")
    s=replace(s,"tile=file(string.format('tile-%04d.bin',index))",'tile=tilePayload[index]')
    s=replace(s,"for i=1,4 do assert(token[i]==pb(15+i),'receipt token')end", "for i=1,4 do assert(token[i]==pb(15+i),'receipt token')end\n  consumed[#consumed+1]={pw(16)+65536*pw(18),emu.getState().masterClock}")
    s=replace(s,'retired=index;retiredAt[index]=st.masterClock;', 'lastAck=string.char(table.unpack(ack));retiredEvents[#retiredEvents+1]={index,st.masterClock,lastAck};retired=index;retiredAt[index]=st.masterClock;')
    # Synchronize at CPU instructions AND DMA transfers; instruction-only
    # callbacks would hide an entire DMA burst inside one rendezvous.
    s=replace(s,'if a==0x6000 then if not firstPoll', 'if a==0x6000 then rpc();if not firstPoll')
    s=replace(s,'if a==0x2118 or a==0x2119 or a==0x2122 or a==0x2104 then', 'if a==0x2118 or a==0x2119 or a==0x2122 or a==0x2104 then\n  rpc()')
    start=s.index('emu.addMemoryCallback(function(a,v)\n if a==0x6000')
    body=r'''
local sequence=0;local target=0;local operation='SYNC';local args={};local finished=false
local startup=assert(io.open(ROOT..'/lua-started.txt','w'));startup:write('started');startup:close()
local function hex(b)return (b:gsub('.',function(c)return string.format('%02x',c:byte())end))end
local function unhex(b)return (b:gsub('..',function(c)return string.char(tonumber(c,16))end))end
local function nextCommand()
 sequence=sequence+1;local deadline=os.time()+90
 while true do
  local f=io.open(ROOT..'/command-'..sequence..'.txt','r')
  if f then
   target=tonumber(f:read('*l'));operation=f:read('*l');args={}
   for line in f:lines()do args[#args+1]=line end;f:close();return
  end
  assert(os.time()<deadline,'ARM RPC timeout '..sequence)
 end
end
nextCommand()
rpc=function()
 if finished then return end
 local now=emu.getState().masterClock
 while now>=target do
  if operation=='PUSH'then
   assert(sent-retired<4,'queue overflow');sent=sent+1
   requests[sent]=unhex(args[1]);tilePayload[sent]=unhex(args[2]or'')
   local g=requests[sent]:byte(9)+256*requests[sent]:byte(10)
   frames[sent]=g-905;frameRelease[g-905]=sourceRelease[g]or target
   if requests[sent]:byte(1)==3 then sealIndex[g-905]=sent end
  elseif operation=='BEGIN'then sourceRelease[tonumber(args[1])]=target
  elseif operation=='FINISH'then TOTAL=sent;finished=true
  else assert(operation=='SYNC','unknown operation')end
  local f=assert(io.open(ROOT..'/reply.tmp','w'))
  f:write(string.format('%d\n%d\n%s\n',now,retired,hex(lastAck)))
  for _,c in ipairs(consumed)do f:write(string.format('%d:%d;',c[1],c[2]))end
  f:write('\n')
  for _,e in ipairs(retiredEvents)do f:write(string.format('%d:%d:%s;',e[1],e[2],hex(e[3])))end
  f:write('\n');f:close();consumed={};retiredEvents={}
  assert(os.rename(ROOT..'/reply.tmp',ROOT..'/reply-'..sequence..'.txt'))
  if finished then return end
  nextCommand();now=emu.getState().masterClock
 end
end
emu.addMemoryCallback(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)
emu.addEventCallback(function()
 if sequence==1 then local s=emu.getState();local f=assert(io.open(ROOT..'/startup-clock.txt','w'));f:write(s.masterClock..' '..s.frameCount);f:close()end
end,emu.eventType.endFrame)
'''
    s=s[:start]+body+s[start:]
    s=s.replace("assert(st.frameCount<360,", "assert(st.frameCount<1200,")
    vals={'ROOT':json.dumps(str(a.out).replace('\\','/')),'MODE':"'normal'",'COMPACT':'true','TOTAL':'1000000','SCHEDULE':"'causal'",'POISON':'true','FAULT':'905','START':'0','FRAMES':str(a.frames)}
    for k,v in vals.items():s=s.replace('@'+k+'@',v)
    assert not re.search(r'@[A-Z]+@',s)
    (a.out/'capture.lua').write_text(s,encoding='utf8',newline='\n')

def wire_plan(q):
    gen,slot,tag,kind,mask=struct.unpack_from('<HHHBB',q)
    rows=q[8:24];alt=struct.unpack_from('<8H',q,24)
    if kind>=2:return bytes([128|kind])+struct.pack('<H',gen)
    if rows==bytes(i//2 for i in range(16)) and all(x==65535 for x in alt):
        return bytes([128|kind])+struct.pack('<HHH',gen,slot,tag)+(bytes([mask])if kind==1 else b'')
    altmask=sum((x!=65535)<<i for i,x in enumerate(alt));bits=sum(x<<(i*3)for i,x in enumerate(rows))
    return bytes([kind,altmask])+struct.pack('<HHH',gen,slot,tag)+bytes([mask])+bits.to_bytes(6,'little')+b'\1'+b''.join(struct.pack('<H',x)for x in alt if x!=65535)

class Link:
    def __init__(self,a):
        self.a=a;self.sequence=0;self.retired=0;self.last=bytes(12);self.sent=0
        self.jobs=[];self.open=None;self.flight=None;self.todo=[];self.plan_at=0
        self.token=0;self.accepted=0;self.end=False;self.producer_clock=0;self.calls=[]
        self.generation=905;self.tilebytes={};self.max_banks=0;self.rom_reads=0;self.max_rounding=0;self.future=[]
        self.plansets={}
        for g in range(905,905+a.frames):
            self.plansets[g]=[bytes.fromhex(q)for _,q in json.loads((a.plans/f'frame{g}/plans.json').read_text())]
            shutil.copyfile(a.fixture/f'expected-{g}.bin',a.out/f'expected-{g}.bin')
        blob=(a.fixture/'requests.bin').read_bytes();at=0;index=0
        while at<len(blob):
            n=struct.unpack_from('<H',blob,at)[0];b=blob[at+2:at+2+n];at+=n+2;index+=1
            if b[0]!=7:continue
            g=struct.unpack_from('<H',b,8)[0];slot=struct.unpack_from('<H',b,10)[0]
            payload=(a.fixture/f'tile-{index:04d}.bin').read_bytes();size=32 if b[1]else 16
            for j in range(0,len(payload),size):self.tilebytes[g,b[1],slot+j]=payload[j:j+size]
        lua_rpc(a)
        shutil.copyfile(a.client/'sink165.sfc',a.out/'client.sfc')
        self.log=(a.out/'mesen.log').open('wb');env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet')
        self.process=subprocess.Popen([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.out/'client.sfc'),'--timeout=1800','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],stdout=self.log,stderr=subprocess.STDOUT,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    def rpc(self,t,operation='SYNC',*args):
        self.sequence+=1;seq=self.sequence;p=self.a.out/f'command-{seq}.txt'
        tmp=self.a.out/'command.tmp';tmp.write_text('\n'.join([str(math.ceil(t)),operation,*args])+'\n',encoding='ascii');tmp.replace(p)
        reply=self.a.out/f'reply-{seq}.txt';deadline=time.monotonic()+100
        while not reply.exists():
            if self.process.poll()is not None:raise AssertionError(('Mesen exited',self.process.returncode,self.a.out/'mesen.log'))
            assert time.monotonic()<deadline,('Mesen timeout',seq,t)
            time.sleep(.001)
        # Windows can briefly retain a sharing lock after the atomic rename.
        # Retry only access-denied, bounded by the same transaction deadline.
        while True:
            try:lines=reply.read_text().splitlines();break
            except PermissionError:
                if time.monotonic()>=deadline:raise
                time.sleep(.002)
        now=int(lines[0]);self.max_rounding=max(self.max_rounding,now-math.ceil(t))
        for item in (lines[3]if len(lines)>3 else '').split(';'):
            if not item:continue
            token,clock=map(int,item.split(':'));self.future.append((clock,0,token,None))
        for item in (lines[4]if len(lines)>4 else '').split(';'):
            if not item:continue
            index,clock,ack=item.split(':');self.future.append((int(clock),1,int(index),bytes.fromhex(ack)))
        self.future.sort()
        # Mesen may return after an atomic DMA operation. Do NOT stall ARM
        # until that future time or expose its future ACK. Enqueue at t while
        # SNES is busy; its next CPU read observes the packet only afterward.
        while self.future and self.future[0][0]<=t:
            clock,kind,index,ack=self.future.pop(0);self.advance(clock)
            if kind:
                assert index==self.retired+1;self.retired=index;self.last=ack
            else:
                assert self.jobs and self.jobs[0]['token']==index,('consume owner',index,self.jobs)
                self.jobs.pop(0);self.producer_clock=max(self.producer_clock,clock)
        self.advance(t)
        return t
    def next_rom(self,t):
        # Exact row242..259 qualification window; CPU-cache hit/core-safe
        # density is a parameter, NOT a trace of the NES core's requests.
        phase=self.a.rom_phase;t=math.ceil(t);frame=(t-phase)//PERIOD
        lo=phase+frame*PERIOD+242*341*4;hi=phase+frame*PERIOD+260*341*4
        t=max(t,lo);t=lo+math.ceil((t-lo)/self.a.rom_stride)*self.a.rom_stride
        if t>=hi:t=phase+(frame+1)*PERIOD+242*341*4
        return t+7
    def publish(self):
        assert self.open and len(self.jobs)<2
        self.open['token']=self.token;self.token+=1;self.jobs.append(self.open);self.open=None
        self.max_banks=max(self.max_banks,len(self.jobs))
    def advance(self,now):
        for _ in range(2000):
            if self.flight:
                q,payload,done=self.flight
                if done>now:return
                gen,slot,tag,kind,mask=struct.unpack_from('<HHHBB',q);kind=int(kind==1);slot*=len(payload)
                match=self.open and self.open['kind']==kind and self.open['slot']+len(self.open['data'])==slot and len(self.open['data'])+len(payload)<=2048
                if self.open and not match:self.publish()
                if not self.open:
                    if len(self.jobs)==2:return
                    self.open=dict(kind=kind,slot=slot,gen=gen,data=b'')
                self.open['data']+=payload;self.flight=None
                self.producer_clock=max(self.producer_clock,done)+math.ceil((2*len(payload)+8)*MASTER/ARM_HZ)
                self.max_banks=max(self.max_banks,len(self.jobs)+1)
            if not self.todo:return
            q,arrived=self.todo[0];gen,slot,tag,kind,mask=struct.unpack_from('<HHHBB',q)
            if arrived>now:return
            if kind==3:
                if self.open:self.publish()
                self.todo.pop(0);self.end=True;continue
            self.todo.pop(0);size=32 if kind==1 else 16
            payload=self.tilebytes[gen,int(kind==1),slot*size]
            t=max(arrived,self.producer_clock)
            if kind!=2:
                for _ in range(mask.bit_count()*2):t=self.next_rom(t);self.rom_reads+=1
            t+=size*4 # bounded interface/CDC allocation, not a measured RTL trace
            self.flight=(q,payload,t)
        raise AssertionError('producer event loop')
    def response(self,tx):
        r=bytearray(len(tx));op=tx[0]
        if op==0xe0:
            used=self.sent-self.retired;assert 0<=used<=4
            r[1]=0xf7;r[2]=int(used>0)|(2 if self.retired else 0)|(4 if used==4 else 0)
            r[3:7]=struct.pack('>HH',self.sent,self.retired);r[7:19]=self.last;r[19]=crc(r[1:19],8,7,0)
        elif op==0xe8:
            r[1:3]=b'\xd7\x04';r[4:6]=struct.pack('>H',self.accepted)
            r[3]=2 if self.end else int(not self.todo and not self.flight)
            if self.jobs:
                d=self.jobs[0];r[6:18]=b'\1'+bytes([d['kind']])+struct.pack('<HHHI',len(d['data']),d['slot'],d['gen'],d['token'])
            r[19]=crc(r[1:19],8,7,0)
        return bytes(r)
    def accept(self,tx,t):
        op=tx[0]
        if op==0xe1:
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            b=tx[1:-2];assert self.sent-self.retired<4
            payload=b''
            if b[0]==7:
                d=self.jobs[0];assert int.from_bytes(b[16:20],'little')==d['token']
                assert b[1]==d['kind'] and struct.unpack_from('<H',b,10)[0]==d['slot'] and struct.unpack_from('<H',b,14)[0]==len(d['data'])
                payload=d['data']
            self.sent+=1;t=self.rpc(t,'PUSH',b.hex(),payload.hex())
        elif op==0xe9:
            n=int.from_bytes(tx[1:3],'little');assert len(tx)==n+8 and tx[-1]==0xa5
            assert crc(tx[:n+6],8,7,0)==tx[n+6] and crc(tx[4:4+n],16,0x1021,65535)==int.from_bytes(tx[n+4:n+6],'big')
            assert not self.todo and not self.flight,('plan credit',len(self.todo),self.flight)
            body=tx[4:4+n];at=0;count=0
            while at<len(body):
                plans=self.plansets[self.generation]
                if self.plan_at<len(plans):q=plans[self.plan_at]
                else:q=struct.pack('<HHHBB',self.generation,0,0,3,0)+bytes(16)+b'\xff'*16
                b=wire_plan(q);assert body[at:at+len(b)]==b,('plan bytes',self.generation,self.plan_at,body[at:].hex(),b.hex())
                self.todo.append((q,t));at+=len(b);count+=1;self.plan_at+=1
            assert at==n and count==tx[3];self.accepted+=1;self.advance(t)
        elif op==0xea:
            assert self.end and not self.jobs and not self.open and not self.flight and not self.todo
            assert self.sent==self.retired and self.last[0]==1 and self.last[1]==3
            assert tx[1:3]==struct.pack('<H',self.generation) and int.from_bytes(tx[3:5],'big')==self.accepted
            assert self.plan_at==len(self.plansets[self.generation])+1
            self.generation+=1;self.plan_at=0;self.accepted=0;self.end=False
        return t

class Runtime(ARM):
    def __init__(self,a,link):
        self.live=False;self.a=a;self.link=link;self.irq=False;self.pending_irq=False
        super().__init__(a.arm,'normal')
        with (a.arm/'obj-nes-100/sd2snes.elf').open('rb')as f:
            elf=ELFFile(f)
            self.static_end=max(s['p_vaddr']+s['p_memsz']for s in elf.iter_segments()if s['p_type']=='PT_LOAD' and 0x20000000<=s['p_vaddr']<0x20020000)
            for cu in elf.get_dwarf_info().iter_CUs():
                for d in cu.iter_DIEs():
                    if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==b'nes_native_runtime165' and d.attributes.get('DW_AT_byte_size'):
                        self.layout['nes_native_runtime165']={'size':d.attributes['DW_AT_byte_size'].value,**{c.attributes['DW_AT_name'].value.decode():member_offset(c)for c in d.iter_children()if c.tag=='DW_TAG_member'}}
        at=(self.static_end+15)&~15
        for field,kind in [('state','nes_native165'),('video','nes_native_video165'),('resident','nes_resident211'),('rt','nes_native_runtime165')]:
            setattr(self,field,at);at=(at+self.layout[kind]['size']+7)&~7
        self.lut=at;self.workspace_end=at+128;assert self.workspace_end<0x2000fe00
        pal=struct.pack('<64H',*map(int,re.search(r'\{(.*?)\}',(a.arm/'nes_palette165.inc').read_text(),re.S)[1].split(',')))
        self.u.mem_write(self.lut,pal);self.u.mem_map(0x40000000,0x30000);self.u.mem_map(0x42000000,0x1000000)
        self.ticks_cb=0x0807ffa0;self.service_cb=0x0807ffb0
        self.clock=float(a.start);self.tick=math.floor(self.clock/(MASTER/100));self.next_irq=(self.tick+1)*MASTER/100
        self.u.mem_write(self.data_symbols['ticks'],struct.pack('<I',self.tick));self.irq_calls=0;self.irq_instructions=0;self.service_calls=0;self.min_sp=0x20010000
        self.max_irq_late=0;self.driver_extra={}
        if a.driver503:
            ops=json.loads(a.driver503.read_text())['runs'][0]['driver_ops_nested']
            for key in ['D0','D1','D2','D3','E0','E1','E8','E9','EA']:
                d=ops[key];self.driver_extra[int(key,16)]=max(0,(d['cycles']/ARM_HZ-d['bytes']*8/2625000)/d['calls'])*MASTER
        self.clock_before=self.clock;self.wire_B={};self.events=[];self.generation=905;self.start_token=0;self.packets=[];self.next_capture_ready=self.clock;self.live=True
        self.actual_service='native_service165' in self.syms
        self.observer_cost={}
        if a.driver503:
            ops=json.loads(a.driver503.read_text())['runs'][0]['driver_ops_nested']
            self.observer_cost={name:ops[op]['cycles']/ops[op]['calls']/ARM_HZ*MASTER for name,op in [('observe136','70'),('screen146','73')]}
        for name,value,n in [('native_first165',1,1),('native_observed165',self.tick,4)]:
            if name in self.data_symbols:self.u.mem_write(self.data_symbols[name],value.to_bytes(n,'little'))
        self.u.mem_write(self.data_symbols['nes_cost471_available'],struct.pack('<I',1))
        def dwt(u,access,address,size,value,user):
            if address==0xe0001004:u.mem_write(address,struct.pack('<I',int(self.clock*ARM_HZ/MASTER)&0xffffffff))
        self.u.hook_add(UC_HOOK_MEM_READ,dwt,begin=0xe0001004,end=0xe0001007)
        self.begin_input()
        assert self.call('nes_runtime165_begin',[self.rt,self.state,self.video,self.lut,self.spi|1,self.ticks_cb|1,self.service_cb|1,0,6000,self.resident,1,1])==1
    def begin_input(self):
        self.index=0;self.prepared=False
        if self.generation>=905+self.a.frames:return
        g=self.generation;geom=(self.a.data/f'frame{g}.geometry').read_bytes();raw=(self.a.data/f'frame{g}.raw').read_bytes()
        self.packets,_,_=(encode if self.a.candidate else old_encode)(geom,raw,g)
        if self.a.capture_gate and g>905:
            # Actual201 ownership releases capture on input COMMIT, while
            # its immutable ROM/display lease remains until final ACK/EA.
            self.source_ready=self.next_capture_ready
        else:self.source_ready=self.clock
        self.clock=self.link.rpc(self.clock,'BEGIN',str(g));self.events.append(dict(generation=g,event='source_begin',clock=self.clock,capture_ready=self.source_ready))
    def status(self):
        if self.live and self.clock<self.source_ready:
            b=bytearray(8);b[1]=0xd6;b[3:5]=self.start_token.to_bytes(2,'big');b[7]=crc(b[1:7],8,7,0);return bytes(b)
        return Machine.status(self)
    def hook(self,u,at,size,user):
        if not self.live:return Machine.hook(self,u,at,size,user)
        if at==self.end:u.emu_stop();return
        if not self.irq and self.clock>=self.next_irq:
            self.pending_irq=True;u.emu_stop();return
        self.instructions+=1;self.clock+=self.a.cpi*MASTER/ARM_HZ
        self.min_sp=min(self.min_sp,u.reg_read(UC_ARM_REG_SP));assert self.min_sp>=self.workspace_end,('ARM stack overlap',hex(self.min_sp),hex(self.workspace_end))
        def ret(v):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        if at==self.ticks_cb:ret(int.from_bytes(u.mem_read(self.data_symbols['ticks'],4),'little'));return
        if at==self.service_cb:
            self.service_calls+=1
            if self.actual_service:u.reg_write(UC_ARM_REG_PC,self.syms['native_service165']|1)
            else:ret(1)
            return
        if at==self.syms.get('nes_cf86_check094'):ret(1);return # healthy board GPIO/context boundary
        for name,op in [('observe136',0x70),('screen146',0x73)]:
            if at==self.syms.get(name):
                cost=self.observer_cost.get(name,8*8*MASTER/2625000)
                self.clock+=cost;self.wire_B[hex(op)]=self.wire_B.get(hex(op),0)+8
                self.events.append(dict(generation=self.generation,event='observer',opcode=hex(op),clock=self.clock))
                ret(1);return
        if at==self.syms.get('nes_native_video211_plan'):self.events.append(dict(generation=self.generation,event='planner_enter',clock=self.clock))
        if at!=self.spi:return
        n=u.reg_read(UC_ARM_REG_R3);tx=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),n));op=tx[0]
        self.clock=self.link.rpc(self.clock);start=self.clock
        if op==0xd0:rx=self.status()
        elif op==0xd1:
            b=self.packets[self.index];assert n==len(b)+3;rx=b'\0'+b+crc(b,16,0x1021,65535).to_bytes(2,'big')
        elif op in (0xd2,0xd3):rx=self.status()
        else:rx=self.link.response(tx)
        self.clock+=n*8*MASTER/2625000+self.driver_extra.get(op,self.a.spi_us*MASTER/1000000)
        self.clock=self.link.rpc(self.clock)
        if op==0xd2:
            assert int.from_bytes(tx[2:4],'big')==((self.start_token+self.index)&65535);self.index+=1
            if self.index==len(self.packets):
                start=(math.floor((self.clock-self.a.rom_phase)/PERIOD)+1)*PERIOD+self.a.rom_phase
                self.next_capture_ready=start+240*341*4
        elif op==0xd3:assert tx[4]==1;self.prepared=True
        elif op>=0xe0:self.clock=self.link.accept(tx,self.clock)
        self.wire_B[hex(op)]=self.wire_B.get(hex(op),0)+n
        self.events.append(dict(generation=self.generation,event='SPI',opcode=hex(op),packet_opcode=tx[1]if op==0xe1 else None,bytes=n,start=start,clock=self.clock))
        if op==0xea:
            self.start_token=(self.start_token+len(self.packets))&65535;self.generation+=1;self.begin_input()
        assert len(rx)==n;u.mem_write(u.reg_read(UC_ARM_REG_R2),rx);ret(1)
    def interrupt(self):
        self.pending_irq=False;self.irq=True;context=self.u.context_save();before=self.instructions
        self.max_irq_late=max(self.max_irq_late,self.clock-self.next_irq)
        self.clock+=24*MASTER/ARM_HZ # explicit exception entry/exit allocation
        self.u.reg_write(UC_ARM_REG_SP,(self.u.reg_read(UC_ARM_REG_SP)-64)&~7)
        self.u.reg_write(UC_ARM_REG_LR,self.end|1)
        self.u.emu_start(self.syms['SysTick_Handler']|1,self.end+2,count=100000)
        assert self.u.reg_read(UC_ARM_REG_PC)==self.end,'SysTick handler did not return'
        self.u.context_restore(context);self.irq=False;self.irq_calls+=1;self.irq_instructions+=self.instructions-before;self.next_irq+=MASTER/100
    def call(self,name,args):
        if not self.live:return Machine.call(self,name,args)
        stack=0x2000ff00
        for reg,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(reg,v)
        for i,v in enumerate(args[4:]):self.u.mem_write(stack+i*4,struct.pack('<I',v))
        self.u.reg_write(UC_ARM_REG_SP,stack);self.u.reg_write(UC_ARM_REG_LR,self.end|1);self.u.reg_write(UC_ARM_REG_XPSR,0x01000000);pc=self.syms[name]
        for _ in range(10000):
            self.u.emu_start(pc|1,self.end+2,count=30000000)
            if self.pending_irq:self.interrupt();pc=self.u.reg_read(UC_ARM_REG_PC);continue
            assert self.u.reg_read(UC_ARM_REG_PC)==self.end,(name,hex(self.u.reg_read(UC_ARM_REG_PC)))
            return self.u.reg_read(UC_ARM_REG_R0)
        raise AssertionError('runtime call watchdog')

def run(a):
    a.out.mkdir(parents=True,exist_ok=False);link=Link(a)
    try:
        m=Runtime(a,link);steps=0
        while m.generation<905+a.frames:
            before=m.generation
            ok=m.call('nes_runtime165_step',[m.rt])
            if not ok:
                detail={}
                for field,kind in [('plan','nes_plan200'),('sink','nes_native_sink165'),('transport','nes_sink_window184')]:
                    base=m.rt+m.layout['nes_native_runtime165'][field]
                    detail[field]=dict(bytes=bytes(m.u.mem_read(base,m.layout[kind]['size'])).hex(),layout=m.layout[kind])
                (a.out/'fault.json').write_text(json.dumps(detail,indent=2)+'\n')
            assert ok==1,('runtime fault',m.generation,m.get(m.rt,'nes_native_runtime165','result'),m.state_value())
            steps+=1
            if m.generation!=before:
                print(json.dumps(dict(generation=m.generation,steps=steps,clock=m.clock,IRQ=m.irq_calls,source_state=m.state_value())),flush=True)
            assert steps<20000
        m.clock=link.rpc(m.clock,'FINISH');assert link.process.wait(timeout=120)==0
        r=json.loads((a.out/'result.json').read_text());r.update(scope=__doc__,firmware_SHA256=sha(a.arm/'obj-nes-100/firmware.stm'),client_SHA256=sha(a.client/'sink165.sfc'),candidate=a.candidate,parameters=dict(CPI=a.cpi,SPI_extra_us=a.spi_us,ROM_safe_slot_stride=a.rom_stride,ROM_phase=a.rom_phase,start=a.start,capture_gate=a.capture_gate),ARM_instructions=m.instructions,SysTick_calls=m.irq_calls,SysTick_instructions=m.irq_instructions,outer_service_stub_calls=m.service_calls,wire_B=m.wire_B,ROM_read_allocations=link.rom_reads,max_bulk_banks=link.max_banks,max_rendezvous_rounding=link.max_rounding,workspace_end=hex(m.workspace_end),observed_stack_low=hex(m.min_sp),physical_timing=False,full_ROM_RTL=False,menu_hardware=False)
        r['parameters']['driver503_SHA256']=sha(a.driver503)if a.driver503 else None
        r['parameters']['driver_extra_us']={hex(k):v/MASTER*1e6 for k,v in m.driver_extra.items()}
        r['IRQ_boundary_lateness_masterclocks']=m.max_irq_late
        r['IRQ_limit']='Real SysTick code, dispatched at instruction/transport boundaries; driver mean already includes its original interrupts, so this is a conservative sensitivity, not exact overlapping MCU cycles.'
        r['atomic_DMA_overshoot_charged_to_ARM']=False;r['future_ACK_filtered']=True
        r['native_service_code_executed']=m.actual_service;r['capture_release']='input COMMIT;following capture overlaps old display lease'
        (a.out/'joint.json').write_text(json.dumps(r,indent=2)+'\n');(a.out/'events.json').write_text(json.dumps(m.events,indent=2)+'\n');print(json.dumps(r),flush=True)
    finally:
        if 'm' in locals():(a.out/'events.json').write_text(json.dumps(m.events,indent=2)+'\n')
        if link.process.poll()is None:link.process.terminate();link.process.wait(timeout=10)
        link.log.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['arm','data','fixture','plans','client','mesen','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--candidate',action='store_true');p.add_argument('--frames',type=int,default=12);p.add_argument('--cpi',type=float,default=1)
    p.add_argument('--capture-gate',action='store_true')
    p.add_argument('--driver503',type=Path)
    p.add_argument('--spi-us',type=float,default=0);p.add_argument('--rom-stride',type=int,default=48);p.add_argument('--rom-phase',type=int,default=0);p.add_argument('--start',type=int,default=3000000)
    a=p.parse_args();a.out=a.out.resolve();assert a.rom_stride>=12 and a.rom_stride%12==0
    run(a)
