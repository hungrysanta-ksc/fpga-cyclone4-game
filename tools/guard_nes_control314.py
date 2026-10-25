# SPDX-License-Identifier: MIT
"""Directed common-executor guards with independent C/receipt scoreboards."""
import sys,json,shutil
from pathlib import Path
import guard_nes_record312 as old
from nes_executor313 import apply as executor,observe
from nes_manifest313 import apply as manifest
from nes_consumer313 import apply as consumer
from nes_admission313 import apply as admission,observe as admission_observe
from nes_delta231 import ROOT,sha,once
from nes_control314 import apply as control314
prior=old.old.old.record305


def patch(d):
    prior(d);executor(d);manifest(d);consumer(d);admission(d);control314(d)


old.old.old.record305=patch
engine=old.old.engine
previous=engine.prior.run


def adapt(s):
    s=observe(s)
    s=once(s,'crc263=c16(crc263,tx[j+1]);end',
           'if((GNEG==91||GNEG==92)&&all263[at]==2&&j==0&&!injected264)begin tx[j+1]=GNEG==91?6:9;injected264=1;end\n      crc263=c16(crc263,tx[j+1]);end')
    a=s.index('  wait(dut.flow.ordinary_ready);')
    b=s.index('  wait(dut.flow.begun&&',a)
    s=s[:a]+'''  for(integer i=0;i<28;i++)begin262[i]=prelude262[48+i];
'''+s[b:]
    for before,after in [('E_READ298','MREAD313'),('E_CAP298','MCAP313'),
                         ('E_NEXT298','MNEXT313'),('E_ZERO298','MISSUE313'),('E_SEAL298','MFINISH313')]:
        s=s.replace('dut.core.validator.state==dut.core.validator.'+before,'dut.flow.state==dut.flow.'+after)
    s=s.replace('dut.core.validator.packet_at298','dut.flow.parser_address')
    s=once(s,'if(dut.flow.state==dut.flow.ACKWAIT&&dut.flow.qdone)begin', '''if((dut.flow.state==dut.flow.ACKWAIT&&dut.flow.qdone)||
   (dut.flow.consume_write&&dut.flow.good_consume&&dut.flow.data_command278))begin''')
    s=admission_observe(s)
    a=s.index(' task ordinary_task263;');b=s.index(' task check_final265;',a)
    s=s[:a]+''' task ordinary_task263;
 integer n,ignored,done313;reg [7:0] val313;reg [31:0] token313;reg [15:0] seq313;
 begin
  n=dut.flow.qlen;done313=dut.flow.queue.consumed312;seq313=dut.flow.packet_seq-1'b1;
  for(integer i=0;i<16;i++)begin
   if(i>=4&&i<=9)val313=i<8?dut.flow.identity[(i-4)*8+:8]:dut.flow.identity[32+(i-8)*8+:8];
   else if(i==2)val313=seq313[7:0];else if(i==3)val313=seq313[15:8];else val313=dut.flow.header[i];
   ignored=call263(1,i,val313);
  end
  for(integer i=0;i<9;i++)rd261(24'h006060+i,val313);
  for(integer i=0;i<4;i++)begin rd261(24'h006048+i,val313);token313[i*8+:8]=val313;end
  for(integer i=16;i<n;i++)begin rd261(24'h400800+i-16,val313);ignored=call263(1,i,val313);end
  ignored=call263(2,n,0);
  token261(token313);wr261(24'h006059,8'ha5);
  wait(dut.flow.queue.consumed312!=done313);ordinary263++;
 end endtask
'''+s[b:]
    return once(s,' initial begin : result264', '''
 initial begin : common313_guards
  if(GNEG>=81&&GNEG<=90)begin
   if(GNEG==83)wait(dut.flow.state==dut.flow.MISSUE313&&dut.flow.header[0]==3&&dut.flow.manifest_byte313==190);
   else if(GNEG==84)wait(dut.flow.canonical_write313);
   else if(GNEG==88)wait(dut.flow.state==dut.flow.CHECK&&dut.flow.data_command278);
   else if(GNEG==90)wait(dut.flow.state==dut.flow.MCAP313&&dut.flow.header[0]==15&&dut.flow.parser_address==41);
   else if(GNEG==89)wait(dut.flow.ordinary_range&&v_ready);
   else wait(dut.flow.state==dut.flow.DMA&&dut.flow.data_command278);
   @(negedge host_clk);injected264=1;
   if(GNEG==83)force dut.flow.held=0;
   else if(GNEG==88)force dut.flow.ordinary_next313=32'hffffffff;
   else if(GNEG==89)force dut.core.validator.v_count=4095;
   else if(GNEG==90)begin force dut.flow.requirements313=1;force dut.flow.manifest_byte313=165;force dut.flow.qdata=8'hff;end
   else begin
    disable bus263;bus_read=1;bus_write=1;
    if(GNEG==84||GNEG==85)begin test_abort=1;end
    else if(GNEG==86)begin token261(dut.flow.chunk_token);wr261(24'h006058,8'h5a);end
    else if(GNEG==87)begin token261(dut.flow.chunk_token);wr261(24'h006050,8'ha5);end
    else begin
     if(GNEG==82)begin
      for(integer i=0;i<dut.flow.chunk_length;i++)begin rd261(24'h400800+i,admission_byte313);end
      token261(dut.flow.chunk_token+1);
     end else token261(dut.flow.chunk_token);
     wr261(24'h006059,8'ha5);
    end
   end
  end
 end
 reg [7:0] queue_frozen313[0:1023];reg freeze313=0;
 always @(negedge host_clk)begin
  if(source_fault&&!freeze313)begin
   freeze313=1;for(integer i=0;i<1024;i++)queue_frozen313[i]=dut.flow.queue.buffer[i];
  end else if(freeze313)begin
   for(integer i=0;i<1024;i++)if(queue_frozen313[i]!==dut.flow.queue.buffer[i])$fatal(1,"STOP queue/canonical write");
  end
 end
 initial begin : result264''')


def run(tool,args,d,label,*extra,**kwargs):
    if label=='vlog':
        p=d/'joint266_tb.sv';p.write_text(adapt(p.read_text()),newline='\n')
    return previous(tool,args,d,label,*extra,**kwargs)


engine.prior.run=run
engine.CASES.update({81:'consume before actual reads',82:'wrong ordinary consume token',
 83:'canonical map differs from independent receipt',84:'STOP during canonical write',
 85:'STOP after storage release before consumption',86:'final ACK before actual consume',
 87:'wrong consume namespace',88:'ordinary token exhaustion',89:'independent range bound',90:'RLE expanded overflow',
 91:'unsupported opcode 6 rejected',92:'unsupported opcode 9 rejected'})


if __name__=='__main__':
    old.old.old.main()
    d=Path(sys.argv[sys.argv.index('--out')+1])
    log=run(Path('C:/altera_standard/25.1std/questa_fse/win64/vsim.exe'),
      ['-c','-sv_lib','producer263','work.joint266_tb','-gGNEG=0','+LAST=905',
       '-do','onerror {quit -code 1};run -all;quit -f'],d,'positive313',180)
    assert 'PASS JOINT266 frames=1' in log
    result=json.loads((d/'result.json').read_text());result['positive_control313']=True
    for n in ('nes_executor313.py','nes_manifest313.py','nes_consumer313.py','nes_admission313.py','guard_nes_executor313.py','nes_control314.py','guard_nes_control314.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);result.setdefault('entry_hashes',{})[n]=sha(d/n)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
