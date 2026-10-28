# SPDX-License-Identifier: MIT
"""Shared source-ready IRQ RTL and an executable single-ARM SPI foreground."""
import json,shutil
from nes_delta231 import ROOT,BASE,sha,once
from nes_capture365 import COMMON as CAPTURE_COMMON
COMMON=CAPTURE_COMMON+('nes_spi270.sv',)
REFERENCE=BASE/'probes/nes-capture365/map03'

def materialize(d):
    folder=ROOT/'src/fpga/nes_hint367';m=json.loads((folder/'manifest.json').read_text())
    for name,h in m['source_files'].items():
        assert sha(folder/name)==h;shutil.copyfile(folder/name,d/name)

def board(d):
    materialize(d);p=d/'nes_live_joint.sv';s=p.read_text()
    s=once(s,'wire progress_irq284,progress_mode284;', 'wire progress_irq284,progress_mode284,source_mode367;\nwire [199:0] source_status270;')
    s=once(s,'wire [199:0] source_status270,output_status270,plan_status270;', 'wire [199:0] output_status270,plan_status270;')
    s=once(s,'assign out_observe_ready=progress_mode284?progress_irq284:external_memory_ready;',
           'assign out_observe_ready=source_mode367?source_status270[0]:progress_mode284?progress_irq284:external_memory_ready;')
    s=once(s,'.progress_mode284(progress_mode284),', '.progress_mode284(progress_mode284),.source_mode367(source_mode367),')
    p.write_text(s,newline='\n')

DRIVER=r'''
 wire gpio367=source_mode367?source_status270[0]:progress_irq284;

 task shift367(input integer count367);
  begin
   for(integer j=0;j<count367;j++)begin
    rx[j]=0;
    for(integer b=7;b>=0;b--)begin
     mosi=tx[j][b];#190.476190476;sck=1;rx[j][b]=selected?miso:0;#190.476190476;sck=0;
    end
   end
   wirebytes+=count367;
  end
 endtask
 always @(posedge clk)if(!reset&&source_start365)begin : start_source367
  string filename367;
  source_frame367=source_serial367_fixture();
  filename367=$sformatf("frame%0d.expected",source_frame367);$readmemh(filename367,expected);
  filename367=$sformatf("frame%0d.records",source_frame367);record_fd=$fopen(filename367,"w");
  seen=0;queries=0;cycles=0;prepare=0;blocked=0;qwait=0;transfer_cycles=0;overlap=0;crc_cycles=0;
  for(integer j=0;j<396;j++)keep[j]=dut.core.memory[addr300(j)];
  $fwrite(events261,"start319,%0d,%0t,%0d\n",source_frame367,$time,romcycle267);
 end
 // Frame ID is used only by passive verification/logging, never by ARM hints.
 function automatic integer source_serial367_fixture();source_serial367_fixture=904+serial;endfunction
 initial begin : live_foreground367
  integer hf367,n367,count367,delay367,ignore367;reg finished367;
  wait(!reset);wait(first!=0);
  for(hf367=first;hf367<=last;hf367++)begin
   ignore367=bridge267(0,hf367,0);if(ignore367<0)$fatal(1,"ARM frame rendezvous367");
   finished367=0;
   while(!finished367)begin
    n367=bridge267(1,0,0);if(n367<0)$fatal(1,"ARM request367");
    delay367=bridge267(5,0,0);#((delay367*CPI+bridge267(6,0,0))*1000.0/84.0);
    if(n367==261)$fwrite(events261,"checkpoint287,%0d,%0t,%0d\n",hf367,$time,delay367);
    else if(n367==260)begin
     if(!ss)$fatal(1,"WFI while source CS held367");
     fork : wake367
      begin wait(gpio367);end
      begin #(10000000-($time%10000000));end
     join_any
     disable wake367;
     $fwrite(events261,"wait367,%0d,%0d,%0d,%0t\n",hf367,source_mode367,gpio367,$time);
    end else if(n367==0)begin
     if(!ss)$fatal(1,"ARM ended with SPI held367");finished367=1;
     $fwrite(events261,"armdone284,%0d,%0t,%0d,%0d\n",hf367,$time,delay367,bridge267(6,0,0));
    end else begin
     count367=n367>=512?(n367&511):n367;
     for(integer j=0;j<count367;j++)tx[j]=bridge267(2,j,0);
     if(n367>=512&&n367<1024)begin
      if(!ss||count367!=13)$fatal(1,"source prefix transaction367");
      #2000;ss=0;#2000;shift367(count367);
      $fwrite(events261,"source_prefix367,%0d,%0d,%0d,%0t\n",hf367,rx[8],rx[9],$time);
     end else if(n367>=1024)begin
      if(ss||count367>250)$fatal(1,"source tail transaction367");
      shift367(count367);#2000;ss=1;#2000;
      $fwrite(events261,"source_tail367,%0d,%0d,%0t\n",hf367,count367,$time);
     end else begin
      if(!ss)$fatal(1,"SPI owner overlap367");
      $fwrite(events261,"ARM_wire_start334,%0d,%0d,%0d,%0t\n",hf367,tx[0],n367,$time);
      if(tx[0]==8'hea)$fwrite(events261,"hint_start367,%0d,%0t\n",hf367,$time);
      transfer(n367);
      if(tx[0]==8'hea)$fwrite(events261,"hint_end367,%0d,%0t\n",hf367,$time);
      $fwrite(events261,"arm267,%0d,%0d,%0d,%0t,%0d,%0d\n",hf367,tx[0],n367,$time,delay367,bridge267(6,0,0));
     end
     for(integer j=0;j<count367;j++)ignore367=bridge267(3,j,rx[j]);
    end
    ignore367=bridge267(7,gpio367,0);
    ignore367=bridge267(4,int'($time),int'($time>>32));if(ignore367<0)$fatal(1,"ARM response367");
   end
   arm_done_frame367=hf367;
  end
 end
 always @(posedge clk)if(planrom.hfinished361)
  $fwrite(events261,"hint_fill367,%0d,%0t\n",source_frame367,$time);
'''

def functional(d):
    materialize(d);p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,'module joint266_tb;', 'module joint266_tb;\n integer arm_done_frame367=904,source_frame367=904;')
    s=once(s,'wire progress_irq284,progress_mode284;', 'wire progress_irq284,progress_mode284,source_mode367;')
    s=once(s,'.progress_mode284(progress_mode284),', '.progress_mode284(progress_mode284),.source_mode367(source_mode367),')
    t=s.index('tiles_task263();',s.index('task output_frame;'));a=s.rfind('fork',0,t);z=s.index('wait(flow_retired);',a)
    s=s[:a]+'''   tiles_task263();
   wait(arm_done_frame367>=f);
'''+s[z:]
    a=s.index('reg [31:0] source_cost280')
    # The next unlabelled initial is the main frame fixture, after consumer.
    consumer=s.index(' initial begin : consumer',a)
    z=s.index(' initial begin\n',consumer)
    s=s[:a]+DRIVER+'\n'+s[z:]
    # Passive source fixtures must be ready even if a following source begins
    # during the previous ARM commit; they never control admission.
    a=s.index('name=$sformatf("frame%0d.expected",f);');z=s.index('for(t=7*341+257;',a)
    s=s[:a]+s[z:]
    s=s.replace('wait(start_ready);','')
    s=once(s,'if(owned||!lease_valid||!waiting_display)', 'if(!lease_valid||!waiting_display)')
    s=once(s,'if(lease_valid||waiting_display||owned)', 'if(lease_valid||waiting_display)')
    s=once(s,'queries!=group_count*33+224+object_count+exception_count+224+palette_count*32+patch_count*256',
           'queries!=dut.core.encoder.q_maps+224+dut.core.encoder.q_objects+dut.core.encoder.q_exceptions+224+dut.core.encoder.q_palettes+dut.core.encoder.admitted_raw*256')
    assert 'source_cost280[' not in s and 'hint361.cmd' not in s and 'wait(enable)' not in s
    p.write_text(s,newline='\n')
    # The bridge still transfers actual bytes, with an explicit held-CS phase.
    p=d/'nes_bridge267.c';s=p.read_text()
    s=once(s,'static unsigned serial, count, delay, tx[259], rx[259];', 'static unsigned serial, count, payload367, delay, tx[259], rx[259];')
    s=once(s,'||count>261)', '||!(count<=261||count==525||(count>=1024&&count<=1274)))')
    s=once(s,'for(unsigned i=0;i<(count>=260?0:count);i++)if(fscanf',
           'payload367=count>=512?(count&511):count>=260?0:count;\n  for(unsigned i=0;i<payload367;i++)if(fscanf')
    s=s.replace('(unsigned)a<count','(unsigned)a<payload367').replace('(unsigned)a>=count','(unsigned)a>=payload367')
    s=once(s,'for(unsigned i=0;i<(count>=260?0:count);i++)fprintf', 'for(unsigned i=0;i<payload367;i++)fprintf')
    p.write_text(s,newline='\n')

def continuous(d,last):
    p=d/'joint266_tb.sv';s=p.read_text()
    s=once(s,' task clear_output;', r'''
 reg [106:0] ppu367[0:89341];reg [191:0] palette367[0:0];
 reg free_run367=0,free_done367=0;
 integer capture_cycle367=0,next_cycle367,free_id367,free_t367,capture_done_id367=907;
 integer attempts367=0,missed367=0,admitted367=0;
 always @(posedge clk)if(!reset&&capture_begin)capture_cycle367=romcycle267;
 always @(posedge clk)if(!reset&&lease_valid)begin
  if(source_generation365!==captured_generation365||source_epoch365!==captured_epoch365)
   $fatal(1,"display context changed during next capture367");
 end
 initial begin : independent_ppu367
  string file367;
  wait(free_run367);next_cycle367=capture_cycle367+357368;
  for(free_id367=908;free_id367<=last+1;free_id367++)begin
   if(free_id367<=last)begin
    file367=$sformatf("frame%0d.hex",free_id367);$readmemh(file367,ppu367);
    file367=$sformatf("frame%0d.palette",free_id367);$readmemh(file367,palette367);
   end
   while(romcycle267<next_cycle367)@(negedge clk);
   palette=palette367[0];scanline=7;dot=257;drive=ppu367[7*341+257];ppu_ce=1;#1;
   attempts367++;if(capture_begin)admitted367++;else missed367++;
   $fwrite(events261,"capture_attempt367,%0d,%0d,%0d,%0d,%0t\n",free_id367,owned,capture_begin,generation,$time);
   if(!capture_begin)$fatal(1,"next capture deadline missed367 frame%0d",free_id367);
   @(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);
   if(free_id367<=last)begin
    for(free_t367=7*341+258;free_t367<=232*341+1;free_t367++)begin
     @(negedge clk);scanline=free_t367/341;dot=free_t367%341;drive=ppu367[free_t367];ppu_ce=1;
     @(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);
    end
    capture_done_id367=free_id367;
   end
   next_cycle367=next_cycle367+357368;
  end
  free_done367=1;
 end
 final $display("CADENCE367 attempts=%0d admitted=%0d missed=%0d",attempts367,admitted367,missed367);
 task clear_output;''')
    s=once(s,'for(t=7*341+257;t<=232*341+1;t++)begin', '''if(f>=908)begin
    wait(capture_done_id367>=f);wait(owned);
   end else for(t=7*341+257;t<=232*341+1;t++)begin''')
    s=once(s,'repeat(64)@(negedge clk);', 'if(f==907)free_run367=1;\n   repeat(64)@(negedge clk);')
    s=once(s,'manual_release=1;', '''if(f==last)begin
    wait(free_done367);
    if(missed367||attempts367!=last-906)$fatal(1,"capture coverage367");
   end
   manual_release=1;''')
    p.write_text(s,newline='\n')
