# SPDX-License-Identifier: MIT
"""Cycle-exact reference/cursor decoder differential, with real dual-clock RAM."""
import argparse,json,random,shutil,subprocess
from pathlib import Path
from nes_delta231 import sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--reference',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
    rng=random.Random(314);packets=[];meta=[]
    for case in range(48):
        data=[];count=rng.randint(1,16)
        for i in range(count):
            kind=rng.randrange(2);slot=rng.randint(1,127);tag=rng.randrange(8192)
            if rng.randrange(2):
                p=[128|kind,1,0,slot,0,tag&255,tag>>8]
                if kind:p+=[rng.randint(1,255)]
            else:
                alt=rng.randrange(256) if kind==0 else 0
                p=[kind,alt,1,0,slot,0,tag&255,tag>>8,255 if kind==0 else rng.randint(1,255)]
                p += [rng.randrange(256) for _ in range(6)]+[1]
                for bit in range(8):
                    if alt&(1<<bit):
                        t=rng.randrange(8192);p += [t&255,t>>8]
            data+=p
        bad=0;abort=case>=40
        if 36<=case<40:
            data=[128,1,0,1,0,1,0];count=1;bad=1
            if case==36:data[0]=132
            if case==37:data[1]=2
            if case==38:data[3]=0
            if case==39:data=data[:-1]
        assert len(data)<=512
        meta += [len(packets),len(data),count,bad,int(abort)]
        packets+=data
    (d/'payload.hex').write_text(''.join(f'{x:02x}\n' for x in packets))
    (d/'meta.hex').write_text(''.join(f'{x:08x}\n' for x in meta))
    for n in ('nes_plan_batch206.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv'):shutil.copyfile(a.source/n,d/n)
    s=(a.reference/'nes_plan_batch206.sv').read_text().replace('module nes_plan_batch206 #','module reference314 #')
    (d/'reference.sv').write_text(s,newline='\n')
    tb=r'''
`timescale 1ns/1ps
module test;
 reg h=0,n=0,reset=1,stop=0,write_valid=0,seal=0;
 always #5 h=~h;always #22.727 n=~n;
 reg [7:0] wd;reg [9:0] len;reg [4:0] plans;
 wire [1:0] wr,idle,fault,pv,ev,partial;wire [15:0] eg[0:1];wire [208:0] fields[0:1];
 integer consumed[0:1];integer k,j,base,size,bad,abortcase;
 @INST@
 always @(posedge n)if(!reset&&!stop)begin
  if({wr[0],idle[0],fault[0],pv[0],ev[0],partial[0]}!=={wr[1],idle[1],fault[1],pv[1],ev[1],partial[1]})$fatal(1,"control mismatch case %0d",k);
  if((pv[0]||ev[0])&&{fields[0],eg[0]}!=={fields[1],eg[1]})$fatal(1,"decoded fields mismatch case %0d",k);
  if(pv[0])consumed[0]++;if(pv[1])consumed[1]++;
 end
 reg [7:0] payload[0:@LAST@];reg [31:0] meta[0:239];
 initial begin
  $readmemh("payload.hex",payload);$readmemh("meta.hex",meta);
  for(k=0;k<48;k++)begin
   @(negedge h);reset=1;stop=0;write_valid=0;seal=0;consumed[0]=0;consumed[1]=0;
   repeat(10)@(negedge h);reset=0;repeat(20)@(negedge h);
   base=meta[k*5];size=meta[k*5+1];plans=meta[k*5+2];bad=meta[k*5+3];abortcase=meta[k*5+4];len=size;
   for(j=0;j<size;j++)begin
    if(abortcase&&j==size/2)begin stop=1;break;end
    wait(wr==3);@(negedge h);wd=payload[base+j];write_valid=1;
    @(negedge h);write_valid=0;
   end
   if(!abortcase)begin @(negedge h);seal=1;@(negedge h);seal=0;end
   repeat(3000)@(negedge n);
   if(abortcase)begin if(wr||pv||ev)$fatal(1,"STOP ownership");end
   else if(bad)begin if(fault!=3)$fatal(1,"malformed plan not rejected %0d",k);end
   else if(fault||consumed[0]!=plans||consumed[1]!=plans)$fatal(1,"incomplete plan case %0d count %0d/%0d",k,consumed[0],plans);
  end
  $display("PASS PLAN314 36 mixed valid, 4 malformed, 8 STOP; cycle-exact reference");$finish;
 end
 initial begin #20000000;$fatal(1,"timeout");end
endmodule
'''
    inst=[]
    for i,module in enumerate(('reference314','nes_plan_batch206')):
        inst.append(f'''{module} #(.SHARED_CRC307(1)) d{i}(.host_clk(h),.nes_clk(n),.reset(reset),.active(1'b1),.stop(stop),.source_fault(1'b0),
 .write_valid(write_valid),.write_ready(wr[{i}]),.write_data(wd),.retire(1'b0),.retire_done(),.retire_permitted(1'b0),.retire_commit(),
 .seal(seal),.seal_length(len),.seal_plans(plans),.seal_crc(16'd0),.host_idle(idle[{i}]),.fault(fault[{i}]),.lease_valid(1'b1),.lease_generation(16'd1),
 .plan_valid(pv[{i}]),.plan_ready(1'b1),.tile_done(1'b1),.plan_kind(fields[{i}][208:207]),.plan_generation(fields[{i}][206:191]),
 .plan_slot(fields[{i}][190:181]),.plan_tag(fields[{i}][180:168]),.plan_rows(fields[{i}][167:120]),.plan_mask(fields[{i}][119:112]),
 .plan_alt_mask(fields[{i}][111:104]),.plan_alt_tags(fields[{i}][103:0]),.end_valid(ev[{i}]),.end_partial295(partial[{i}]),.end_ready(1'b1),.end_generation(eg[{i}]));''')
    tb=tb.replace('@INST@','\n'.join(inst)).replace('@LAST@',str(len(packets)-1))
    (d/'test.sv').write_text(tb,newline='\n');q=Path('C:/altera_standard/25.1std/questa_fse/win64')
    names=['nes_plan_batch206.sv','reference.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv','test.sv']
    for tool,args in [('vlib',['work']),('vlog',['-sv',*names]),('vsim',['-c','test','-do','run -all;quit -f'])]:
        with (d/(tool+'.log')).open('wb') as log:r=subprocess.run([q/(tool+'.exe'),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        text=(d/(tool+'.log')).read_text(errors='replace');assert r.returncode==0 and '** Error' not in text and '** Fatal' not in text,text[-3000:]
    assert 'PASS PLAN314' in text
    result=dict(passed=True,valid=36,malformed=4,STOP=8,actual_inputs={n:sha(d/n) for n in names+['payload.hex','meta.hex']})
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
