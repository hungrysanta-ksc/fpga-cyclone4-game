# SPDX-License-Identifier: MIT
"""Compare old/new plan fields with real256-host-cycle ingress and dual clocks."""
import argparse,json,os,shutil,subprocess,re
from pathlib import Path
from nes_delta231 import BASE,sha
from nes_plan348 import apply
TB=r'''
module plan348_tb;
 parameter integer STOP348=0,BAD348=0;
 reg hc=0,nc=0;always #5 hc=~hc;always #23 nc=~nc;
 reg reset=1,stop=0,write_valid=0,seal=0,retire=0;
 reg[7:0] wd;reg[9:0] sl;reg[4:0] sp;reg[15:0] generation;
 wire[1:0] wr,hi,pv,ev,ef,td,pr,ep,rc,rd;
 reg[1:0] tile_done=0;wire[1:0] zr,st;
 reg[9:0] cursor[0:1];integer cycles=0,fd[0:1],seen[0:1];
 wire[1:0] kind[0:1];wire[15:0] gen[0:1];wire[9:0] slot[0:1];wire[12:0] tag[0:1];
 wire[47:0] rows[0:1];wire[7:0] mask[0:1],amask[0:1];wire[103:0] alt[0:1];
 genvar g;generate for(g=0;g<2;g=g+1)begin:units
 wire p_ready=cycles%7!=0;integer delay_count=0;reg running=0;
 if(g==0)nes_plan_reference #(.SHARED_CRC307(1)) dut(
 .host_clk(hc),.nes_clk(nc),.reset(reset),.active(1'b1),.stop(stop),.source_fault(1'b0),
 .plan_cursor319(cursor[g]),.plan_zero319(zr[g]),.plan_step319(st[g]),
 .write_valid(write_valid),.write_ready(wr[g]),.write_data(wd),.retire(retire),.retire_done(rd[g]),.retire_permitted(1'b1),.retire_commit(rc[g]),
 .seal(seal),.seal_length(sl),.seal_plans(sp),.seal_crc(16'd0),.host_idle(hi[g]),.fault(ef[g]),
 .lease_valid(1'b1),.lease_generation(generation),.plan_valid(pv[g]),.plan_ready(p_ready),.tile_done(tile_done[g]),
 .plan_kind(kind[g]),.plan_generation(gen[g]),.plan_slot(slot[g]),.plan_tag(tag[g]),.plan_rows(rows[g]),.plan_mask(mask[g]),.plan_alt_mask(amask[g]),.plan_alt_tags(alt[g]),
 .end_valid(ev[g]),.end_partial295(ep[g]),.end_ready(p_ready),.end_generation());
 else nes_plan_batch206 #(.SHARED_CRC307(1)) dut(
 .host_clk(hc),.nes_clk(nc),.reset(reset),.active(1'b1),.stop(stop),.source_fault(1'b0),
 .plan_cursor319(cursor[g]),.plan_zero319(zr[g]),.plan_step319(st[g]),
 .write_valid(write_valid),.write_ready(wr[g]),.write_data(wd),.retire(retire),.retire_done(rd[g]),.retire_permitted(1'b1),.retire_commit(rc[g]),
 .seal(seal),.seal_length(sl),.seal_plans(sp),.seal_crc(16'd0),.host_idle(hi[g]),.fault(ef[g]),
 .lease_valid(1'b1),.lease_generation(generation),.plan_valid(pv[g]),.plan_ready(p_ready),.tile_done(tile_done[g]),
 .plan_kind(kind[g]),.plan_generation(gen[g]),.plan_slot(slot[g]),.plan_tag(tag[g]),.plan_rows(rows[g]),.plan_mask(mask[g]),.plan_alt_mask(amask[g]),.plan_alt_tags(alt[g]),
 .end_valid(ev[g]),.end_partial295(ep[g]),.end_ready(p_ready),.end_generation());
 always @(posedge nc)begin
  if(reset||stop)begin cursor[g]<=0;running<=0;tile_done[g]<=0;end
  else begin
   if(zr[g])cursor[g]<=0;else if(st[g])cursor[g]<=cursor[g]+1'b1;
   tile_done[g]<=0;
   if((pv[g]||ev[g])&&p_ready)begin
    $fwrite(fd[g],"%0d %0d %0d %0d %0d %012x %02x %02x %026x %0d\n",generation,kind[g],gen[g],slot[g],tag[g],rows[g],mask[g],amask[g],alt[g],ep[g]);seen[g]=seen[g]+1;
    if(pv[g])begin running<=1;delay_count<=100;end
   end
   if(running)begin
    if(delay_count==0)begin tile_done[g]<=1;running<=0;end else delay_count<=delay_count-1;
   end
  end
 end
 end endgenerate
 always @(posedge nc)begin cycles<=cycles+1;if(!reset&&!stop&&ef&&!BAD348)$fatal(1,"plan fault %b ref hf=%0d nf=%0d closed=%0d state=%0d word=%0d retire=%0d",ef,units[0].genblk1.dut.hf,units[0].genblk1.dut.nf,units[0].genblk1.dut.closed,units[0].genblk1.dut.state,units[0].genblk1.dut.word_valid,retire);end
 reg[7:0] bytes[0:65535];integer size,total=0,at=0,n,k,np;
 initial begin
  fd[0]=$fopen("reference.txt","w");fd[1]=$fopen("candidate.txt","w");seen[0]=0;seen[1]=0;
  if(BAD348)$readmemh($sformatf("bad%0d.hex",BAD348),bytes);else $readmemh("input.hex",bytes);size=bytes[0]+256*bytes[1];at=2;
  while(at<size)begin
   reset=1;repeat(10)@(negedge hc);generation=bytes[at]+256*bytes[at+1];at=at+2;reset=0;repeat(10)@(negedge hc);
   np=bytes[at];at=at+1;
   for(k=0;k<np;k=k+1)begin
    n=bytes[at]+256*bytes[at+1];sp=bytes[at+2];sl=n;at=at+3;total=total+sp;
    wait(&hi);
    for(integer j=0;j<n;j=j+1)begin
     repeat(255)@(negedge hc);
     if(wr!=3)$fatal(1,"ingress missed256-clock deadline %b",wr);
     wd=bytes[at];at=at+1;write_valid=1;@(negedge hc);write_valid=0;
    end
    repeat(40)@(negedge hc);seal=1;@(negedge hc);seal=0;
    if(BAD348)begin wait(ef==3);repeat(64)@(negedge hc);if(pv||ev)$fatal(1,"malformed exposed plan");$display("PASS PLAN348 MALFORMED %0d",BAD348);$finish;end
   end
   wait(seen[0]==total&&seen[1]==total);repeat(500)@(negedge hc);
   retire=1;@(negedge hc);retire=0;repeat(500)@(negedge hc);
  end
  if(seen[0]!=seen[1])$fatal(1,"plan count");$display("PASS PLAN348 %0d",total);$finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
 initial if(STOP348)begin
  reg [7:0] frozen[0:1023];
  wait(units[1].genblk1.dut.clear348);@(negedge hc);stop=1;
  repeat(8)@(negedge hc);
  if(pv||ev||wr||hi)$fatal(1,"STOP exposes plan");
  for(integer j=0;j<1024;j++)frozen[j]=units[1].genblk1.dut.payload[j];
  repeat(64)@(negedge hc);
  for(integer j=0;j<1024;j++)if(frozen[j]!==units[1].genblk1.dut.payload[j])$fatal(1,"clear wrote after STOP");
  $display("PASS PLAN348 CLEAR STOP");$finish;
 end
endmodule
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);o=ap.parse_args();d=o.out;d.mkdir(parents=True,exist_ok=False)
 ref=BASE/'probes/nes-ingress338/window03'
 for n in ('nes_plan_batch206.sv','nes_domain_reset124.sv','nes_native_mailbox206.sv'):shutil.copyfile(ref/n,d/n)
 (d/'reference.sv').write_text((d/'nes_plan_batch206.sv').read_text().replace('module nes_plan_batch206','module nes_plan_reference'),newline='\n');apply(d)
 stream=bytearray(b'\0\0');expected=0
 for f in (905,906,907):
  b=(ref/f'actual-plans293-{f}.bin').read_bytes();at=0;count=0;generation=None
  while at<len(b):
   n=int.from_bytes(b[at:at+2],'little');np=b[at+2];x=b[at+3:at+3+n];g=int.from_bytes(x[1:3] if x[0]&128 else x[2:4],'little')
   if generation is None:generation=g
   assert g==generation
   at+=3+n;count+=1;expected+=np
  b+=bytes([3,0,1,0x83])+generation.to_bytes(2,'little');count+=1;expected+=1
  stream+=generation.to_bytes(2,'little')+bytes([count])+b
 for mask in range(256):
  generation=100+mask
  full=bytes([0,mask,generation&255,generation>>8,1,0,2,0,255,0x40,0x22,0x6d,0x64,0x6b,0xff,1])
  full+=b''.join((0x1200+i).to_bytes(2,'little') for i in range(8) if mask&(1<<i))
  end=bytes([3,0,generation&255,generation>>8])+bytes(11)+bytes([1])
  b=(len(full)+len(end)).to_bytes(2,'little')+bytes([2])+full+end
  stream+=generation.to_bytes(2,'little')+bytes([1])+b;expected+=2
 stream[:2]=len(stream).to_bytes(2,'little');(d/'input.hex').write_text(stream.hex(' ')+'\n')
 (d/'plan348_tb.sv').write_text(TB,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
 for exe,args in [('vlib',['work']),('vlog',['-sv','reference.sv','nes_plan_batch206.sv','nes_domain_reset124.sv','nes_native_mailbox206.sv','plan348_tb.sv']),('vsim',['-c','work.plan348_tb','-do','onerror {quit -code 1};run -all;quit -f'])]:
  with (d/f'{exe}.log').open('wb') as log:r=subprocess.run([str(q/f'{exe}.exe'),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=180)
  txt=(d/f'{exe}.log').read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',txt),txt[-4000:]
 assert f'PASS PLAN348 {expected}' in txt
 assert (d/'candidate.txt').read_bytes()==(d/'reference.txt').read_bytes()
 stop=d/'clear-stop';stop.mkdir();shutil.copytree(d/'work',stop/'work');shutil.copyfile(d/'input.hex',stop/'input.hex')
 with (stop/'vsim.log').open('wb') as log:r=subprocess.run([str(q/'vsim.exe'),'-c','work.plan348_tb','-gSTOP348=1','-do','onerror {quit -code 1};run -all;quit -f'],cwd=stop,stdout=log,stderr=subprocess.STDOUT,timeout=120)
 assert r.returncode==0 and 'PASS PLAN348 CLEAR STOP' in (stop/'vsim.log').read_text()
 malformed=[]
 full=bytearray([0,0,1,0,1,0,2,0,255,0x40,0x22,0x6d,0x64,0x6b,0xff,1])
 short=bytes([0x80,1,0,1,0,2,0])
 bad=[bytes([0xc0])+short[1:],bytes([4])+bytes(full[1:])]
 for pos,value in ((7,32),(5,4),(15,0)):
  b=bytearray(full);b[pos]=value;bad.append(bytes(b))
 bad.extend((short[:-1],short+b'\0',bytes([0,1])+bytes(full[2:])))
 for case,b in enumerate(bad,1):
  run=d/f'bad{case}';run.mkdir();shutil.copytree(d/'work',run/'work')
  blob=bytearray(b'\0\0\1\0\1')+len(b).to_bytes(2,'little')+bytes([1])+b
  blob[:2]=len(blob).to_bytes(2,'little');(run/f'bad{case}.hex').write_text(blob.hex(' ')+'\n')
  with (run/'vsim.log').open('wb') as log:r=subprocess.run([str(q/'vsim.exe'),'-c','work.plan348_tb',f'-gBAD348={case}','-do','onerror {quit -code 1};run -all;quit -f'],cwd=run,stdout=log,stderr=subprocess.STDOUT,timeout=120)
  assert r.returncode==0 and f'PASS PLAN348 MALFORMED {case}' in (run/'vsim.log').read_text(),case
  malformed.append(case)
 r=dict(passed=True,malformed=malformed,clear_STOP=True,plans=expected,recorded_frames=3,alt_masks=256,ingress_spacing_host_cycles=256,dual_clock=True,stall=True,RTL_sha256=sha(d/'nes_plan_batch206.sv'))
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
if __name__=='__main__':main()
