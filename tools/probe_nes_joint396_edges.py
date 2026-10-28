# SPDX-License-Identifier: MIT
"""Independent ABI boundary vectors and shared cursor reset/arbitration."""
import argparse,json,random,shutil,struct,subprocess
from pathlib import Path
from nes_delta231 import ROOT,sha

def valid(raw,bank):
 d,s,n,f,w,v,r,c=struct.unpack('<HHHBBBBH',raw);mode=(f>>2)&3;ref=bool(f&16);stride=bool(f&32);zero=bool(f&64)
 if f&128 or not n or r>5 or c>=8192:return False
 if r<2:
  unit=16 if r==0 else 32
  return f==0 and n<=2048 and n%unit==0 and c+n//unit<=(1024 if r==0 else 128) and w==126 and v==128 and s>=32768 and s+n<=40960 and d==(bank*24576+c*8 if r==0 else 8192+bank*8192+c*16)
 # A stride column stays inside its 32-row SNES screen; canonical bit10 selects the second screen.
 if r==2:return not ref and not zero and mode==1 and f&3==0 and n%2==0 and w==126 and 49152<=s and s+n<=53248 and c<2048 and (((c%1024)//32 if stride else c)+n//2<=(32 if stride else 2048)) and v==(129 if stride else 128) and d==12288+bank*8192+c
 domain,base=((512,24576),(544,25088),(3418,25856))[r-3]
 return not stride and w==127 and v==0 and c+n<=domain and s==base+bank*32768+c and ((r!=5 and c==0 and mode==0 and n==domain and f&3==(1 if r==3 else 2)) if ref else (f&3==3 and mode!=0 and d==0)) and (not zero or (r==5 and c==21 and n==1100 and mode==2))

TB=r'''`timescale 1ns/1ps
module edge396_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,start=0,bank=0;reg[95:0] record;wire done,bad;
 nes_check396 check396(.*);
 reg sr=0,pr=0;wire sc,pc;wire[2:0] si;
 nes_walk396 walk(.clk(clk),.reset(reset),.source_request(sr),.plan_request(pr),.source_capture(sc),.plan_capture(pc),.source_index(si));
 reg[97:0] vectors[0:COUNT-1];integer ticks,seen;
 task tick;begin @(posedge clk);#1;end endtask
 initial begin
  $readmemh("vectors.hex",vectors);repeat(3)tick();reset=0;
  for(integer i=0;i<COUNT;i++)begin
   @(negedge clk);{bank,record}=vectors[i][96:0];start=1;tick();@(negedge clk);start=0;ticks=0;
   while(!done&&ticks<100)begin tick();ticks++;end
   if(!done||bad!==vectors[i][97])$fatal(1,"ABI vector%0d bank%0d record%h bad%0d expected%0d",i,bank,record,bad,vectors[i][97]);
  end
  // Both clients request: the six source writes are ordered and indivisible.
  @(negedge clk);sr=1;pr=1;seen=0;
  while(seen<6)begin @(posedge clk);if(pc)$fatal(1,"plan overtook source");if(sc)begin if(si!=seen)$fatal(1,"footer cursor");seen++;end #1;end
  @(negedge clk);sr=0;seen=0;
  repeat(10)begin @(posedge clk);if(pc)seen++;#1;end
  if(seen<2)$fatal(1,"plan did not resume");
  // Reset during a pending plan and midway through every footer index.
  for(integer j=0;j<6;j++)begin
   @(negedge clk);reset=1;#1;if(sc||pc)$fatal(1,"reset published capture");tick();@(negedge clk);reset=0;sr=1;pr=1;
   ticks=0;while(!(sc&&si==j)&&ticks<30)begin tick();ticks++;end
   if(ticks==30)$fatal(1,"source not scheduled");
  end
  @(negedge clk);reset=1;sr=0;pr=0;repeat(3)tick();@(negedge clk);reset=0;
  repeat(12)begin tick();if(sc||pc)$fatal(1,"DONE after reset without request");end
  $display("EDGES396 PASS vectors=%0d source_priority=1 reset_indices=6 post_stop_done=0",COUNT);$finish;
 end
 initial begin #100000000;$fatal(1,"edge timeout");end
endmodule
'''

STAGE=r'''`timescale 1ns/1ps
module stage396_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,active=1,begin_valid=0,begin_tile=0,byte_valid=0,seal=0,consume=0;
 reg[11:0] begin_length=0;reg[31:0] begin_token=1,consume_token=1;
 reg[15:0] generation=7;reg kind=1;reg[9:0] first=0;
 reg[7:0] byte_data=0;wire begin_ready,byte_ready,producer_error,chunk_ready,consume_error;
 reg word_valid=0,word_end=0,word_kind=1;reg[15:0]word_generation=7;reg[9:0]word_slot=0;reg[5:0]word_length=32;
 wire word_ready,meta_write,tile_empty;wire[9:0]meta_address;wire[7:0]meta_data;reg[7:0]meta_q;
 reg[7:0] metadata[0:1023];
 always @(posedge clk)begin meta_q<=metadata[meta_address];if(meta_write)metadata[meta_address]<=meta_data;end
 reg[23:0]address=24'h400800;reg read_n=0,write_n=1;wire[7:0]data_out;wire oe_n;
 nes_stage396 dut(.*);
 task tick;begin @(posedge clk);#1;if(producer_error||consume_error)$fatal(1,"stage error");end endtask
 task tile(input integer slot);integer n;begin
  @(negedge clk);for(integer i=0;i<word_length;i++)metadata[i]=slot^i^8'h5a;word_slot=slot;word_valid=1;n=0;
  while(!word_ready&&n<200)begin tick();n++;end
  if(!word_ready)$fatal(1,"prefill stalled slot%0d",slot);
  tick();@(negedge clk);word_valid=0;tick();
 end endtask
 task open_job(input integer is_tile,len,slot);integer n;begin
  @(negedge clk);begin_tile=is_tile;begin_length=len;first=slot;begin_valid=1;
  if(!begin_ready)$fatal(1,"begin busy");tick();@(negedge clk);begin_valid=0;
  if(is_tile)begin n=0;while(!chunk_ready&&n<2000)begin tick();n++;end if(!chunk_ready)$fatal(1,"binding stalled");end
 end endtask
 task verify(input integer is_tile,len,slot);reg[7:0]expect_byte;begin
  for(integer i=0;i<len;i++)begin
   @(negedge clk);address=24'h400800+i;repeat(5)tick();
   expect_byte=is_tile?((slot+i/(kind?32:16))^(i%(kind?32:16))^8'h5a):(i^8'ha6);
   if(oe_n||data_out!==expect_byte)$fatal(1,"data mismatch byte%0d got%h expected%h oe%0d",i,data_out,expect_byte,oe_n);
  end
  @(negedge clk);consume=1;consume_token=begin_token;tick();@(negedge clk);consume=0;begin_token++;repeat(2)tick();
  if(chunk_ready||!oe_n)$fatal(1,"consumed aperture still visible");
 end endtask
 initial begin
  repeat(3)tick();@(negedge clk);reset=0;
  for(integer i=0;i<112;i++)tile(i);
  if(dut.used!=3584||dut.stamps!=112||!oe_n)$fatal(1,"full prefill state");
  // A full unpublished tile FIFO must not block the reserved ordinary region.
  open_job(0,512,0);
  for(integer i=0;i<512;i++)begin @(negedge clk);byte_valid=1;byte_data=i^8'ha6;if(!byte_ready)$fatal(1,"ordinary credit");tick();end
  @(negedge clk);byte_valid=0;seal=1;tick();@(negedge clk);seal=0;verify(0,512,0);
  if(dut.used!=3584)$fatal(1,"ordinary consumed tile");
  open_job(1,2048,0);verify(1,2048,0);
  for(integer i=0;i<64;i++)tile(i);
  if(dut.used!=3584)$fatal(1,"wrap occupancy");
  open_job(1,1536,64);verify(1,1536,64);
  open_job(1,2048,0);verify(1,2048,0);
  if(!tile_empty)$fatal(1,"not drained");
  // BG16B tiles fill all192 stamps before the byte FIFO; wrap both rings.
  kind=0;word_kind=0;word_length=16;
  for(integer i=0;i<192;i++)tile(i);
  if(dut.stamps!=192||dut.used!=3072)$fatal(1,"stamp capacity");
  @(negedge clk);word_valid=1;word_slot=192;
  repeat(12)begin tick();if(word_ready||meta_write||dut.used!=3072)$fatal(1,"stamp overflow accepted");end
  @(negedge clk);word_valid=0;
  open_job(1,2048,0);verify(1,2048,0);
  for(integer i=192;i<256;i++)tile(i);
  open_job(1,2048,128);verify(1,2048,128);
  if(!tile_empty)$fatal(1,"stamp wrap not drained");
  // Cancel a partially copied mailbox and ensure neither publication nor writes.
  @(negedge clk);word_valid=1;word_slot=77;repeat(4)tick();@(negedge clk);reset=1;word_valid=0;
  repeat(5)begin tick();if(meta_write||word_ready||chunk_ready||!oe_n)$fatal(1,"STOP leak");end
  @(negedge clk);reset=0;repeat(8)tick();if(!tile_empty||chunk_ready)$fatal(1,"DONE after STOP");
  $display("STAGE396 PASS full3584 ordinary512 full192stamps wrap=1 reads=10240 cancel_midcopy=1");$finish;
 end
 initial begin #2000000;$fatal(1,"stage timeout");end
endmodule
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 vectors=set();rng=random.Random(396)
 for q in sorted(a.arm.glob('jobs*.json')):
  bank=(int(q.stem[4:])-905)%2
  for j in json.loads(q.read_text()):
   raw=bytes.fromhex(j['record']);vectors.add((raw,bank))
   for bit in range(96):
    b=bytearray(raw);b[bit//8]^=1<<(bit%8);vectors.add((bytes(b),bank))
   for at in(0,2,4,10):
    for value in(0,1,15,16,31,32,127,128,511,512,1023,1024,2047,2048,2049,3418,3584,8191,8192,32767,32768,40960,49152,53248,65535):
     b=bytearray(raw);b[at:at+2]=struct.pack('<H',value);vectors.add((bytes(b),bank))
 # Deterministic sample of all recorded-record mutations; full normal replay is separate.
 vectors=sorted(vectors);rng.shuffle(vectors);vectors=vectors[:24000]
 (d/'vectors.hex').write_text('\n'.join(f'{(int(not valid(raw,b))<<97)|(b<<96)|int.from_bytes(raw,"little"):025x}'for raw,b in vectors)+'\n')
 for name in('nes_check396.sv','nes_walk396.sv','nes_stage396.sv'):shutil.copyfile(ROOT/'src/fpga/nes_joint396'/name,d/name)
 (d/'edge396_tb.sv').write_text(TB.replace('COUNT',str(len(vectors))))
 (d/'stage396_tb.sv').write_text(STAGE)
 exe=Path('C:/altera_standard/25.1std/questa_fse/win64')
 for name,args in [('vlib',['work']),('vlog',['-sv','nes_check396.sv','nes_walk396.sv','nes_stage396.sv','edge396_tb.sv','stage396_tb.sv']),('vsim',['-c','work.edge396_tb','-do','onerror {quit -code 1};run -all;quit -f']),('stage',['-c','work.stage396_tb','-do','onerror {quit -code 1};run -all;quit -f'])]:
  with(d/(name+'.log')).open('wb')as log:r=subprocess.run([str(exe/(('vsim'if name=='stage'else name)+'.exe'))]+args,cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=100,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-3000:]
 assert 'EDGES396 PASS'in(d/'vsim.log').read_text()
 assert 'STAGE396 PASS'in(d/'stage.log').read_text()
 result=dict(passed=True,vectors=len(vectors),oracle='unbounded integer ABI bounds; per-field boundary and one-bit mutation',cursor=dict(source_priority=True,reset_indices=6,post_reset_done=False),pins={q.name:sha(q)for q in d.iterdir()if q.is_file()})
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
