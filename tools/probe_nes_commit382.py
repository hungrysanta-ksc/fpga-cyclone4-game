# SPDX-License-Identifier: MIT
"""379 PPU-window/real descriptor schedule with measured381sameblank commit service."""
import json,shutil
import probe_nes_dma379 as previous
import probe_nes_present378 as timing
from nes_delta231 import ROOT,BASE,sha,once
timing.KERNEL=BASE/'probes/nes-present378/vblank01/capsule'
engine=previous.engine;old_prepare=engine.prepare

def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];p=d/'joint266_tb.sv';s=p.read_text()
 proof=json.loads((timing.KERNEL/'result.json').read_text());latches={x['latch_offset_clocks'] for x in proof['cases']};assert len(latches)==1;latch=latches.pop()
 old='''   while(blank378())begin #(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;end
   while(!blank378())begin #(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;end
   base=$realtime;window_index=(romcycle267+SNES_PHASE378)/357368;'''
 new=f'''   base=$realtime;
   if(blank378())begin
    #({latch}*MASTER_NS378);
    // Actual381 SLHV latch-time decision;no future geometry or bank data.
    if(phase378()/1364>=225&&phase378()/1364<=257)begin
     $fwrite(events261,"sameblank382,%0d,%0t,%0d\\n",f,$time,phase378());
    end else begin
     while(blank378())begin #(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;end
     while(!blank378())begin #(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;end
     base=$realtime;
    end
   end else begin
    while(!blank378())begin #(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;end
    base=$realtime;
   end
   window_index=(romcycle267+SNES_PHASE378)/357368;'''
 s=once(s,old,new)
 oldread='''     else begin rd261(a,b);if(b!==tok[a[1:0]*8+:8])$fatal(1,"actual final token read378");end'''
 newread='''     else begin rd261(a,b);
      if(a==24'h006001)begin if(b[7:6])begin ppu378[16'h2100]=8'h80;ppu378[16'h420c]=0;return;end end
      else if(b!==tok[a[1:0]*8+:8])$fatal(1,"actual final token read378");
     end'''
 s=once(s,oldread,newread);p.write_text(s,newline='\n');shutil.copyfile(ROOT/'tools/probe_nes_commit382.py',d/'probe_nes_commit382.py')
 (d/'manifest382.json').write_text(json.dumps(dict(sameblank=True,cutoff_scanline=257,latch_offset_clocks=latch,kernel=proof,
  scope='Actual381 head/currentblank service allocation on379schedule;extra counter cost retained fornext-blank path. Not fullCPU arbitraryphase reexecution.'),indent=2)+'\n')
 return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
