# SPDX-License-Identifier: MIT
"""Post-ACK queue lifetime, payload, manifest, cancellation negative tests."""
import argparse,json,os,shutil
from pathlib import Path
from probe_nes_joint265 import prepare,run
from nes_delta231 import sha,once


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src,pins,stats=prepare(d,905);s=(d/'joint265_tb.sv').read_text()
 s=once(s,'module joint265_tb;', 'module joint265_tb;parameter GNEG=0;integer hashes264=0;reg injected264=0;')
 s=s.replace('!reset&&active263)', '!reset&&active263&&!GNEG)')
 s=s.replace('&&!NEG)', '&&!NEG&&!GNEG)').replace('&&!NEG&&!PRENEG)', '&&!NEG&&!PRENEG&&!GNEG)')
 # Keep C as an oracle on successful runs. Mutated packets must reach RTL even
 # when the independent C oracle would reject them earlier.
 s=once(s,'events263=call263(2,n,0);','if(!GNEG)events263=call263(2,n,0);')
 s=once(s,'    ignore265=call263(2,n,0);internal265++;','    if(!GNEG)ignore265=call263(2,n,0);internal265++;')
 s=once(s,'    check_final265();','    if(!GNEG)check_final265();')
 s=once(s,'for(integer i=0;i<n;i++)begin rd261(24\'h400000+i,val263);', '''for(integer i=0;i<n;i++)begin
   if(GNEG==2&&i==n-1)begin val263=0;end else rd261(24'h400000+i,val263);''')
 s=once(s,'dut.flow.chunk_token!=tok263', '(dut.flow.chunk_token!=tok263&&GNEG!=8)')
 s=once(s,'    token261(token263);wr261', '    token261(token263+(GNEG==13));wr261')
 s=once(s,'token261(tok263);wr261', 'token261(GNEG==8?dut.flow.chunk_token:tok263);wr261')
 s=once(s,"  wr261(24'h006010,p263[0]==3?1:0);", "  if(GNEG==1)p263[2]=p263[2]^1;\n  wr261(24'h006010,p263[0]==3?1:0);")
 # Change real SPI packet bytes, recompute its transport CRC. This tests semantic
 # validation, not merely the outer SPI CRC detector.
 s=once(s,'tx[j+1]=all263[at+j];crc263=', '''tx[j+1]=all263[at+j];
      if(!injected264)begin
       if(GNEG==5&&all263[at]==15&&j==184)begin tx[j+1]=tx[j+1]^1;injected264=1;end
       if(GNEG==6&&all263[at]==2&&all263[at+1]==5&&all263[at+10]==0&&j==17)begin tx[j+1]=tx[j+1]^1;injected264=1;end
       if(GNEG==7&&all263[at]==10&&j==10)begin tx[j+1]=1;injected264=1;end
       if(GNEG==8&&all263[at]==7&&j==16)begin tx[j+1]=tx[j+1]^1;injected264=1;end
       if(GNEG==9&&all263[at]==15&&j==0)begin tx[j+1]=10;injected264=1;end
       if(GNEG==10&&all263[at]==10&&j==16)begin tx[j+1]=tx[j+1]^1;injected264=1;end
       if(GNEG==14&&all263[at]==7&&j==8)begin tx[j+1]=tx[j+1]^1;injected264=1;end
       if(GNEG==15&&all263[at]==14&&j==1)begin tx[j+1]=tx[j+1]^1;injected264=1;end
       if(GNEG==16&&all263[at]==7&&j==2)begin tx[j+1]=0;injected264=1;end
       if(GNEG==17&&all263[at]==10&&j==0)begin tx[j+1]=3;injected264=1;end
       if(GNEG==11&&all263[at]==2&&all263[at+1]==3&&j==10)begin tx[j+1]=1;injected264=1;end
      end
      if((GNEG==18||GNEG==19)&&all263[at]==10&&all263[at+10]==0)begin
       if(j==0)tx[j+1]=11;
       if(GNEG==19)begin
        if(j==16)tx[j+1]=3;
        if(j==17||j==146)tx[j+1]=127;
       end
      end
      crc263=''')
 s=once(s,"  for(integer i=2;i<10;i++)wr261(24'h006010+i,p263[i]);", """  for(integer i=2;i<10;i++)begin
   if(GNEG==20&&i==3)continue;
   wr261(24'h006010+i,p263[i] ^ ((GNEG==21&&i==4)?1:0));
   if(GNEG==22&&i==2)wr261(24'h006010+i,p263[i]);
  end""")
 s=once(s,"wr261(24'h00601a,8'h65);wr261(24'h00601b,8'h9a);wr261(24'h00601c,8'ha5);\n  wait(dut.flow.queue.retired!=head265);", """if(GNEG!=27)wr261(24'h00601a,GNEG==28?8'h64:8'h65);
  wr261(24'h00601b,8'h9a);wr261(24'h00601c,8'ha5);
  wait(dut.flow.queue.retired!=head265);""")
 s=once(s,"     rd261(24'h006070+j,val263);", """     if(GNEG==23&&j==23)continue;
     if(GNEG==24&&j==0)begin
      bus_address=24'h006071;bus_read=0;#400;bus_read=1;wait(source_fault);
     end
     rd261(24'h006070+j,val263);""")
 s=once(s,"if(GNEG==1)p263[2]=p263[2]^1;", "if(GNEG==1)p263[2]=p263[2]^1;if(GNEG==29)p263[2]=p263[2]-1'b1;")
 s=once(s,'endmodule', '''
 always @(posedge clk)if(dut.h_valid&&h_ready)hashes264++;
 initial begin : cancel264
  if(GNEG==3||GNEG==4)begin
   wait(hashes264==8);@(negedge clk);disable bus263;
   bus_read=1;bus_write=1;repeat(8)@(negedge host_clk);
   if(GNEG==3)test_abort=1;else begin token261(dut.flow.last_map_token);wr261(24'h006058,8'h5a);end
  end
  if(GNEG==25||GNEG==26)begin
   wait(dut.flow.state==dut.flow.OSETUP&&dut.flow.header[0]==15);
   @(negedge host_clk);disable bus263;bus_read=1;bus_write=1;repeat(8)@(negedge host_clk);
   if(GNEG==25)wr261(24'h00601c,8'ha5);else begin wait(dut.core.encoder.cursor>8);test_abort=1;end
  end
  if(GNEG==12)begin
   wait(dut.flow.state==dut.flow.OSETUP);@(negedge host_clk);disable bus263;
   bus_read=1;bus_write=1;repeat(8)@(negedge host_clk);wr261(24'h00601c,8'ha5);
  end
 end
 initial begin : result264
 reg [7:0] frozen[0:1023];
 if(GNEG)begin
  wait(source_fault);disable bus263;repeat(4)@(negedge clk);
  if(v_sealed||lease_valid||staged||rack||flow_retired)$fatal(1,"postfault completion");
  for(integer i=0;i<1024;i++)frozen[i]=dut.core.memory[i];
  repeat(256)@(negedge clk);
  for(integer i=0;i<1024;i++)if(frozen[i]!==dut.core.memory[i])$fatal(1,"postfault RAM write");
  $display("PASS DIRECT265 GNEG=%0d fault=%0d hashbytes=%0d",GNEG,source_fault,hashes264);$finish;
 end
 end
 initial begin #150000000;if(GNEG)$fatal(1,"guard264 timeout");end
endmodule''')
 (d/'joint265_tb.sv').write_text(s,encoding='utf-8',newline='\n')
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer264.c','-o','producer263.dll'],d,'native')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint265_tb.sv'],d,'vlog');guards=[]
 for i in range(1,30):
  log=run(a.questa_bin/'vsim.exe',['-c','-sv_lib','producer263','work.joint265_tb',f'-gGNEG={i}','+LAST=905','-do','onerror {quit -code 1};run -all;quit -f'],d,f'guard{i}',120)
  assert f'PASS DIRECT265 GNEG={i}' in log;guards.append(i)
 r=dict(passed=True,guards=guards,rtl_hashes={n:sha(d/n) for n in src},TB_sha256=sha(d/'joint265_tb.sv'),scope=__doc__)
 shutil.copyfile(__file__,d/'guard_nes_joint265.py');(d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=True,guards=guards)))


if __name__=='__main__':main()
