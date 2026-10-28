# SPDX-License-Identifier: MIT
"""375RTL/377ARM on shared SYSCLK;charge actual266 display-kernel service/VBlank."""
import csv,json,shutil,sys
present='--present' in sys.argv
if present:sys.argv.remove('--present')
warm='--warm-display' in sys.argv
if warm:sys.argv.remove('--warm-display')
import probe_nes_frontier377 as previous
from nes_delta231 import ROOT,BASE,sha,once
engine=previous.engine;old_prepare=engine.prepare
KERNEL=BASE/'probes/nes-present378/kernel01'

EXTRA=r'''
 localparam realtime MASTER_NS378=MASTER_PERIOD_PS378*0.001;
 reg [63:0] head378[0:127],tail378[0:127];reg [7:0] ppu378[0:65535];
 reg [7:0] scroll378[0:3];integer scroll_count378=0,ppu_writes378=0,presents378=0;
 function automatic [7:0] view378(input integer j);
  case(j)
   0:view378={7'd0,~display_serial373[0]};1:view378=expected_display265[18];2:view378=expected_display265[22];
   3:view378=prelude262[30];4:view378=prelude262[31];5:view378=prelude262[32];6:view378=prelude262[33];7:view378=prelude262[34];
   default:view378=expected_display265[j+4];
  endcase
 endfunction
 function automatic integer phase378;return (romcycle267+SNES_PHASE378)%357368;endfunction
 function automatic bit blank378;return phase378()>=225*1364;endfunction
 task until378(input realtime target);
  if(target>$realtime)#(target-$realtime);
 endtask
 task display_head378;
  integer bank,n,j;reg [63:0] e;reg [7:0] b;realtime base,target,shift,last_sample;
  begin
   bank=~display_serial373[0];bank=bank&1;
   if(view378(1)!=24||view378(2)!=2)$fatal(1,"kernel branch outside measured scope378");
   $readmemh($sformatf("kernel-head%0d.hex",bank),head378);n=head378[0];base=$realtime;shift=0;
   $fwrite(events261,"display_ready378,%0d,%0t,%0d\n",f,$time,phase378());
   for(integer i=1;i<=n;i++)begin
    e=head378[i];target=base+e[63:40]*MASTER_NS378+shift;until378(target);
    if(e[31:8]==24'h006054)begin
     rd261(e[31:8],b);
     while(!b)begin #(92*MASTER_NS378);rd261(e[31:8],b);end
     // Actual bus task and any observed ready stall advance all later events.
     if($realtime>target+400)shift+=($realtime-target-400);
    end else begin
     j=e[31:8]-24'h006070;rd261(e[31:8],b);last_sample=$realtime-200;
     if(j<0||j>=12||b!==view378(j))$fatal(1,"CPU view378 mismatch");
     display_reads265++;
    end
   end
   until378(last_sample+122*MASTER_NS378);
   $fwrite(events261,"display_poll378,%0d,%0t,%0d\n",f,$time,phase378());
  end
 endtask
 task display_tail378;
  integer bank,n,j,window_index;reg [63:0] e;reg [7:0] b;reg [23:0] a;reg [31:0] tok;realtime base,target;
  begin
   bank=(~display_serial373[0])&1;tok=dut.flow.last_map_token;scroll_count378=0;
   // Match the ROM:leave any current blank,then poll until the NEXT entry.
   // 92 is the largest observed4212 poll spacing46/52/92,not a CPU WCET proof.
   while(blank378())begin #(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;end
   while(!blank378())begin #(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;end
   base=$realtime;window_index=(romcycle267+SNES_PHASE378)/357368;
   $fwrite(events261,"vblank378,%0d,%0t,%0d,%0d\n",f,$time,phase378(),window_index);
   $readmemh($sformatf("kernel-tail%0d.hex",bank),tail378);n=tail378[0];
   for(integer i=1;i<=n;i++)begin
    e=tail378[i];target=base+e[63:40]*MASTER_NS378;until378(target);
    if(source_fault||flow_fault||test_abort)return;
    if(!blank378())$fatal(1,"display service left VBlank378");
    a=e[31:8];b=e[7:0];
    if(a>=24'h006048&&a<=24'h00604f)b=tok[a[1:0]*8+:8];
    if(a==24'h00210d||a==24'h00210e)begin b=view378(8+scroll_count378);scroll378[scroll_count378]=b;scroll_count378++;end
    if(a>=24'h006000)begin
     if(e[32])wr261(a,b);
     else begin rd261(a,b);if(b!==tok[a[1:0]*8+:8])$fatal(1,"actual final token read378");end
    end else begin
     if(!e[32])$fatal(1,"unsupported native read378");
     ppu378[a]=b;ppu_writes378++;
     $fwrite(events261,"ppu378,%0d,%0d,%0d,%0t,%0d\n",f,a,b,$time,phase378());
    end
   end
   if(scroll_count378!=4||ppu378[16'h2100]!=15||ppu378[16'h210b]!=(bank?6:0)||ppu378[16'h2101]!=bank+1||
      ppu378[16'h2107]!=(bank?8'h51:8'h31)||ppu378[16'h420c]!=14||ppu378[16'h212e]!=17)$fatal(1,"PPU bank/HDMA/window378");
   presents378++;
   $fwrite(events261,"present378,%0d,%0t,%0d,%0d\n",f,$time,window_index,phase378());
   wait(!v_sealed);
  end
 endtask
'''

def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];kernel=KERNEL;proof=json.loads((kernel/'result.json').read_text());assert proof['passed']
 for case in proof['cases']:
  bank=case['bank'];file=kernel/f'bank{bank}/events.csv';assert sha(file)==case['events']
  events=[list(map(int,x)) for x in csv.reader(file.read_text().splitlines())];head_first=case['head_first_master'];first_poll=case['first_4212_master']
  last_poll=max(x[3] for x in events if x[1]==0x4212)
  head=[x for x in events if head_first<=x[3]<first_poll];tail=[x for x in events if x[3]>last_poll]
  for name,rows,origin in (('head',head,head_first),('tail',tail,last_poll)):
   encoded=[len(rows)]+[((clock-origin)<<40)|(op<<32)|(address<<8)|value for op,address,value,clock,line in rows]
   (d/f'kernel-{name}{bank}.hex').write_text('\n'.join(f'{x:016x}' for x in encoded)+'\n')
  pins[str(file)]=sha(file)
 s=(d/'joint266_tb.sv').read_text();s=once(s,'reg clk=0;always #22.727 clk=~clk;',
  'reg clk=0;always begin #(MASTER_PERIOD_PS378/2*0.001)clk=1;#((MASTER_PERIOD_PS378-MASTER_PERIOD_PS378/2)*0.001)clk=0;end')
 s=once(s,'parameter real CPI=1.0;',f'parameter real CPI=1.0;\n parameter integer PRESENT378={int(present)},PRESENT_FIRST378={907 if warm else 905},MASTER_PERIOD_PS378=46561,SNES_PHASE378=0;')
 s=once(s,' initial begin : bus263',EXTRA+'\n initial begin : bus263')
 s=once(s,'    for(integer j=0;j<12;j++)begin\n     val263=0;', '    if(PRESENT378&&f>=PRESENT_FIRST378)display_head378();else begin\n    for(integer j=0;j<12;j++)begin\n     val263=0;')
 s=once(s,'    for(integer j=0;j<4;j++)if(dut.core.memory[712+j]', '    end\n    for(integer j=0;j<4;j++)if(dut.core.memory[712+j]')
 s=once(s,"    token261(dut.flow.last_map_token);wr261(24'h006058,8'h5a);wait(!v_sealed);",
  "    if(PRESENT378&&f>=PRESENT_FIRST378)display_tail378();else begin token261(dut.flow.last_map_token);wr261(24'h006058,8'h5a);wait(!v_sealed);end")
 (d/'joint266_tb.sv').write_text(s,newline='\n');shutil.copyfile(ROOT/'tools/probe_nes_present378.py',d/'probe_nes_present378.py')
 (d/'manifest378.json').write_text(json.dumps(dict(present=present,present_first_frame=907 if warm else 905,master_period_ps=46561,SNES_phase_cycles=0,kernel=proof,scope=__doc__),indent=2)+'\n')
 return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
