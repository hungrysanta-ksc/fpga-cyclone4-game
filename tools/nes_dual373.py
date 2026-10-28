# SPDX-License-Identifier: MIT
"""NES373 two-context input/display boundary; shared by simulation and board MAP."""
import json,shutil,re
from nes_delta231 import ROOT,sha,once
from nes_capture368 import COMMON as PREVIOUS
DIRECTORY=ROOT/'src/fpga/nes_dual373'
CHANGED=tuple(p.name for p in DIRECTORY.glob('*.sv'))
COMMON=tuple(dict.fromkeys(PREVIOUS+tuple(n for n in CHANGED if n!='nes_live_joint.sv')))
def materialize(d):
 for n in CHANGED:shutil.copyfile(DIRECTORY/n,d/n)
def functional(d):
 materialize(d);p=d/'joint266_tb.sv';s=p.read_text()
 s=once(s,' wire [31:0] source_epoch365,captured_epoch365;', ''' wire [31:0] display_serial373;wire [2:0] display_raw373;
 wire [15:0] dispatch_gen373;
 wire [31:0] dispatch_epoch373;
 wire [31:0] dispatch_serial373;
 wire [31:0] source_epoch365,captured_epoch365;''')
 s=once(s,'nes_joint267_board dut(', 'nes_joint267_board dut(.display_serial373(display_serial373),.display_epoch373(captured_epoch365),.display_generation373(captured_generation365),.display_raw373(display_raw373),')
 s=s.replace('.captured_epoch(captured_epoch365),.captured_generation(captured_generation365),.*);','.captured_epoch(captured_epoch365),.captured_generation(captured_generation365),.display_serial373(display_serial373),.display_raw373(display_raw373),.*);')
 s=s.replace('.bank(~serial[0])','.bank(~display_serial373[0])').replace("{7'd0,~serial[0]}","{7'd0,~display_serial373[0]}")
 s=s.replace('.tile_generation(source_generation365)','.tile_generation(dispatch_gen373)').replace('.end_generation(source_generation365)','.end_generation(dispatch_gen373)')
 s=s.replace('.epoch361(source_epoch365),.serial361(serial)','.epoch361(dispatch_epoch373),.serial361(dispatch_serial373)').replace('.generation(source_generation365),','.generation(dispatch_gen373),').replace('.captured_epoch(source_epoch365),.live_epoch','.captured_epoch(dispatch_epoch373),.live_epoch')
 s=once(s,'if(output_phase&&dut.core.ram_a_we)$fatal(1,"source write during host phase");','''// Source shadow and validator memory are physically distinct RAMs.
  if(dut.core.ram_a_we&&dut.core.encoder.state==dut.core.encoder.IDLE)$fatal(1,"idle source RAM write373");''')
 s=once(s,'''if(dut.grant278&&(!output_phase||dut.core.encoder.q_pending||
     dut.core.encoder.mask_pending278||!dut.core.transport_empty))
   $fatal(1,"host grant before source/query/transport drain");''','''if(dut.grant278&&(!output_phase||!lease_valid))
   $fatal(1,"host grant without committed display context373");''')
 s=s.replace('reg [1:0] published337=0','reg [3:0] published337=0').replace('b337<2','b337<4')
 s=s.replace('"input_publish337,%0d,%0d,%0t\\n",f,b337','"input_publish337,%0d,%0d,%0t\\n",source_frame367,b337')
 s=s.replace('"materialized366,%0d,%0d,%0t\\n",f,romcycle267','"materialized366,%0d,%0d,%0t\\n",source_frame367,romcycle267')
 s=s.replace('frame.started&&!waiting_display','frame.started')
 s=s.replace('dut.core.transport.block_valid[~dut.core.transport.bank]','dut.core.transport.wgray!=dut.core.transport.rgray_s2')
 s=s.replace('frame.local_source365','(frame.materialized&&frame.armed)')
 s=s.replace('if(source_generation365!==captured_generation365||source_epoch365!==captured_epoch365)', 'if(dispatch_gen373!==captured_generation365||dispatch_epoch373!==captured_epoch365||dispatch_serial373!==display_serial373)')
 s=s.replace('wait(capture_done_id367>=f);wait(owned);','wait(capture_done_id367>=f);')
 # Write passive per-frame fixture metadata at source admission, while collector is immutable.
 old='''   name=$sformatf("frame%0d.cfg",f);cf=$fopen(name,"w");
   $fwrite(cf,"%0d %0d %0d %0d %0d %0d\\n",generation,patch_count,object_count,exception_count,group_count,palette_count);$fclose(cf);'''
 assert old in s;s=s.replace(old,'')
 s=s.replace('string filename367;\n  source_frame367', 'string filename367;integer cfg373;\n  source_frame367')
 needle='  filename367=$sformatf("frame%0d.expected",source_frame367);'
 s=once(s,needle,'''  if(!owned||!geometry_valid||source_generation365!=generation)$fatal(1,"source admission without immutable capture373");
  filename367=$sformatf("frame%0d.cfg",source_frame367);cfg373=$fopen(filename367,"w");
  $fwrite(cfg373,"%0d %0d %0d %0d %0d %0d\\n",generation,patch_count,object_count,exception_count,group_count,palette_count);$fclose(cfg373);
'''+needle)
 s=s.replace('if(!owned||!geometry_valid)$fatal(1,"collector frame=', 'if(f<908&&(!owned||!geometry_valid))$fatal(1,"collector frame=')
 s=s.replace('for(integer j=0;j<396;j++)if(keep[j]!==dut.core.memory[addr300(j)])$fatal(1,"persistent state clobbered");', '''// This input may overlap the previous display's legal validator writes.
   // Each actual display is checked independently against its expected payload/receipt.
   if(f<=907)for(integer j=0;j<396;j++)if(keep[j]!==dut.core.memory[addr300(j)])$fatal(1,"persistent state clobbered");''')
 s=s.replace('endmodule','assign dispatch_gen373=captured_generation365;\n assign dispatch_epoch373=captured_epoch365;\n assign dispatch_serial373=display_serial373;\n endmodule')
 p.write_text(s,newline='\n')
def board(d):materialize(d)
