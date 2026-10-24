# SPDX-License-Identifier: MIT
"""Passive source/SPI/first-ROM ownership audit on unchanged336 RTL and ARM."""
import json,shutil
import probe_nes_read336 as previous
from nes_delta231 import ROOT,sha,once
engine=previous.engine
old_prepare=engine.prepare


def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0]
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,'   #(transaction_cost280[token*5+(final_ack?2:pop?1:0)]*CPI*1000.0/84.0);', '''   $fwrite(events261,"input_begin337,%0d,%0d,%0d,%0d,%0d,%0t\\n",hf337,token,pop,final_ack,transaction_cost280[token*5+(final_ack?2:pop?1:0)],$time);
   #(transaction_cost280[token*5+(final_ack?2:pop?1:0)]*CPI*1000.0/84.0);''')
    s=once(s,'   #2000;ss=1;#2000;wirebytes+=size;\n   if(!final_ack)', '''   #2000;ss=1;#2000;wirebytes+=size;
   $fwrite(events261,"input_wire337,%0d,%0d,%0d,%0d,%0d,%0t\\n",hf337,token,final_ack,rx[8][0],size,$time);
   if(!final_ack)''')
    s=once(s,'     #(source_cost280[token]*CPI*1000.0/84.0);', '''     $fwrite(events261,"input_decode337,%0d,%0d,%0d,%0t\\n",hf337,token,source_cost280[token],$time);
     #(source_cost280[token]*CPI*1000.0/84.0);''')
    s=once(s,' task exchange280(', ' integer hf337;\n task exchange280(')
    s=once(s,'   wait(enable);ended=0;pop=0;', '   wait(enable);hf337=hf;ended=0;pop=0;')
    s=once(s,'   wait(source_done);@(negedge clk);$fclose(record_fd);', '''   wait(source_done);@(negedge clk);$fclose(record_fd);
   $fwrite(events261,"input_done337,%0d,%0d,%0t\\n",f,romcycle267,$time);''')
    s=once(s,' parameter integer ROM_WINDOW=0;', ''' reg [1:0] published337=0;
 always @(posedge clk)begin
  if(reset)published337<=0;
  else begin
   published337<=dut.core.transport.publish;
   for(integer b337=0;b337<2;b337++)if(dut.core.transport.publish[b337]&&!published337[b337])
    $fwrite(events261,"input_publish337,%0d,%0d,%0t\\n",f,b337,$time);
  end
 end
 parameter integer ROM_WINDOW=0;''')
    p.write_text(s,newline='\n')
    shutil.copyfile(ROOT/'tools/probe_nes_ingress337.py',d/'probe_nes_ingress337.py');pins['probe_nes_ingress337.py']=sha(d/'probe_nes_ingress337.py')
    return src,pins


instances=[]
old_init=engine.ARM296.__init__
old_call=engine.ARM296.call
def observed_init(self,*args,**kwargs):
    old_init(self,*args,**kwargs);self.calls337=[];instances.append(self)
    for name in ('start286','geometry286','expand286','h2early286','begin285','plan_crc336'):
        if name in self.symbols:self.watch317[self.symbols[name]&~1]=name
def observed_call(self,name,args):
    start=self.stamp317();answer=old_call(self,name,args)
    self.calls337.append(dict(name=name,start=start,end=self.stamp317(),result=answer))
    return answer
old_worker=engine.worker
def worker(*args,**kwargs):
    result=old_worker(*args,**kwargs)
    (args[0]/'calls337.json').write_text(json.dumps(instances[-1].calls337,indent=2)+'\n',newline='\n')
    return result
engine.ARM296.__init__=observed_init
engine.ARM296.call=observed_call
engine.prepare=prepare
engine.worker=worker
engine.__file__=__file__
if __name__=='__main__':engine.main()
