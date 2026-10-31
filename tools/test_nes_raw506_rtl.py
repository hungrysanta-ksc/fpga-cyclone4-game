# SPDX-License-Identifier: MIT
"""Actual exporter506 delayed-query/backpressure and cancellation test."""
import argparse,json,shutil,struct,subprocess
from pathlib import Path
from nes_raw506 import encode,sha
TB=r'''
module tb;
reg clk=0;always #5 clk=~clk;
reg reset=1,enable=0,owned=0;reg[15:0] generation;
reg[5:0] groups,palettes;reg[7:0] objects,exceptions;reg[2:0] patches;
wire query,valid,release_frame;wire[2:0]kind;wire[12:0]index;wire[15:0]qgen;wire[95:0]tx;wire[3:0]state,error;
reg response=0,hit=0;reg[63:0]data;reg[63:0]mem[0:65535];reg[95:0]expected[0:4095];
integer cycle=0,pending=0,qaddr=0,at=0,count=0,cases,logfd,ret,g,c0,c1,c2,c3,c4,c5,c6,mode,queries=0,total=0;
reg[95:0]held;reg holding=0;reg finished=0;
wire ready=(cycle%7!=0 && cycle%7!=1);
nes_native_export203 dut(.clk(clk),.reset(reset),.enable(enable),.frame_owned(owned),.geometry_valid(1'b1),.frame_generation(generation),
 .patch_count(patches),.row_count(8'd224),.object_count(objects),.exception_count(exceptions),.group_count(groups),.palette_count(palettes),
 .query(query),.query_kind(kind),.query_index(index),.query_generation(qgen),.response(response),.hit(hit),.data(data),
 .tx_valid(valid),.tx_ready(ready),.tx_data(tx),.ack_valid(state==8),.ack_ready(),.ack_accept(1'b1),.ack_generation(generation),.release_frame(release_frame),.observe_state177(state),.error(error),.busy());
always @(posedge clk)begin
 cycle<=cycle+1;response<=0;
 if(reset)begin pending<=0;holding<=0;end else begin
  if(pending>0)begin
   pending<=pending-1;
   if(pending==1)begin response<=1;hit<=1;data<=mem[qaddr];end
  end else if(query)begin pending<=1+cycle%4;qaddr<={kind,index};queries=queries+1;end
  if(holding && valid && tx!==held)$fatal(1,"unstable backpressure");
  holding<=valid&&!ready;held<=tx;
  if(mode==2 && kind==7 && index>=128 && state==3)enable<=0;
  if(valid && ready)begin
   if(mode==2 && tx[95:93]==7 && tx[76:64]==3)$fatal(1,"COMMIT after raw STOP");
   if(mode==0)begin
    if(at>=count||tx!==expected[at])$fatal(1,"record mismatch gen=%0d at=%0d got=%h expected=%h",generation,at,tx,expected[at]);
    $fwrite(logfd,"%0d,%0d,%0d,%0d,%024h\n",generation,at,cycle,queries,tx);at=at+1;
    if(at==count)finished=1;
   end else if(tx[95:93]==7 && tx[76:64]==2)begin
    if(error!==(mode==2?4'd1:4'd3))$fatal(1,"wrong rejection %0d",error);finished=1;
   end
  end
 end
 if(cycle>2000000)$fatal(1,"watchdog");
end
initial begin
 cases=$fopen("cases.txt","r");logfd=$fopen("records.csv","w");$fwrite(logfd,"generation,record,cycle,queries,word\n");
 while(!$feof(cases))begin
  ret=$fscanf(cases,"%d %d %d %d %d %d %d %d %d %d\n",g,c0,c1,c2,c3,c4,c5,c6,count,mode);
  if(ret==10)begin
   @(negedge clk);reset=1;enable=0;owned=0;repeat(4)@(negedge clk);
   $readmemh($sformatf("input-%0d.hex",g),mem);$readmemh($sformatf("expect-%0d.hex",g),expected,0,count-1);
   generation=g;groups=c0/33;palettes=c5/32;objects=c2;exceptions=c3;patches=c6;
   if(mode==1)mem[16'he000]=64;
   queries=0;at=0;finished=0;reset=0;owned=1;enable=1;
   while(!finished)@(negedge clk);
   if(mode==2)repeat(20)@(negedge clk);
   total=total+1;$display("PASS506 gen=%0d mode=%0d records=%0d queries=%0d",g,mode,at,queries);
  end
 end
 $fclose(cases);$fclose(logfd);$display("PASS506 total=%0d",total);$finish;
end
endmodule
'''
def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False);shutil.copy2(a.exporter,a.out/'nes_native_export203.sv');(a.out/'tb.sv').write_text(TB)
    cases=[]
    for g in list(range(905,917))+[1000,1001,1002,1003]:
        geom=(a.data/f'frame{min(g,905)if g>=1000 else g}.geometry').read_bytes();raw=(a.data/f'frame{min(g,905)if g>=1000 else g}.raw').read_bytes()
        if g==1000:raw=bytes([63])*512
        if g==1001:raw=bytes([0,63])*256
        packets,counts,arrays=encode(geom,raw,g);mode=1 if g==1002 else 2 if g==1003 else 0
        lines=[]
        for k,values in list(enumerate(arrays))+[(7,list(raw))]:
            if values:lines+=['@%04x'%(k<<13)]+['%016x'%v for v in values]
        lines+=['@ffff','0000000000000000'];(a.out/f'input-{g}.hex').write_text('\n'.join(lines)+'\n')
        records=[]
        for p in packets:
            at=0
            while at<len(p):
                key=int.from_bytes(p[at:at+2],'big');k,i=key>>13,key&8191;w=8 if k==0 and i&4096 else [2,1,7,4,7,1,2,8][k]
                v=int.from_bytes(p[at+4:at+4+w],'big');records.append((k<<93)|(g<<77)|(i<<64)|v);at+=4+w
        (a.out/f'expect-{g}.hex').write_text(''.join('%024x\n'%v for v in records))
        cases.append([g,*counts,geom[5740],len(records),mode])
    (a.out/'cases.txt').write_text(''.join(' '.join(map(str,c))+'\n'for c in cases));(a.out/'run.do').write_text('onerror {quit -code 1}\nonbreak {quit -code 1}\nrun -all\nquit -code 0\n')
    (a.out/'inputs.json').write_text(json.dumps(dict(cases=cases,exporter_SHA256=sha(a.exporter),testbench_SHA256=sha(a.out/'tb.sv')),indent=2)+'\n')
def run(a):
    for name,args in [('lib',['vlib','work']),('compile',['vlog','-sv','nes_native_export203.sv','tb.sv']),('sim',['vsim','-c','-quiet','-do','run.do','tb'])]:
        with(a.out/(name+'.log')).open('wb')as f:r=subprocess.run([str(a.questa_bin/(args[0]+'.exe')),*args[1:]],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        assert r.returncode==0,(name,(a.out/(name+'.log')).read_text(errors='replace'))
    assert 'PASS506 total=16'in(a.out/'sim.log').read_text();(a.out/'result.json').write_text(json.dumps(dict(passed=True,cases=16,scope=__doc__,inputs_SHA256=sha(a.out/'inputs.json'),records_SHA256=sha(a.out/'records.csv')))+'\n');print('PASS506 source:14 exact records/2 failure cases')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run'])
    for n in ['data','exporter','out','questa-bin']:p.add_argument('--'+n,type=Path)
    a=p.parse_args();(prepare if a.mode=='prepare'else run)(a)
