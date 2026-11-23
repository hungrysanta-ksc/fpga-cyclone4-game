"""Exercise saved-row identity and compare successful and fault report bytes on both links."""
import argparse
import json
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from check_nes_frame862_arm import TimedProbe
from nes_header950 import SOURCE, work


def test(mode):
    built=work(mode)/'link/src'
    q=TimedProbe(built)
    scratch=q.data['ptrcache']+16
    current=bytearray(16)
    ok=True
    calls=[]
    def spi(cpu,pc,size,_):
        tx=cpu.mem_read(cpu.reg_read(UC_ARM_REG_R1),2)
        assert tx==bytes((0x78,0)) and cpu.reg_read(UC_ARM_REG_R3)==16
        calls.append(1)
        cpu.mem_write(cpu.reg_read(UC_ARM_REG_R2),bytes(current))
        q.ret(cpu,int(ok))
    pc=q.syms['nes_native165_bulk']
    q.u.hook_add(UC_HOOK_CODE,spi,None,begin=pc,end=pc)
    # Reuse the wire ABI's row storage, never feed an expected identity to the FPGA.
    gen=0x3af7; token=0x1f452839
    def arm_row():
        row=bytearray(44)
        struct.pack_into('<H',row,2,gen)
        row[14]=3
        row[32]=1
        struct.pack_into('<I',row,40,token)
        q.u.mem_write(scratch,bytes(row))
        q.u.mem_write(q.data['pending950'],struct.pack('<I',scratch))
    for name,answer_gen,answer_token,chunks,success in (
            ('match',gen,token,1,True),('stale-generation',gen-1,token,1,True),
            ('stale-token',gen,token-1,1,True),('empty',gen,token,0,True),
            ('SPI-error',gen,token,1,False)):
        arm_row();current[:]=bytes(16)
        current[1]=0x95;struct.pack_into('<H',current,2,answer_gen)
        current[5]=chunks;struct.pack_into('<I',current,12,answer_token);ok=success
        before=len(calls);q.call('finish_header950',[]);q.call('finish_header950',[])
        assert len(calls)==before+1 and q.u.mem_read(scratch+14,1)[0]==(7 if name=='match' else 3)
        assert int.from_bytes(q.u.mem_read(scratch+40,4),'little')==token
    if mode in ('bound','release'):
        # A chunk with zero token must not authenticate an absent descriptor.
        arm_row();q.u.mem_write(scratch+32,bytes(12))
        current[5]=1;struct.pack_into('<I',current,12,0);ok=True
        q.call('finish_header950',[])
        assert q.u.mem_read(scratch+14,1)[0]==3
    arm_row();before=len(calls)
    # Cross the 60-second deadline while the displayed row still awaits D2.
    q.now=6000
    q.put(q.rt,'nes_native_runtime165','started',0,4)
    q.put(q.rt,'nes_native_runtime165','limit',6000,4)
    q.u.mem_write(q.data['ticks'],struct.pack('<I',q.now))
    q.put(q.rt,'nes_native_runtime165','service',q.syms['native_service165']|1,4)
    q.put(q.resident,'nes_resident211','open',1,1)
    assert not q.call('nes_runtime165_step',[q.rt]) and q.get(q.rt,'nes_native_runtime165','result')==1
    assert not q.get(q.resident,'nes_resident211','open') and len(calls)==before
    assert not q.call('nes_runtime165_step',[q.rt]) and len(calls)==before
    q.call('nes_budget210_reset',[]);q.call('finish_header950',[])
    assert len(calls)==before

    def trace_outputs(src):
        probe=TimedProbe(src)
        at=0x20012000
        records=[]
        for valid,ack,mask in ((0,0,0),(1,0,0xff),(1,1,0xa6)):
            probe.u.mem_write(probe.data['nes_sink_trace168'],bytes((valid,ack,mask,0))+bytes(range(28)))
            probe.u.mem_write(at,b'~'*256)
            length=probe.call('nes_sink168_format',[at,256])
            assert 0<length<255
            value=bytes(probe.u.mem_read(at,length+2))
            assert value[-2:]==b'\0~'
            for cap in (length,length+1):
                probe.u.mem_write(at,b'~'*256)
                used=probe.call('nes_sink168_format',[at,cap])
                if cap==length:
                    assert used==0xffffffff and bytes(probe.u.mem_read(at,256))==b'~'*256
                else:
                    assert used==length and bytes(probe.u.mem_read(at,length+2))==value
            records.append(value)
        return records
    assert trace_outputs(SOURCE/'link/src')==trace_outputs(built)
    result=dict(saved_generation_and_token=True,stale_generation=True,stale_token=True,
                empty_and_SPI_failure_rejected=True,one_shot=True,timed_exit_before_D2_no_probe=True,reset_discards_pending=True,
                unexpected_chunk_tested=mode in ('bound','release'),sink_report_vectors=3,short_and_exact_capacity=True)
    (work(mode)/'identity950.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode')
    test(p.parse_args().mode)
