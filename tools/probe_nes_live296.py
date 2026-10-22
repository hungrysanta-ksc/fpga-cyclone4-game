# SPDX-License-Identifier: MIT
"""Actual BG-phase publication into retained refill/IRQ/tile ROM path."""
import inspect,shutil
import probe_nes_live289 as old
from nes_wait296 import prepare as native
from nes_bg295 import unbatch as unbatch295
from nes_close295 import apply as close295
from nes_joint296 import apply
from nes_bg293 import unbatch
from nes_delta231 import ROOT,sha,once


from unicorn.arm_const import UC_ARM_REG_LR
class ARM296(old.previous.ARM):
    def __init__(self,*args):
        self.service_events296=[];self.return296=None
        super().__init__(*args)
    def hook(self,uc,address,size,user):
        word=lambda n:int.from_bytes(uc.mem_read(self.symbols[n],4),'little')
        if self.return296==address:
            self.service_events296[-1].update(after_size=word('output_size285'),after_done=word('done296'),end_instruction=self.instructions)
            self.return296=None
        if address==(self.symbols['service296']&~1):
            state=bytes(uc.mem_read(self.symbols['state259'],4))
            self.service_events296.append(dict(instruction=self.instructions,before_size=word('output_size285'),before_done=word('done296'),
                sent=int.from_bytes(state[:2],'little'),retired=int.from_bytes(state[2:],'little'),plan_at=word('plan_at267'),plan_bytes=word('plan_bytes267')))
            self.return296=uc.reg_read(UC_ARM_REG_LR)&~1
        super().hook(uc,address,size,user)


def build_rom(d):
    ns=dict(old.__dict__);ns['native']=native
    exec(compile(inspect.getsource(old.build_rom),'build294','exec'),ns);ns['build_rom'](d)


def prepare(*args,**kwargs):
    src,pins=old.prepare(*args,**kwargs);d=args[0];close295(d);apply(d)
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,' task clear_output;', '''
 always @(posedge clk)if(!reset&&active263)begin
  if(planrom.pv&&planrom.pready)$fwrite(events261,"plan293,%0d,%0d,%0d,%0t\\n",f,planrom.kind,planrom.slot,$time);
  if(tv263&&tr263&&ti263==0)$fwrite(events261,"tile293,%0d,%0d,%0d,%0t\\n",f,tk263,ts263,$time);
 end
 always @(posedge host_clk)if(!reset&&active263)begin
  if(dut.flow.tile_consume||dut.flow.map_consume)$fwrite(events261,"consume293,%0d,%0d,%0d,%0t\\n",f,dut.flow.owner,dut.flow.chunk_token,$time);
 end
 task clear_output;''')
    p.write_text(s,encoding='utf-8',newline='\n')
    for n in ('nes_bg293.py','nes_bg294.py','nes_bg295.py','nes_stage290.py','nes_close295.py','probe_nes_live295.py','nes_wait296.py','nes_joint296.py','probe_nes_live296.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins


def worker(*args,**kwargs):
    s=inspect.getsource(old.previous.worker)
    s=once(s,'arm.uc.mem_write(0x20010000,blob)',"arm.uc.mem_write(0x20010000,b'\\xa5'*len(blob))")
    s=once(s,"assert actual==(d/f'plans{f-904}.bin').read_bytes(),('plans',f)","assert unbatch295(actual)==unbatch((d/f'plans{f-904}.bin').read_bytes()),('plan order293',f)\n        (d/f'actual-plans293-{f}.bin').write_bytes(actual)")
    s=once(s,'steps=[];prefills=0;last_size=0','steps=[];prefills=0;last_size=0;early_refills293=0')
    s=once(s,"if n!=last_size:call('prefill287');prefills+=1;last_size=n", "if n!=last_size:\n                call('prefill287');prefills+=1;last_size=n\n                if ok!=2:early_refills293+=1")
    s=once(s,'row=dict(frame=f,instructions=', 'row=dict(frame=f,early_refills=early_refills293,instructions=')
    s=once(s,"arm.call('seed287',[generation]);ep.checkpoint();", "arm.call('seed287',[generation]);call('start290',[f-904,generation]);ep.checkpoint();")
    s=once(s,"            ep.checkpoint()", "            call('tiles290',[0]);ep.checkpoint()")
    s=once(s,'start=len(ep.transfers);', 'start296=len(arm.service_events296);start=len(ep.transfers);')
    s=once(s,'row=dict(frame=f,', 'row=dict(service296=arm.service_events296[start296:],frame=f,')
    ns=dict(old.previous.__dict__);ns['ARM']=ARM296;ns['unbatch']=unbatch;ns['unbatch295']=unbatch295
    exec(compile(s,'worker294','exec'),ns);return ns['worker'](*args,**kwargs)


def main():
    ns=dict(old.previous.prior.__dict__)
    ns.update(prepare=prepare,build_rom=build_rom,worker=worker,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(old.previous.prior.main),'live294','exec'),ns);ns['main']()


if __name__=='__main__':main()
