"""Run the linked ARM scroll entry with a completed map submission and controlled E0 replies."""
import argparse
import json
from pathlib import Path

from guard_nes_progress870 import Machine, offsets, crc, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR, UC_ARM_REG_PC


def check(src,progress_reads=1,rows=0xffffffff):
    m = Machine(src, bytes(128))
    sink, plan, window = 0x20012000, 0x20013000, 0x20014000
    guard, spi, queue = 0x0807ffc0, 0x0807ffc4, 0x0807ffc8
    layout = {sink:offsets(src,'nes_native_sink165'), plan:offsets(src,'nes_plan200'),
              window:offsets(src,'nes_sink_window184'), m.video:m.layout['nes_native_video165']}
    def put(base, field, val, size=1):
        m.u.mem_write(base+layout[base][field],val.to_bytes(size,'little'))
    last = bytes.fromhex('020211002e000000b603')
    def callback(u, pc, size, ctx):
        ret = 1
        if pc==guard:
            ret = case!='stop' and not (case=='stop_after_credit' and len(ops)>=2)
        elif pc==spi:
            assert bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),1))==b'\xe0'
            live = not ops or case=='timeout'
            ops.append('live' if live else 'returned')
            r = bytearray(20)
            r[1:7]=bytes((0xf7,1 if live else 2,0,12,0,11 if live else 12))
            if not live:
                r[7:19]=bytes((0,last[0]))+last[2:]+bytes.fromhex('659a')
                if case=='identity':
                    r[15]^=1
            if progress_reads>1:
                if case=='progress_live' or (case in ('normal','progress_identity','progress_crc') and len(ops)==3):
                    r[2]|=8
                    if case=='progress_identity':r[15]^=1
                    if not live:ops[-1]='progress'
            r[19]=crc(r[1:19],8,7,0)^int(case=='crc')
            if case=='progress_crc' and r[2]&8:r[19]^=1
            u.mem_write(u.reg_read(UC_ARM_REG_R2), bytes(r))
        else:
            b=bytes(u.mem_read(u.reg_read(UC_ARM_REG_R1),16))
            assert b[1]==5
            ops.append('scroll' if b[10:12]==b'\0\0' else 'padding')
        u.reg_write(UC_ARM_REG_R0,int(ret))
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    for pc in (guard,spi,queue):
        m.u.hook_add(UC_HOOK_CODE,callback,begin=pc,end=pc)
    result={}
    cases=('normal','timeout','stop','identity','crc')
    if progress_reads>1:
        cases+=('no_progress','stop_after_credit','progress_live','progress_identity','progress_crc')
    for case in cases:
        for base in (sink,plan,window):
            m.u.mem_write(base,bytes(512))
        for field,val in [('plan',plan),('enqueue',queue|1),('exchange',queue|1)]:
            put(sink,field,val,4)
        put(sink,'map_next',55)  # 32 + 23 accepted map rows
        put(plan,'window',window,4)
        put(plan,'bank_history',2)
        for field,val,width in [('guard',guard|1,4),('transfer',spi|1,4),('initialized',1,1),
                                ('ever_sent',1,1),('sent',12,2),('retired',11,2),('poll_limit',2,4)]:
            put(window,field,val,width)
        m.u.mem_write(window+layout[window]['last'],last)
        put(m.video,'patch_count',1)
        put(m.video,'hdma_size',21,2)
        put(m.video,'scroll_issued',0)
        ops=[]
        ok=m.call('nes_scroll810',[sink,m.video,rows,0x7fffff,1])
        assert ok==(case in ('normal','no_progress')) and bool(m.u.mem_read(m.video+layout[m.video]['scroll_issued'],1)[0])==bool(ok)
        if ok:
            expected=['live','returned']
            if case=='no_progress':expected+=['returned']*(progress_reads-1)
            elif progress_reads>1:expected+=['progress']
            assert ops==expected+['scroll','padding']
        else:
            assert 'scroll' not in ops and 'padding' not in ops
            assert m.u.mem_read(window+layout[window]['error'],1)[0]=={
                'timeout':7,'stop':2,'identity':8,'crc':4,'stop_after_credit':2,
                'progress_live':4,'progress_identity':8,'progress_crc':4}[case]
        result[case]=dict(accepted=bool(ok),events=ops)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('src',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--progress-reads',type=int,choices=(1,96),default=1)
    p.add_argument('--rows',type=lambda n:int(n,0),default=0xffffffff)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.src,a.progress_reads,a.rows),indent=2)+'\n')
