# SPDX-License-Identifier: MIT
import shutil
import probe_nes_owner319 as old
from nes_execute321 import apply
from nes_delta231 import ROOT,sha,once
previous=old.engine.prepare
def prepare(*args,**kwargs):
    src,pins=previous(*args,**kwargs);d=args[0];apply(d)
    p=d/'joint266_tb.sv';s=p.read_text()
    for old,kind,phase in [('PREAD',1,'READ'),('PCAP',1,'CAP'),('DREAD',0,'READ'),('DCAP',0,'CAP'),('MREAD313',2,'READ'),('MCAP313',2,'CAP')]:
        s=s.replace('dut.flow.state==dut.flow.'+old, f'(dut.flow.state==dut.flow.RAM_{phase}321&&dut.flow.read_kind321==2\'d{kind})')
    s=once(s,'endmodule', '''
 integer ram_cycles321=0,ram_reads321=0,ram_commits321=0;
 integer queue_reads321=0,open_wait321=0,put_wait321=0,receipt_wait321=0;
 always @(posedge host_clk)begin
  if(reset)begin
   ram_cycles321=0;ram_reads321=0;ram_commits321=0;
   queue_reads321=0;open_wait321=0;put_wait321=0;receipt_wait321=0;
  end else begin
   if(dut.ram_phase321!=0)ram_cycles321++;
   if(dut.ram_phase321==1||dut.ram_phase321==3||dut.ram_phase321==5||dut.ram_phase321==7||dut.ram_phase321==9)ram_reads321++;
   if(dut.ram_phase321!=0&&dut.core.ram_b_we)ram_commits321++;
   if(dut.flow.state==dut.flow.RAM_READ321)queue_reads321++;
   if(dut.flow.state==dut.flow.OPEN&&!dut.flow.begin_ready)open_wait321++;
   if(dut.flow.state==dut.flow.PUT&&!dut.flow.prelude_mode&&!dut.flow.put_ready)put_wait321++;
   if(dut.flow.state==dut.flow.WAIT_RECEIPT)receipt_wait321++;
  end
 end
endmodule''')
    marker='   $fwrite(events261,"frame_done,'
    assert s.count(marker)==1
    at=s.index(marker)
    s=s[:at]+'''   $fwrite(events261,"execute321,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d\\n",f,ram_cycles321,ram_reads321,ram_commits321,queue_reads321,open_wait321,put_wait321,receipt_wait321);
'''+s[at:]
    p.write_text(s,newline='\n')
    for n in ('nes_execute321.py','probe_nes_execute321.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins
old.engine.prepare=prepare
old.engine.__file__=__file__
if __name__=='__main__':old.engine.main()
