# SPDX-License-Identifier: MIT
"""Liveness counterexample for holding a unified queue head through a batch.

Actual206 decoder,260 tile staging and188 aperture; synthetic tile bytes and
queue-head policy. This is not an implemented unified queue or a ROM timing run.
The copy-and-release policy retains the existing plan RAM and decoded context.
"""
from pathlib import Path
import argparse,json,os,shutil
from nes_delta231 import BASE,sha
from probe_nes_joint266 import run

TB=r'''
`timescale 1ns/1ps
module plan268_tb;
 parameter HOLD=1;
 reg clk=0,hclk=0,reset=1;
 always #22.727 clk=~clk;
 always #5.952381 hclk=~hclk;
 reg wv=0,seal=0;reg [7:0] wd;
 wire wr,pv,pr,tdone,ev,ef,tf,pe,ce,idle;
 wire [1:0] pk;wire [15:0] pg,eg;wire [9:0] ps;wire [12:0] pt;
 wire [47:0] rows;wire [103:0] tags;wire [7:0] mask,am;
 nes_plan_batch206 decoder(.host_clk(hclk),.nes_clk(clk),.reset(reset),.active(1'b1),.stop(1'b0),.source_fault(1'b0),
 .write_valid(wv),.write_ready(wr),.write_data(wd),.retire(1'b0),.retire_done(),.retire_permitted(1'b0),.retire_commit(),
 .seal(seal),.seal_length(10'd@LENGTH@),.seal_plans(5'd@COUNT@),.seal_crc(16'h@CRC@),.host_idle(idle),.fault(ef),
 .lease_valid(1'b1),.lease_generation(16'd45),.plan_valid(pv),.plan_ready(pr),.tile_done(tdone),
 .plan_kind(pk),.plan_generation(pg),.plan_slot(ps),.plan_tag(pt),.plan_rows(rows),.plan_mask(mask),.plan_alt_mask(am),.plan_alt_tags(tags),
 .end_valid(ev),.end_ready(1'b0),.end_generation(eg));
 reg sending=0,finished_tile=0;reg [4:0] index=0;integer completed=0,accepted_bytes=0;
 assign pr=!sending;assign tdone=finished_tile;
 wire tr;wire [5:0] length=pk==1?32:16;
 always @(posedge clk)begin
  finished_tile<=0;
  if(!reset)begin
   if(pv&&pr)begin sending<=1;index<=0;end
   if(sending&&tr)begin
    accepted_bytes++;
    if(index==length-1)begin sending<=0;finished_tile<=1;completed++;end
    else index<=index+1'b1;
   end
  end
 end
 wire req,pbegin,pput,pseal,br,putr,cr,er,closed;wire [7:0] pd;
 wire [11:0] clen;wire [31:0] ct;wire [9:0] cs;wire [15:0] cg;wire ck;
 reg [31:0] token=1;reg queue_head=1,end_sent=0;integer consumed_bytes=0,consumed_chunks=0;
 wire consume=cr&&!queue_head;
 wire source_end=completed==@COUNT@&&!sending&&!end_sent;
 always @(posedge clk)if(source_end&&er)end_sent<=1;
 always @(posedge hclk)if(!reset)begin
  if((!HOLD&&seal)||(HOLD&&decoder.word_ready))queue_head<=0;
  if(pbegin&&br)token<=token+1'b1;
  if(consume)begin consumed_bytes+=clen;consumed_chunks++;end
  if(ef||tf||pe||ce)$fatal(1,"unexpected RTL fault");
 end
 nes_tile_producer260 tiles(.nes_clk(clk),.host_clk(hclk),.reset(reset),.active(1'b1),.stop(1'b0),.source_fault(1'b0),
 .tile_valid(sending),.tile_ready(tr),.tile_data({3'd0,index}^ps[7:0]),.tile_index(index),.tile_length(length),.tile_kind(pk),.tile_slot(ps),.tile_generation(pg),
 .end_valid(source_end),.end_ready(er),.end_generation(16'd45),.token_seed(token),
 .request_stage(req),.grant_stage(1'b1),.p_begin(pbegin),.p_put(pput),.p_seal(pseal),.p_data(pd),
 .begin_ready(br),.put_ready(putr),.producer_error(pe),.chunk_ready(cr),.chunk_length(clen),.chunk_token(ct),
 .chunk_kind(ck),.chunk_slot(cs),.chunk_generation(cg),.consume(consume),.consume_token(ct),.fault(tf),.end_sealed(closed),.sealed_generation());
 nes_bulk_aperture188 #(.ALLOW_SHORT_SEAL(1)) aperture(.clk(hclk),.reset(reset),.active(1'b1),.stop(1'b0),
 .begin_valid(pbegin),.begin_length(12'd2048),.begin_token(token),.begin_ready(br),.byte_valid(pput),.byte_data(pd),.byte_ready(putr),
 .seal(pseal),.cancel(1'b0),.producer_error(pe),.chunk_ready(cr),.chunk_length(clen),.chunk_token(ct),
 .consume(consume),.consume_token(ct),.consume_error(ce),.address(24'd0),.read_n(1'b1),.write_n(1'b1),.data_out(),.oe_n(),.dir());
 reg [7:0] packet[0:@LAST@];integer i,before_count;
 initial begin
  $readmemh("batch.hex",packet);repeat(10)@(negedge hclk);reset=0;
  for(i=0;i<@LENGTH@;i++)begin wait(wr);@(negedge hclk);wv=1;wd=packet[i];@(negedge hclk);wv=0;end
  @(negedge hclk);seal=1;@(negedge hclk);seal=0;
  repeat(20000)@(negedge hclk);
  if(HOLD)begin
   if(!queue_head||aperture.sealed!=3||!sending||tr||completed>=@COUNT@-1||consumed_chunks!=0||decoder.state!=5)
    $fatal(1,"missing held-head counterexample completed%0d sealed%0d state%0d",completed,aperture.sealed,decoder.state);
   before_count=accepted_bytes;repeat(1000)@(negedge hclk);
   if(accepted_bytes!=before_count)$fatal(1,"not a stable blocked cycle");
   $display("PASS HELD_HEAD_BLOCKED completed=%0d/%0d bytes=%0d sealed=%0d",completed,@COUNT@,accepted_bytes,aperture.sealed);
  end else begin
   if(queue_head||completed!=@COUNT@||consumed_bytes!=@BYTES@||!end_sent||aperture.sealed!=0)
    $fatal(1,"copy-and-release incomplete completed%0d consumed%0d",completed,consumed_bytes);
   $display("PASS COPY_RELEASE completed=%0d bytes=%0d chunks=%0d",completed,consumed_bytes,consumed_chunks);
  end
  $finish;
 end
endmodule
'''


def decode(raw):
 at=0;out=[]
 while at<len(raw):
  k=raw[at]&3;short=bool(raw[at]&128)
  n=[7,8,3,3][k] if short else 16+2*raw[at+1].bit_count()
  a=at+(3 if short else 4)
  slot=int.from_bytes(raw[a:a+2],'little') if k<2 else 0
  g=at+(1 if short else 2)
  out.append(dict(kind=k,slot=slot,generation=int.from_bytes(raw[g:g+2],'little'),bytes=32 if k==1 else 16));at+=n
 assert at==len(raw)
 return out


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
 d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 shutil.copyfile(Path(__file__),d/Path(__file__).name)
 source=BASE/'probes/nes-joint267/plans01/plans45.bin';raw=source.read_bytes();n=int.from_bytes(raw[:2],'little');count=raw[2];data=raw[3:3+n]
 plans=decode(data);assert len(plans)==count
 crc=65535
 for b in data:
  crc^=b<<8
  for _ in range(8):crc=((crc<<1)^0x1021 if crc&32768 else crc<<1)&65535
 values=dict(LENGTH=n,COUNT=count,CRC=f'{crc:04x}',LAST=n-1,BYTES=sum(x['bytes'] for x in plans));tb=TB
 for k,v in values.items():tb=tb.replace('@'+k+'@',str(v))
 assert '@' not in tb.replace('@(','') # all template fields resolved
 (d/'batch.hex').write_text(data.hex(' ')+'\n');(d/'plan268_tb.sv').write_text(tb,encoding='utf-8',newline='\n')
 prior=BASE/'probes/nes-joint267/joint04';names=['nes_plan_batch206.sv','nes_tile_producer260.sv','nes_bulk_aperture188.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv']
 pins={str(source.relative_to(BASE)):sha(source)}
 for name in names:shutil.copyfile(prior/name,d/name);pins[str((prior/name).relative_to(BASE))]=sha(prior/name)
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*names,'plan268_tb.sv'],d,'vlog')
 logs=[]
 for mode,marker in [(1,'PASS HELD_HEAD_BLOCKED'),(0,'PASS COPY_RELEASE')]:
  log=run(a.questa_bin/'vsim.exe',['-c','work.plan268_tb',f'-gHOLD={mode}','-do','onerror {quit -code 1};run -all;quit -f'],d,f'vsim-{mode}')
  assert marker in log;logs.extend(line for line in log.splitlines() if 'PASS ' in line)
 result=dict(passed=True,scope=__doc__,frame=949,batch=1,plans=plans,logs=logs,input_hashes=pins,script_sha256=sha(Path(__file__)),TB_sha256=sha(d/'plan268_tb.sv'),unified_RTL=False,whole_MAP=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,logs=logs)))


if __name__=='__main__':main()
