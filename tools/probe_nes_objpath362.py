# SPDX-License-Identifier: MIT
import shutil,sys
import probe_nes_hint361 as previous
from nes_obj362 import apply
from nes_query356 import apply as query
from nes_cancel358 import apply as cancel
from nes_execute362 import apply as common
from nes_delta231 import ROOT,sha,once
engine=previous.engine;old_prepare=engine.prepare
keep_source='--keep-source' in sys.argv
if keep_source:sys.argv.remove('--keep-source')
def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];apply(d)
 if not keep_source:query(d);cancel(d);common(d)
 p=d/'joint266_tb.sv';s=p.read_text()
 for x,y in [('hint361[0:23]','hint361[0:27]'),('j<24;j++','j<28;j++'),('wirebytes+=24','wirebytes+=28')]:s=once(s,x,y)
 if not keep_source:
  s=s.replace('dut.core.transport.publish','dut.core.transport.busy')
  s=s.replace('always @(posedge clk)begin\n  if(reset)published337','always @(posedge host_clk)begin\n  if(reset)published337').replace('always @(posedge clk)if(!reset&&dut.core.transport_crc_pending)','always @(posedge host_clk)if(!reset&&dut.core.transport_crc_pending)')
  begin=s.index(' always @(posedge clk)if(!reset)begin\n  if(dut.core.encoder.a_we');end=s.index(' reg [7:0] tx',begin)
  block=s[begin:end].replace('posedge clk','posedge host_clk').replace('  if(query)queries++;\n','')
  x=block.index('  if(dut.core.encoder.state!=');y=block.index('  if(dut.core.record_valid&&dut.core.record_ready)',x);counters=block[x:y];block=block[:x]+block[y:]
  s=s[:begin]+block+' always @(posedge clk)if(!reset)begin\n if(query)queries++;\n'+counters+' end\n'+s[end:]
  # The same owner assertions used by the separately measured common boundary.
  text=(ROOT/'tools/probe_nes_execute362.py').read_text();start=text.index(' integer crc_source362=');stop=text.index(' task clear_output;',start)
  s=once(s,' task clear_output;',text[start:stop]+' task clear_output;')
 p.write_text(s,newline='\n')
 p=d/'hint-run361.py';p.write_text(p.read_text(encoding='utf-8').replace('run_nes_hint361.py','run_nes_obj362.py'),encoding='utf-8',newline='\n')
 for n in ('nes_obj362.py','probe_nes_objpath362.py','run_nes_obj362.py','nes_query356.py','nes_cancel358.py','nes_execute362.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
