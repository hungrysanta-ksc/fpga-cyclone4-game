# SPDX-License-Identifier: MIT
import shutil
import probe_nes_ingress338 as previous
from nes_reader351 import apply
from nes_delta231 import ROOT,sha,once
engine=previous.engine
old=engine.prepare

def prepare(*a,**k):
    src,pins=old(*a,**k);d=a[0];apply(d)
    # Import observer text without installing its generator hooks.
    import ast
    tree=ast.parse((ROOT/'tools/probe_nes_port350.py').read_text())
    observer=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OBSERVER' for t in n.targets))
    observer=observer.replace('dut.flow.queue.read_address312','dut.flow.ram_address351')
    observer=observer.replace('dut.flow.record_valid312','(dut.flow.state==dut.flow.HLOAD315&&dut.flow.header_pending351)')
    observer=observer.replace('dut.flow.state==dut.flow.DREAD',"(dut.flow.state==dut.flow.PREAD&&dut.flow.read_kind351==1)")
    observer=observer.replace('dut.flow.state==dut.flow.DCAP',"(dut.flow.state==dut.flow.PCAP&&dut.flow.read_kind351==1)")
    observer=observer.replace('dut.flow.state==dut.flow.MCAP313',"(dut.flow.state==dut.flow.PCAP&&dut.flow.read_kind351==2)")
    observer=observer.replace('dut.flow.parser_address,dut.flow.at,','dut.flow.parser_address,(dut.flow.state==dut.flow.HLOAD315?dut.flow.return_addr351:dut.flow.at),')
    p=d/'joint266_tb.sv';s=p.read_text();s=once(s,'endmodule',observer+'\nendmodule');p.write_text(s,newline='\n')
    for n in ('nes_reader351.py','probe_nes_reader351.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins

old_init=engine.ARM296.__init__
def observed_init(self,*a,**k):
    old_init(self,*a,**k)
    for n in ('nes_dirty231_material','nes_dirty231_begin'):
        if n in self.symbols:self.watch317[self.symbols[n]&~1]=n
engine.ARM296.__init__=observed_init
engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
