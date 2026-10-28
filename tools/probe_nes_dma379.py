# SPDX-License-Identifier: MIT
"""378 display schedule plus warm PPU DMA access-window admission;not atomic frame proof."""
import json,shutil
import probe_nes_present378 as previous
from nes_delta231 import ROOT,sha,once
engine=previous.engine;old_prepare=engine.prepare

EXTRA=r'''
 task descriptor379(input integer map379,output integer bytes379,position379,output reg [31:0] token379);
  reg [7:0] b[0:10],ready379;
  begin
   rd261(24'h006040,ready379);
   if(!ready379)$fatal(1,"descriptor read before ready379");
   for(integer j=0;j<11;j++)rd261(24'h006041+j,b[j]);
   bytes379={b[2],b[1]};position379={b[4],b[3]};token379={b[10],b[9],b[8],b[7]};
   if(b[0][1]!=map379||b[0][2]!=(~display_serial373[0])||{b[6],b[5]}!=captured_generation365||
     bytes379==0||bytes379>2048)$fatal(1,"external descriptor identity/range379");
   $fwrite(events261,"descriptor379,%0d,%0d,%0d,%0d,%0d,%0d,%0t\n",f,map379,b[0],bytes379,position379,token379,$time);
  end
 endtask
 task dma_window379(input integer bytes379,input integer kind379,input integer clocks379);
  integer budget379,started379;realtime at379;
  begin
   // Startup905/906 retain the original forced-blank fixtures. Only warm
   // display access is constrained here;this is not a new boot proof.
   if(f>=907)begin
    budget379=clocks379>0?clocks379:1000+bytes379*10;at379=$realtime;started379=phase378();
    if(budget379>50468)$fatal(1,"command cannot fit one VBlank379");
    while(!blank378()||357368-phase378()<budget379)begin
     #(92*MASTER_NS378);if(test_abort||source_fault||flow_fault)return;
    end
    $fwrite(events261,"dma_wait379,%0d,%0d,%0d,%0t,%0t,%0d,%0d\n",f,kind379,bytes379,at379,$time,started379,phase378());
   end
  end
 endtask
 task dma_end379(input integer kind379);
  begin
   if(f>=907&&!blank378())$fatal(1,"warm PPU transfer outside VBlank379");
   $fwrite(events261,"dma_end379,%0d,%0d,%0t,%0d\n",f,kind379,$time,phase378());
  end
 endtask
'''

def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];p=d/'joint266_tb.sv';s=p.read_text()
 # Task definitions precede every caller and follow phase378 declarations.
 s=once(s,' task ordinary_cpu267;',EXTRA+'\n task ordinary_cpu267;')
 s=once(s,'realtime start267,target267;reg executed267;', 'realtime start267,target267;reg executed267,ppu379;')
 s=once(s,'  start267=$realtime;read267=0;', '''  ppu379=dut.flow.header[1]==3||dut.flow.header[1]==4;
  if(ppu379)dma_window379(dut.flow.chunk_length,2,int'(cpu267[cpu_at267+count267-1][63:40])+32);
  if(test_abort||source_fault||flow_fault)return;
  start267=$realtime;read267=0;''')
 s=once(s,'  $fwrite(events261,"cpu267,', '''  if(ppu379)dma_end379(2);
  $fwrite(events261,"cpu267,''')
 s=once(s,'integer n313,ignore313,done313;', 'integer n313,ignore313,done313,position379;')
 s=once(s,'  n313=dut.flow.chunk_length;token313=dut.flow.chunk_token;done313=dut.flow.queue.consumed312;',
  '  descriptor379(0,n313,position379,token313);dma_window379(n313,0,0);\n  if(test_abort||source_fault||flow_fault)return;\n  done313=dut.flow.queue.consumed312;')
 s=once(s,'  tilebytes263+=n313;', '  dma_end379(0);\n  tilebytes263+=n313;')
 s=once(s,'    ignore263=call263(6,first263,n/2);#41904;', '    dma_window379(n,1,0);\n    if(test_abort||source_fault||flow_fault)disable bus263;\n    ignore263=call263(6,first263,n/2);#41904;')
 s=once(s,'    n=dut.flow.chunk_length;first263=dut.flow.first;token263=dut.flow.chunk_token;',
  '    descriptor379(1,n,first263,token263);')
 s=once(s,'    wait(dut.flow.state!=dut.flow.DMA);', '    wait(dut.flow.state!=dut.flow.DMA);dma_end379(1);')
 # The added task references378 phase/clock definitions;move its declaration
 # after those definitions,while leaving callable task names unchanged.
 s=s.replace(EXTRA+'\n','');s=once(s,' initial begin : bus263',EXTRA+'\n initial begin : bus263')
 p.write_text(s,newline='\n');shutil.copyfile(ROOT/'tools/probe_nes_dma379.py',d/'probe_nes_dma379.py')
 (d/'manifest379.json').write_text(json.dumps(dict(warm_PPU_access_gate=True,WRAM_unrestricted=True,cold905906_original_fixtures=True,
  budget='Typedmap/tile1000+10*bytes;CGRAM/OAM actual CPU trace lastdelta+32 master clocks;whole-command gate includingWRAM precopy',atomic_frame_proven=False,source=sha(ROOT/'tools/probe_nes_dma379.py')),indent=2)+'\n')
 return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
