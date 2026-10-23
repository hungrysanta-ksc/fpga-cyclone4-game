# SPDX-License-Identifier: MIT
import shutil
import probe_nes_expand325 as old
from nes_joint327 import apply,native
from nes_delta231 import ROOT,sha,once
engine=old.old.engine
previous_init=engine.ARM296.__init__
def observed_init(self,*args,**kwargs):
    previous_init(self,*args,**kwargs)
    if 'issue_map327' in self.symbols:self.watch317[self.symbols['issue_map327']&~1]='issue_map327'
engine.ARM296.__init__=observed_init
previous=engine.prepare
def prepare(*args,**kwargs):
    src,pins=previous(*args,**kwargs);d=args[0];apply(d)
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,' task clear_output;',r'''
 integer seen_frame327=0;reg [2:0] accepted327=0,response327=0;
 always @(posedge clk)if(!reset&&active263)begin
  if(seen_frame327!=f)begin seen_frame327=f;accepted327=0;response327=0;end
  if(planrom.kind<3&&planrom.mr&&planrom.mready&&!core_req267&&!accepted327[planrom.kind])begin
   accepted327[planrom.kind]=1;$fwrite(events261,"rom_accept327,%0d,%0d,%0t\n",f,planrom.kind,$time);
  end
  if(planrom.kind<3&&planrom.source.cache_path.cache.back_response&&!response327[planrom.kind])begin
   response327[planrom.kind]=1;$fwrite(events261,"rom_response327,%0d,%0d,%0t\n",f,planrom.kind,$time);
  end
 end
 integer expected_count327=0;
 always @(posedge host_clk)if(!reset&&active263&&!source_fault)begin
  if(dut.scan_start327)begin expected_count327=0;$fwrite(events261,"scan_start327,%0d,%0t\n",f,$time);end
  if(dut.core.validator.state==dut.core.validator.E_CAPTURE327)begin
   if(dut.expected_addr327!=expected_count327)$fatal(1,"expected sequence327");
   expected_count327++;
  end
  if(dut.scan_done327)begin
   if(expected_count327!=446)$fatal(1,"incomplete expected scan327");
   $fwrite(events261,"scan_done327,%0d,%0d,%0t\n",f,expected_count327,$time);
  end
  if(dut.flow.canonical_read313&&dut.flow.canonical_write313)$fatal(1,"expected RAM port collision327");
 end
 task clear_output;''')
    p.write_text(s,newline='\n')
    for n in ('nes_joint327.py','probe_nes_joint327.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins
engine.prepare=prepare
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
