"""Read-only map production/issuance and tile-owner trace on original694 ARM.

No byte, instruction, timestamp, queue credit or ROM grant is changed.
Run through the original694/689 linked ARM/SNES schedule and pin all clocks.
"""
import hashlib,runpy
from unittest.mock import patch
from test_nes_raw506_joint import Runtime
from check_nes_game478 import ELFFile
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_SP

TARGET={905,906,911,*range(951,958)}

def observe(original):
    def init(cpu,args,link):
        original(cpu,args,link)
        L=cpu.layout;video=cpu.video;at=video+L['nes_native_video165']['map']
        plan=cpu.rt+L['nes_native_runtime165']['plan'];sink=cpu.rt+L['nes_native_runtime165']['sink']
        window=cpu.rt+L['nes_native_runtime165']['transport']
        pending={};returns=set();serial=0;tracking=None;last=[0]*64;issued={};completed=[]
        def get(p,t,k,n=1):return int.from_bytes(cpu.u.mem_read(p+L[t][k],n),'little')
        def record(event,**kw):cpu.events.append(dict(event=event,generation=cpu.generation,clock=cpu.clock,**kw))
        def fields():
            d={k:get(plan,'nes_plan200',k,2 if k in ('sent','bytes','bulk_until') else 1)
               for k in ('sent','bytes','count','bulk_until','bulk_valid','bulk_pending','finished','ending','bank_history')}
            d['plan_bytes']=d.pop('bytes')
            d.update(map_next=get(sink,'nes_native_sink165','map_next'),pair=get(sink,'nes_native_sink165','map_pair683'),
                queued=(get(window,'nes_sink_window184','sent',2)-get(window,'nes_sink_window184','retired',2))&65535)
            return d
        def writes(u,access,address,size,value,user):
            if tracking!=cpu.generation or tracking not in TARGET:return
            lo=max(at,address);hi=min(at+4096,address+size)
            raw=value.to_bytes(size,'little')
            for pos in range(lo,hi):
                if pos-at in issued:assert raw[pos-address]==issued[pos-at],('map changed after issuance',tracking,pos-at)
                last[(pos-at)//64]=cpu.clock
        cpu.u.hook_add(UC_HOOK_MEM_WRITE,writes,begin=at,end=at+4095)
        def start(u,pc,size,user):
            nonlocal tracking,last,issued,completed
            if cpu.irq:return
            tracking=cpu.generation;last=[0]*64;issued={};completed=[]
            if tracking in TARGET:record('planner712',**fields())
        pc=cpu.syms['nes_native_video211_plan'];cpu.u.hook_add(UC_HOOK_CODE,start,begin=pc,end=pc)
        # Pinned source line is the common row549_done block (including reuse).
        # Observe its first instruction, not a guessed last store timestamp.
        source=(args.arm/'nes_planner211.c').read_text().splitlines()
        assert 'resident->finish_bg_row' in source[183]
        with (args.arm/'obj-nes-100/sd2snes.elf').open('rb') as f:
            dwarf=ELFFile(f).get_dwarf_info();pcs=[]
            for cu in dwarf.iter_CUs():
                if cu.get_top_DIE().attributes['DW_AT_name'].value.endswith(b'nes_planner211.c'):
                    lp=dwarf.line_program_for_CU(cu)
                    pcs=[x.state.address for x in lp.get_entries() if x.state and x.state.line==184]
        assert pcs
        def row_done(u,pc,size,user):
            if cpu.irq or tracking!=cpu.generation or tracking not in TARGET:return
            completed.append(cpu.clock)
            assert len(completed)<=32
            record('row_complete712',rows=len(completed),**fields())
        cpu.u.hook_add(UC_HOOK_CODE,row_done,begin=min(pcs),end=min(pcs))
        def freeze(u,pc,size,user):
            if cpu.irq or tracking!=cpu.generation or tracking not in TARGET:return
            if u.reg_read(UC_ARM_REG_R0)==video+L['nes_native_video165']['oam'] and u.reg_read(UC_ARM_REG_R2)==544:
                assert len(completed)==get(video,'nes_native_video165','groups')
                data=bytes(u.mem_read(at,4096));record('map_frozen712',last_write=last[:],row_complete=completed[:],row_PC=min(pcs),SHA256=hashlib.sha256(data).hexdigest(),**fields())
        pc=cpu.syms['memset'];cpu.u.hook_add(UC_HOOK_CODE,freeze,begin=pc,end=pc)
        def packet(u,pc,size,user):
            if cpu.irq or tracking!=cpu.generation or tracking not in TARGET:return
            op,sec,off=(u.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
            if op not in (2,24) or sec!=2:return
            sp=u.reg_read(UC_ARM_REG_SP);p,n=(int.from_bytes(u.mem_read(sp+i,4),'little') for i in (0,4))
            assert p==at+off and off%64==n%64==0 and 0<n<=192 and off+n<=4096
            data=bytes(u.mem_read(p,n))
            issued.update((off+i,b) for i,b in enumerate(data))
            record('map_packet712',offset=off,bytes=n,op=op,last_write=last[off//64:(off+n)//64],
                SHA256=hashlib.sha256(data).hexdigest(),**fields())
        pc=cpu.syms['packet_wire'];cpu.u.hook_add(UC_HOOK_CODE,packet,begin=pc,end=pc)
        def returned(u,pc,size,user):
            if cpu.irq:return
            key=(pc,u.reg_read(UC_ARM_REG_SP))
            for c in reversed(pending.pop(key,[])):
                assert c['g']==cpu.generation
                kw=dict(call=c['id'],name=c['name'],start=c['clock'],instructions=cpu.instructions-c['instructions'],result=u.reg_read(UC_ARM_REG_R0),**fields())
                if c['name']=='nes_plan527_map_credit':kw['ready']=bool(u.mem_read(c['arg1'],1)[0])
                record('return712',**kw)
        def enter(name):
            def entered(u,pc,size,user):
                nonlocal serial
                if cpu.irq or cpu.generation not in TARGET:return
                serial+=1;c=dict(id=serial,name=name,g=cpu.generation,clock=cpu.clock,instructions=cpu.instructions,arg1=u.reg_read(UC_ARM_REG_R1))
                record('call712',call=serial,name=name,arg1=c['arg1'],**fields())
                ret=u.reg_read(UC_ARM_REG_LR)&~1;pending.setdefault((ret,u.reg_read(UC_ARM_REG_SP)),[]).append(c)
                if ret not in returns:returns.add(ret);u.hook_add(UC_HOOK_CODE,returned,begin=ret,end=ret)
            return entered
        for name in ('map527','nes_sink527_early','nes_plan527_map_credit','offer527'):
            pc=cpu.syms[name];cpu.u.hook_add(UC_HOOK_CODE,enter(name),begin=pc,end=pc)
    return init

if __name__=='__main__':
    with patch.object(Runtime,'__init__',observe(Runtime.__init__)):
        runpy.run_module('test_nes_longrun694',run_name='__main__')
