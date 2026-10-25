# SPDX-License-Identifier: MIT
import os,shutil
import probe_nes_live317 as observer
from nes_metadata317 import native
from nes_owner319 import apply
from nes_delta231 import ROOT,sha,once
engine=observer.engine
engine.native=native
previous=engine.prepare

def prepare(*args,**kwargs):
    src,pins=previous(*args,**kwargs);d=args[0]
    if os.environ.get('NES319_REFERENCE')!='1':apply(d)
    p=d/'joint266_tb.sv';s=p.read_text()
    # A common absolute capture schedule. The capture starts are on NES edges;
    # no per-candidate delay is subtracted from measured processing cost.
    if os.environ.get('NES319_FIXED')=='1':
        s=once(s,'   wait(initialized);@(negedge clk);', '''   wait(initialized);
   if($realtime>1000000.0+(f-905)*160000000.0)$fatal(1,"missed fixed start319");
   wait($realtime>=0); // event-free comparison below uses an explicit delay
   #(1000000.0+(f-905)*160000000.0-$realtime);
   @(negedge clk);
   $fwrite(events261,"capture319,%0d,%0t,%0d\\n",f,$time,romcycle267);''')
    s=once(s,'   @(negedge clk);enable=1;@(negedge clk);enable=0;', '''   @(negedge clk);enable=1;
   $fwrite(events261,"start319,%0d,%0t,%0d\\n",f,$time,romcycle267);
   @(negedge clk);enable=0;''')
    p.write_text(s,newline='\n')
    for n in ('nes_owner319.py','probe_nes_owner319.py','nes_metadata317.py','probe_nes_live317.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
    return src,pins
engine.prepare=prepare
engine.__file__=__file__
if __name__=='__main__':engine.main()
