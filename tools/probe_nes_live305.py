# SPDX-License-Identifier: MIT
"""ARM303 supply priority with active-record RTL305 and passive live IRQ/ROM diagnostics."""
import inspect,shutil
import probe_nes_live289 as old
from nes_arch300 import apply as arch300,observe as observe300
from nes_joint303 import native
from nes_record305 import apply as record305,observe as observe305
from nes_bg295 import unbatch as unbatch295
from nes_close295 import apply as close295
from nes_joint298 import apply as joint298,observe
from nes_bg293 import unbatch
from nes_delta231 import ROOT,sha,once


from unicorn.arm_const import UC_ARM_REG_LR
class ARM296(old.previous.ARM):
    def __init__(self,*args):
        self.service_events296=[];self.return296=None
        super().__init__(*args)
    def hook(self,uc,address,size,user):
        if address==(self.symbols['progress302']&~1):self.endpoint.checkpoint()
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
    src,pins=old.prepare(*args,**kwargs);d=args[0];close295(d);joint298(d);arch300(d);record305(d)
    p=d/'joint266_tb.sv';s=observe305(observe300(observe(p.read_text())))
    s=once(s,' task clear_output;', '''
 integer slot305=0,core305=0,other305=0,read305=0,frame305=0;
 reg [1:0] firstreq305=0,firstmiss305=0;
 always @(posedge clk)if(!reset&&active263)begin
  if(frame305!=f)begin frame305=f;firstreq305=0;firstmiss305=0;end
  if(planrom.kind<2&&planrom.source.tile_request&&!firstreq305[planrom.kind])begin
   firstreq305[planrom.kind]=1;
   $fwrite(events261,"firstreq305,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0t\\n",f,planrom.kind,romcycle267,qualify267,planrom.source.cache_path.cache.hit,planrom.source.cache_path.cache.pending,planrom.source.tile_ready,$time);
  end
  if(planrom.kind<2&&planrom.source.cache_path.cache.back_request&&!firstmiss305[planrom.kind])begin
   firstmiss305[planrom.kind]=1;
   $fwrite(events261,"firstmiss305,%0d,%0d,%0d,%0d,%0d,%0t\\n",f,planrom.kind,romcycle267,qualify267,core_req267,$time);
  end
  if(planrom.source.tile_request&&!planrom.source.tile_ready)begin
   if(!qualify267)slot305++;
   else if(core_req267)core305++;
   else other305++;
  end
  if(planrom.mr&&planrom.mready&&!core_req267)read305++;
  if(tv263&&tr263&&ti263==0)$fwrite(events261,"romtile305,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0t\\n",f,tk263,ts263,romcycle267,slot305,core305,other305,read305,$time);
  if(planrom.pv&&planrom.pready)$fwrite(events261,"plan293,%0d,%0d,%0d,%0t\\n",f,planrom.kind,planrom.slot,$time);
  if(planrom.pv&&planrom.pready)$fwrite(events261,"romplan305,%0d,%0d,%0d,%0d,%0d,%0t\\n",f,planrom.kind,romcycle267,qualify267,core_req267,$time);
  if(tv263&&tr263&&ti263==0)$fwrite(events261,"tile293,%0d,%0d,%0d,%0t\\n",f,tk263,ts263,$time);
 end
 always @(posedge host_clk)if(!reset&&active263)begin
  if(dut.flow.tile_consume||dut.flow.map_consume)$fwrite(events261,"consume293,%0d,%0d,%0d,%0t\\n",f,dut.flow.owner,dut.flow.chunk_token,$time);
 end
 task clear_output;''')
    s=s.replace('"display context265 frame%0d byte%0d",f,j','"display context265 frame%0d byte%0d got=%02x expected=%02x hcount=%0d mem699=%02x",f,j,val263,display_expected266,dut.core.validator.h_count,dut.core.memory[699]')
    p.write_text(s,encoding='utf-8',newline='\n')
    for n in ('nes_bg293.py','nes_bg294.py','nes_bg295.py','nes_stage290.py','nes_close295.py','probe_nes_live295.py','nes_wait296.py','nes_joint298.py','probe_nes_live298.py','nes_arch300.py','probe_nes_live300.py','probe_nes_live300rtl.py','nes_slice302.py','probe_nes_live302.py','nes_slice302b.py','probe_nes_live302b.py','nes_slice302c.py','probe_nes_live302c.py','nes_joint303.py','probe_nes_live303.py','nes_record305.py','probe_nes_live305.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins


def worker(*args,**kwargs):
    s=inspect.getsource(old.previous.worker).replace('assert len(steps)<=32','assert len(steps)<=2048')
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
