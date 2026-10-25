# SPDX-License-Identifier: MIT
"""NES348 actual fixed-block repeat8/16 encoder: MASK/left SHIFT/right SHIFT, stalls and SHIFT-build STOP."""
import argparse,json,shutil,subprocess,os,re
from pathlib import Path
from nes_delta231 import sha
from nes_fixed347 import encode347 as encode280
TB=r'''
module record344_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort_source=0,start=0,ack_valid=0,display_ack=0;
 integer f=1,ticks=0,fd,at=0;
 wire ready,done,ack_ready,rv,bv;wire[3:0] fault;wire[7:0] len,data;
 wire query;wire[2:0] qkind;wire[12:0] qi;reg response=0;reg[63:0] raw=0;
 reg[15:0] maps[0:32];reg[7:0] memory[0:1023];reg[7:0] aq=0,bq=0;
 wire[9:0] aa,ba;wire awe,bwe;wire[7:0] aw,bw;
 wire record_ready=ticks%7==0,byte_ready=ticks%5!=0;
 nes_core257 dut(.clk(clk),.reset(reset),.abort_source(abort_source),.start(start),.start_ready(ready),
 .plan_zero319(1'b0),.plan_step319(1'b0),.ram_a_q(aq),.ram_b_q(bq),.ram_a_addr(aa),.ram_b_addr(ba),.ram_a_we(awe),.ram_b_we(bwe),.ram_a_w(aw),.ram_b_w(bw),
 .display_write(1'b0),.display_request(1'b0),.display_response_ready(1'b0),
 .v_begin_valid(1'b0),.v_target_bank(1'b0),.v_raw_count(3'd0),.v_range_valid(1'b0),.v_map_range(1'b0),.v_first(12'd0),.v_count(12'd0),.v_check_valid(1'b0),.v_check_value(8'd0),.v_finish_valid(1'b0),.v_all_consumed(1'b0),.v_display_ack(display_ack),
 .h_start(1'b0),.h_kind(2'd0),.h_index(4'd0),.h_valid(1'b0),.h_data(8'd0),.context_valid(1'b0),.context_data(8'd0),
 .transport_crc_pending(1'b0),.transport_empty(1'b1),.transport_crc(16'd0),.transport_byte(8'd0),
 .stream_valid(1'b0),.stream_data(8'd0),.sink_ready(1'b0),
 .display_lease(1'b1),.display_generation(f[15:0]),.display_epoch(32'd1),.range_external(1'b0),.range_dma_done(1'b0),
 .frame_owned(1'b1),.geometry_valid(1'b1),.frame_generation(f[15:0]),.content_epoch(32'd1),.frame_serial(f),.patch_count(3'd0),
 .row_count(8'd224),.object_count(8'd0),.exception_count(8'd0),.group_count(6'd1),.palette_count(6'd1),
 .query(query),.query_kind(qkind),.query_index(qi),.raw_response(response),.raw_hit(1'b1),.raw_data(raw),
 .record_valid(rv),.record_ready(record_ready),.record_length(len),.byte_valid(bv),.byte_ready(byte_ready),.byte_data(data),
 .ack_valid(ack_valid),.ack_ready(ack_ready),.ack_accept(1'b1),.ack_generation(f[15:0]),.done(done),.fault(fault));
 reg held=0;reg[7:0] held_data;
 always @(posedge clk)begin
  ticks<=ticks+1;aq<=memory[aa];bq<=memory[ba];if(awe)memory[aa]<=aw;if(bwe)memory[ba]<=bw;
  response<=query;
  if(query)begin
   raw<=0;
   if(qkind==0)begin if(qi>=33)$fatal(1,"map query bounds");raw<={48'd0,maps[qi]};end
   else if(qkind==1)raw<=qi[0]?64'h12:64'h34;
   else if(qkind==4)raw<=64'h0000018000000000;
  end
  if(!reset&&!abort_source&&!fault)begin
   if(held&&(!bv||data!==held_data))$fatal(1,"unstable stalled output");
   if(dut.state==dut.BUILD344&&dut.mask_pending278)$fatal(1,"build/write collision");
   if(awe&&(dut.state==dut.FSTORE||dut.state==dut.BUILD344||dut.mask_pending278)&&(aa<768||aa>=844))$fatal(1,"record bounds");
  end
  held<=bv&&!byte_ready;held_data<=data;
  if(rv&&record_ready)begin $fwrite(fd,"%0d %0d ",f,len);at=0;end
  if(bv&&byte_ready)begin $fwrite(fd,"%02x",data);at=at+1;if(at==len)$fwrite(fd,"\n");end
 end
 parameter integer NEG=0;
 initial begin
  reg[7:0] frozen[0:1023];
  if(NEG!=0)begin
   if(NEG==1)wait(f==2&&dut.state==dut.BUILD344&&dut.kind==dut.SHIFT&&dut.build_i==1);
   else wait(f==1&&dut.state==dut.BUILD344&&dut.kind==dut.REPEAT348&&dut.build_i==1);
   @(negedge clk);abort_source=1;repeat(4)@(negedge clk);
   if(fault!=4||rv||bv||ack_ready)$fatal(1,"SHIFT STOP not terminal");
   for(integer j=0;j<1024;j++)frozen[j]=memory[j];
   repeat(256)@(negedge clk);
   for(integer j=0;j<1024;j++)if(frozen[j]!==memory[j])$fatal(1,"write after SHIFT STOP");
   $display("PASS RECORD344 SHIFT STOP");$finish;
  end
 end
 initial begin
  fd=$fopen("records.txt","w");for(integer j=0;j<1024;j++)memory[j]=8'ha5;
  for(integer j=0;j<33;j++)maps[j]=16'h100+j;
  repeat(4)@(negedge clk);reset=0;
  for(f=1;f<=4;f=f+1)begin
   if(f==2)begin for(integer j=0;j<32;j++)maps[j]=maps[j+1];maps[32]=16'h222;end
   if(f==3)begin for(integer j=32;j>0;j--)maps[j]=maps[j-1];maps[0]=16'h333;end
   wait(ready);@(negedge clk);start=1;@(negedge clk);start=0;
   wait(ack_ready);@(negedge clk);ack_valid=1;@(negedge clk);ack_valid=0;
   wait(done);@(negedge clk);display_ack=1;@(negedge clk);display_ack=0;
  end
  $fclose(fd);if(fault)$fatal(1,"source fault %0d",fault);
  $display("PASS RECORD344 SOURCE4");$finish;
 end
 initial begin #10000000;$fatal(1,"source timeout");end
endmodule
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);o=ap.parse_args();d=o.out.resolve();d.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 shutil.copyfile(o.source/'nes_core257.sv',d/'nes_core257.sv');(d/'record344_tb.sv').write_text(TB,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 def run(exe,args,cwd,label):
  with (cwd/(label+'.log')).open('wb') as log:r=subprocess.run([str(q/exe),*args],cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(cwd/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-3000:];return text
 run('vlib.exe',['work'],d,'vlib');run('vlog.exe',['-sv','nes_core257.sv','record344_tb.sv'],d,'vlog')
 log=run('vsim.exe',['-c','work.record344_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim');assert 'PASS RECORD344 SOURCE4' in log
 rows={f:[] for f in range(1,5)}
 for line in (d/'records.txt').read_text().splitlines():
  f,n,b=line.split();v=bytes.fromhex(b);assert len(v)==int(n);rows[int(f)].append(v)
 old=bytes(4398);prior_raw=None;maps=list(range(0x100,0x121));counts=[]
 for f in range(1,5):
  if f==2:maps=maps[1:]+[0x222]
  if f==3:maps=[0x333]+maps[:-1]
  g=bytearray(4398);g[:66]=b''.join(x.to_bytes(2,'little') for x in maps);g[2112:2336]=bytes([0x34,0x12])*112;g[4320]=0x18
  g[4385:4397]=b''.join(x.to_bytes(2,'little') for x in (33,224,0,0,224,32))
  want=encode280(old,bytes(g),b'',prior_raw,f,f);assert rows[f]==want,(f,rows[f][:2],want[:2])
  shifts=[r for r in rows[f] if r[0]&128 and (r[0]&127)<32];counts.append(len(shifts));old=bytes(g);prior_raw=b''
 assert counts==[0,1,1,0]
 neg=d/'stop';neg.mkdir();shutil.copytree(d/'work',neg/'work')
 nlog=run('vsim.exe',['-c','work.record344_tb','-gNEG=1','-do','onerror {quit -code 1};run -all;quit -f'],neg,'vsim');assert 'PASS RECORD344 SHIFT STOP' in nlog
 neg2=d/'repeat-stop';neg2.mkdir();shutil.copytree(d/'work',neg2/'work')
 nlog2=run('vsim.exe',['-c','work.record344_tb','-gNEG=2','-do','onerror {quit -code 1};run -all;quit -f'],neg2,'vsim');assert 'PASS RECORD344 SHIFT STOP' in nlog2
 assert any(r[0]&128 and (r[0]&127)>=32 and r[0]!=255 and r[1]==2 for r in rows[1])
 r=dict(passed=True,repeat16=True,repeat_build_STOP=True,frames=4,SHIFT_counts=counts,stall=True,SHIFT_build_STOP=True,RTL_sha256=sha(d/'nes_core257.sv'),TB_sha256=sha(d/'record344_tb.sv'),log_sha256=sha(d/'vsim.log'),stop_log_sha256=sha(neg/'vsim.log'),records_sha256=sha(d/'records.txt'),scope=__doc__)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps(r))
if __name__=='__main__':main()
