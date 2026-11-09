"""Measure existing MMC690 elapsed/step guards before designing long-session mode.

Injected tick/step state exercises linked Cortex-M4 code. This is not a real
hour-long run and does not implement or deliver an unlimited-play build.
"""
import argparse,json
from pathlib import Path
from check_nes_idle676 import Receiver
from check_nes_game478 import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR,sha

class Clock(Receiver):
    def __init__(self,src,now):
        self.now=now
        super().__init__(src,'empty')
        self.u.mem_map(0xe0001000,0x1000)
        self.put(self.state,'nes_native165','state',0,1)
    def hook(self,u,at,size,user):
        if at==self.ticks:
            u.reg_write(UC_ARM_REG_R0,self.now)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
        super().hook(u,at,size,user)

def run(src):
    rows=[]
    for name,start,now,steps,limit,expected in (
        ('before60',0,5999,0,6000,0),('at60',0,6000,0,6000,1),
        ('after60',0,6001,0,6000,1),('one_hour_injected',0,360000,0,6000,1),
        ('tick_wrap_before_limit',0xfffffff0,4,0,6000,0),
        ('step_cap_even_with_large_time_limit',0,1,4194304,0x7fffffff,6),
        ('zero_limit_guard_is_immediate_deadline',0,1,0,0,1)):
        m=Clock(src,now)
        for k,v in [('started',start),('steps',steps),('limit',limit)]:m.put(m.rt,'nes_native_runtime165',k,v,4)
        ok=bool(m.call('nes_runtime165_step',[m.rt]))
        result=m.get(m.rt,'nes_native_runtime165','result')
        assert result==expected and ok==(expected==0),(name,ok,result,m.ops)
        assert m.ops==([0xd0] if expected==0 else []),(name,m.ops)
        rows.append(dict(case=name,passed=True,result=result,continued=ok,operations=m.ops))
    return dict(firmware=sha(src/'obj-nes-100/firmware.stm'),passed=True,cases=rows,
        scope=__doc__,unlimited_implemented=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();j=run(a.arm);a.out.write_text(json.dumps(j,indent=2)+'\n');print('PASS692',len(j['cases']),'existing guard boundary cases')
