# SPDX-License-Identifier: MIT
"""Actual ARM270/refill/IRQ/ROM with NES-clock ordinary interpreter."""
import inspect,sys
import probe_nes_refill267 as old
from probe_nes_refill270 import prepare as prior_prepare,build
from nes_joint272 import patch
from nes_delta231 import once
SHARED='--shared-context' in sys.argv
if SHARED:sys.argv.remove('--shared-context')


def prepare(*args,**kwargs):
    src,pins=prior_prepare(*args,**kwargs)
    patch(args[0],src,pins,shared=SHARED)
    p=args[0]/'joint266_tb.sv';s=p.read_text()
    s=once(s,'module joint266_tb;','''module joint266_tb;
 integer meta_words272=0,body_bytes272=0,read_requests272=0,local_events272=0,completed272=0;''')
    s=once(s,'endmodule', '''
 always @(posedge host_clk)if(!reset)begin
  if(dut.flow.state==dut.flow.OPUSH&&dut.flow.mready)meta_words272++;
  if(dut.flow.state==dut.flow.OBYTE&&dut.flow.mready)body_bytes272++;
 end
 always @(posedge clk)if(!reset)begin
  if(dut.flow.parser_event_valid&&dut.flow.parser_event_ready)local_events272++;
  if(dut.flow.parser_reply_valid&&dut.flow.back_ready)begin
   if(dut.flow.parser_reply>=16)read_requests272++;
   else if(dut.flow.parser_reply==0)completed272++;
  end
 end
endmodule''')
    anchor=r'   $fwrite(events261,"frame_done,%0d,%0t,%0t\n",f,$time,output_end261-source_end261);'
    s=once(s,anchor,anchor+'''
   if(meta_words272!=8*completed272||body_bytes272!=read_requests272)
    $fatal(1,"parser272 metadata/read accounting");
   $fwrite(events261,"parser272,%0d,%0d,%0d,%0d,%0d,%0d\\n",f,meta_words272,body_bytes272,read_requests272,local_events272,completed272);''')
    if SHARED:
        s=once(s,'endmodule','''
 always @(posedge clk)if(!reset&&dut.cfg_valid272&&dut.cfg_ready272)begin
  if(!dut.core.output_phase||dut.core.encoder.q_pending||source_fault)
   $fatal(1,"source/context ownership collision");
 end
endmodule''')
    p.write_text(s,encoding='utf-8',newline='\n')
    return src,pins


def main():
    ns=dict(old.__dict__)
    ns.update(prepare=prepare,build=build,__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(old.main),'refill272-main','exec'),ns)
    ns['main']()


if __name__=='__main__':main()
