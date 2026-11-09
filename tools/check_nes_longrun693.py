"""Linked M4 long-session guards, real status decode, and rolling statistics."""
import argparse,json,struct
from pathlib import Path
from check_nes_longrun692 import Clock
from elftools.elf.elffile import ELFFile
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR,sha,crc
from test_nes_raw506_joint import member_offset
from unicorn import UC_HOOK_CODE

class Probe(Clock):
    def __init__(self,src,now=0):
        self.board=False;self.fault=False;self.stage=6;self.bad=False;self.calls=[];self.status_override=None;self.exit_on_status=False
        super().__init__(src,now)
        with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
            e=ELFFile(f);self.data={s.name:s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']=='STT_OBJECT'}
            for cu in e.get_dwarf_info().iter_CUs():
                for d in cu.iter_DIEs():
                    if d.tag!='DW_TAG_structure_type' or not d.attributes.get('DW_AT_name') or not d.attributes.get('DW_AT_byte_size'):continue
                    n=d.attributes['DW_AT_name'].value.decode()
                    if n not in ('nes_budget210','nes_run136_report','nes_sink_window184'):continue
                    self.layout[n]={'size':d.attributes['DW_AT_byte_size'].value,**{c.attributes['DW_AT_name'].value.decode():member_offset(c) for c in d.iter_children() if c.tag=='DW_TAG_member'}}
        self.rt=self.data['native_runtime165'];self.u.mem_write(self.rt,bytes(self.layout['nes_native_runtime165']['size']))
        assert self.call('nes_runtime165_begin',[self.rt,self.state,self.video,self.lut,self.spi|1,self.ticks|1,self.service|1,0,0,self.resident,1,1])
    def ret(self,u,v):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(self,u,at,size,user):
        if at==getattr(self,'spi',0) and u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0]==0xe0:
            b=bytearray(self.status_override or bytes(20));b[1]=0xf7;b[19]=crc(b[1:19],8,7,0)
            if self.exit_on_status:
                self.stage=126;self.now=100;u.mem_write(self.data['ticks'],struct.pack('<I',100));self.calls.append(0xe0)
            u.mem_write(u.reg_read(UC_ARM_REG_R2),bytes(b));self.ret(u,1);return
        if self.board:
            if at==self.syms.get('getticks',-1):self.ret(u,self.now);return
            if at==self.syms['nes_cf86_check094']:self.ret(u,int(not self.fault));return
            if at==self.syms['nes_cf86_fail094']:self.calls.append('fail');self.ret(u,0);return
            if at==self.syms['nes_rom_spi_transfer']:
                op=u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0];self.calls.append(op)
                assert op in (0x70,0x73)
                b=bytes([0,0xe5,0,0,0,0,0,10]) if op==0x70 else bytes([0,0xe6,self.stage,0xa9,0,0,1,2 if self.bad else 3])
                u.mem_write(u.reg_read(UC_ARM_REG_R2),b);self.ret(u,1);return
        super().hook(u,at,size,user)

def run(src):
    rows=[]
    for name,now,watch,steps,result in (
        ('past60',6001,6000,4194304,0),('one_hour_idle_injected',360000,0,4194304,0),
        ('tick_wrap',4,0xfffffff0,4194304,0),('no_frame499',499,498,0,0),
        ('no_frame500_allowed',500,499,0,0),('stopped_tick',0,0,4194304,6)):
        m=Probe(src)
        m.now=now
        for k,v in [('limit',watch),('steps',steps)]:m.put(m.rt,'nes_native_runtime165',k,v,4)
        ok=m.call('nes_runtime165_step',[m.rt]);actual=m.get(m.rt,'nes_native_runtime165','result')
        assert actual==result and bool(ok)==(result==0),(name,actual,ok)
        assert m.ops==([0xd0] if not result else [])
        rows.append(dict(case=name,result=actual,ops=m.ops,passed=True))
    for name,stage,bad,fault,result in [('normal',6,False,False,0),('user',126,False,False,8),('bad_status',126,True,False,2),('fault_wins',126,False,True,2)]:
        m=Probe(src);m.now=10;m.board=True;m.stage=stage;m.bad=bad;m.fault=fault
        m.u.mem_write(m.data['ticks'],struct.pack('<I',m.now))
        m.put(m.rt,'nes_native_runtime165','service',m.syms['native_service165']|1,4)
        # Abort must revoke prior resident/certification ownership.
        m.put(m.resident,'nes_resident211','open',1,1)
        ok=m.call('nes_runtime165_step',[m.rt]);actual=m.get(m.rt,'nes_native_runtime165','result')
        assert actual==result and bool(ok)==(result==0),(name,ok,actual,m.calls)
        if result:
            assert not m.get(m.resident,'nes_resident211','open') and not m.ops
            count=len(m.calls);assert not m.call('nes_runtime165_step',[m.rt]) and len(m.calls)==count
        if fault:assert not m.calls
        if bad:assert m.calls[-1]=='fail'
        rows.append(dict(case=name,result=actual,board_ops=m.calls,passed=True))
    m=Probe(src);addr=m.data['nes_budget210'];kind='nes_budget210';stats=[]
    for elapsed in (500,3999,4000,5499,5500,5999,6000,360000):
        m.call('nes_budget210_frame',[elapsed]);m.call('nes_budget210_time',[1,2]);m.call('nes_budget210_display',[elapsed,m.video])
        stats.append(dict(elapsed=elapsed,epoch=m.get(addr,kind,'epoch693',4),bin=m.get(addr,kind,'bin')))
    assert [x['bin'] for x in stats]==[1,7,8,10,11,11,0,0]
    assert [x['epoch'] for x in stats][-2:]==[6000,360000]
    counts=struct.unpack('<II',m.u.mem_read(addr+m.layout[kind]['displayed_window'],8));assert counts==(2,2)
    # Clock wrap cannot reopen the first-run comparison windows.
    m.put(addr,kind,'epoch693',0xfffffff0,4);m.call('nes_budget210_frame',[4]);m.call('nes_budget210_display',[4,m.video])
    assert struct.unpack('<II',m.u.mem_read(addr+m.layout[kind]['displayed_window'],8))==counts
    m.put(addr,kind,'serial',65535,2);m.call('nes_budget210_frame',[5]);assert m.get(addr,kind,'serial',2)==1
    n=m.call('nes_budget210_format',[0x20012000,6144]);assert 0<n<6144
    text=bytes(m.u.mem_read(0x20012000,n)).decode()
    assert 'budget_schema=693\n' in text and 'display_5_40_55=2,2\n' in text
    assert m.call('nes_budget210_format',[0x20012000,32])==0xffffffff
    # Real queue retirement arithmetic across65535, with the same latest-ACK
    # identity validation. The forged marker must not be accepted after wrap.
    for stale in (False,True):
        q=Probe(src);w=q.rt+q.layout['nes_native_runtime165']['transport'];k='nes_sink_window184'
        for field,v,size in [('sent',1,2),('retired',65534,2),('ever_sent',1,1)]:q.put(w,k,field,v,size)
        b=bytearray(20);b[2]=2;b[4]=b[6]=1;b[17]=0 if stale else 0x65;b[18]=0x9a;q.status_override=b
        ok=q.call('nes_window532_room',[w,0x20011ff0]);assert bool(ok)!=stale
        assert q.get(w,k,'error')==(8 if stale else 0)
        rows.append(dict(case='credit_wrap_stale' if stale else 'credit_wrap',passed=True))
    # Stop arrives after a real pending-SEAL status transaction. No retirement
    # or fabricated final display ACK is permitted by the exit path.
    q=Probe(src);q.board=True;q.now=10;q.u.mem_write(q.data['ticks'],struct.pack('<I',10))
    q.put(q.rt,'nes_native_runtime165','service',q.syms['native_service165']|1,4)
    w=q.rt+q.layout['nes_native_runtime165']['transport'];k='nes_sink_window184'
    q.put(w,k,'sent',1,2);q.put(w,k,'ever_sent',1,1);q.u.mem_write(w+q.layout[k]['last'],bytes([3])+bytes(9))
    q.put(q.resident,'nes_resident211','open',1,1)
    b=bytearray(20);b[2]=1;b[4]=1;q.status_override=b;q.exit_on_status=True
    assert not q.call('nes_window184_drain',[w,0x20011ff0])
    assert q.get(q.rt,'nes_native_runtime165','result')==8 and q.get(w,k,'retired',2)==0
    assert not q.get(q.resident,'nes_resident211','open') and not q.ops and q.calls.count(0xe0)==1
    rows.append(dict(case='user_during_pending_SEAL',passed=True,board_ops=q.calls,retired=0))
    for name,result,frames,error in [('user_before_first_display',8,0,0),('user_after_display',8,5,0),('service_fault_not_user',2,0,4)]:
        q=Probe(src)
        def terminal(u,at,size,user):
            if at==q.syms['nes_runtime165_step']:
                q.put(q.rt,'nes_native_runtime165','result',result,1);q.put(q.rt,'nes_native_runtime165','frames',frames,4);q.ret(u,0)
            else:q.ret(u,1)
        for fn in ('nes_runtime165_step','nes_runtime165_begin','nes_cost471_begin','nes_cost471_end'):
            q.u.hook_add(UC_HOOK_CODE,terminal,begin=q.syms[fn],end=q.syms[fn])
        entry,=[fn for fn in q.syms if fn.startswith('native_frames222')]
        q.call(entry,[1,1])
        assert q.get(q.data['nes_run136'],'nes_run136_report','first_error')==error,name
        assert q.get(q.rt,'nes_native_runtime165','resident',4)==0
        rows.append(dict(case=name,passed=True,error=error,scope='Actual terminal classification; frame loop and counters stubbed'))
    return dict(passed=True,firmware=sha(src/'obj-nes-100/firmware.stm'),cases=rows,statistics=stats,first_windows=counts,
        scope=__doc__+' Clock/status injected; no physical hour-long run or full joint schedule.',Flash_B=(src/'obj-nes-100/firmware.stm').stat().st_size)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=run(a.arm);a.out.write_text(json.dumps(r,indent=2)+'\n');print('PASS693 linked ARM guards/status/statistics',len(r['cases']))
