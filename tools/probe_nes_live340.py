# SPDX-License-Identifier: MIT
"""Live M4 decode/BG preparation charged at each verified source bank.

D4 shifter/prefix remains RTL + measured prefix-instruction replay. The same
M4 instance prepares BG before input ACK and continues into output execution.
Every fixture byte given to M4 is checked against actual SPI before its bank
checkpoint retires. There is no uncharged CPU/SPI overlap.
"""
import inspect,shutil
import probe_nes_joint340 as old
from nes_delta231 import once,BASE
engine=old.engine
old_prepare=engine.prepare
old_native=engine.native
def native(d):
    old_native(d)
    p=d/'nes_planner285.c';s=p.read_text()
    s='extern unsigned prefill287(void);\n'+s
    s=once(s,'reserve_bytes293=bytes;reserve_plans293=plans;return true;', 'reserve_bytes293=bytes;reserve_plans293=plans;return prefill287()!=0;')
    p.write_text(s,newline='\n')
def prepare(*args,**kwargs):
    src,pins=old_prepare(*args,**kwargs);d=args[0]
    for f in range(905,args[1]+1):
        shutil.copyfile(BASE/f'probes/nes-hybrid340/arm03/frame{f}.records',d/f'input340-{f}.records')
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,'integer hf,k;reg ended,pop;', 'integer hf,k,bridge340;reg ended,pop;')
    s=once(s,'wait(enable);hf337=hf;ended=0;pop=0;', 'wait(enable);hf337=hf;bridge340=bridge267(0,hf,0);if(bridge340<0)$fatal(1,"input ARM start340");ended=0;pop=0;')
    s=once(s,'integer i,b,size;reg [7:0] c;', 'integer i,b,size,n340,delay340,ignore340;reg [7:0] c;')
    s=once(s,'     #(source_cost280[token]*CPI*1000.0/84.0);', '''     n340=bridge267(1,0,0);if(n340!=261)$fatal(1,"non-checkpoint before input commit340 %0d",n340);
     delay340=bridge267(5,0,0);#((delay340*CPI+bridge267(6,0,0))*1000.0/84.0);
     $fwrite(events261,"input_ARM340,%0d,%0d,%0d,%0t\\n",hf337,token,delay340,$time);
     ignore340=bridge267(4,int'($time),int'($time>>32));if(ignore340<0)$fatal(1,"input ARM response340");''')
    s=once(s,'ignore267=bridge267(0,f,0);if(ignore267<0)$fatal(1,"ARM rendezvous start");finished267=0;', 'finished267=0; // M4 already owns the checked input-bank rendezvous.')
    p.write_text(s,newline='\n');return src,pins

old_source=inspect.getsource
def worker_source(fn):
    s=old_source(fn)
    if 'decoder+=n;ep.before+=n' in s and 'preview=False;components={}' in s:
        s=s.replace("records(d/f'frame{f}.records')", "records(d/f'input340-{f}.records')")
        s=once(s,'decoder+=n;ep.before+=n', 'decoder+=n')
        s=once(s,'        geom,raw=golden(f);', '            ep.checkpoint ()\n        geom,raw=golden(f);')
        s=s.replace('decoder_excluded=decoder','decoder_excluded=0,live_decoder_instructions340=decoder')
    return s
inspect.getsource=worker_source
engine.prepare=prepare
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
