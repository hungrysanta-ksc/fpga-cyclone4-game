"""Run 594 ARM against the sealed compact map and the original safe command mailbox."""
import argparse
import shutil
from functools import partial
from pathlib import Path
from budget_nes_region597 import pack, response, value_header
from check_nes_map598 import ROOT, CORE, TAP, checked_board, collector
from check_nes_region595 import exercise, simulate, sources
from map_nes_boundary598 import cached
from map_nes_budget596 import replace, variants


def instrument(d,out):
    f=d/'nes_region595_tb.sv';s=f.read_text()
    s=replace(s,' nes_region595 dut(',''' reg cap_start=0,cap_end=0,bg=0,commit_row=0,patch_row=0;
 reg [7:0] cy;reg [63:0] ev=0;
 wire co,cv,mresp,mhit,dh,rd;wire [63:0] md,ds;wire [4:0] rg;wire [15:0] mc;
 wire [5:0] cg;
 nes_native_compact181 collector(.clk(clk),.reset(reset),.release_scene(released),.begin_scene(cap_start),
  .end_scene(cap_end),.source_fault(1'b0),.event_valid(bg),.event_data(ev),
  .row_commit(commit_row),.row_patched(patch_row),.committed_row(cy),.owned(co),.valid(cv),.group_count(cg),
  .query(query && kind==0),.query_kind(2'd0),.query_address(index[10:0]),.response(mresp),.hit(mhit),.data(md),
  .read_summary(rd),.read_group(rg),.summary_hit(dh),.summary(ds),.map_crc(mc));
 nes_region595 dut(.read_summary(rd),.read_group(rg),.summary_hit(dh),.summary_data(ds),.captured_crc(mc),''')
    s=replace(s,".geometry_valid(1'b1)",".geometry_valid(co && cv)")
    s=replace(s,'if(corrupt!=0&&!injected&&dut.phase==1&&index==5)begin pending<=values[index]^1;injected<=1;end','')
    s=replace(s,'   if(delay>0)', '''   if(mresp)begin
    if(!mhit || md!==values[index])$fatal(1,"collector reply");
    if(corrupt && !injected && dut.phase==1 && index==5)begin pending<=md^1;injected<=1;end
    else pending<=md;
   end
   if(query && kind==0 && dut.phase==0)$fatal(1,"duplicate scan");
   if(delay>0)''')
    s=replace(s,'    owned=1;enable=1;','''    @(negedge clk);cap_start=1;@(negedge clk);cap_start=0;
    for(i=0;i<224;i=i+1)begin
     cy=i;patch_row=values[4*2048+i][49];
     if(!patch_row)for(b=0;b<33;b=b+1)begin
      ev=0;ev[12:0]=values[33*(values[2048+i]>>3)+b][12:0];ev[42:41]=values[33*(values[2048+i]>>3)+b][14:13];
      ev[40:33]=b;ev[32:25]=i;ev[15:13]=values[2048+i][2:0];bg=1;@(negedge clk);
     end
     bg=0;commit_row=1;@(negedge clk);commit_row=0;repeat(33)@(negedge clk);
    end
    cap_end=1;@(negedge clk);cap_end=0;repeat(2)@(negedge clk);
    if(!co||!cv||cg!=groups)$fatal(1,"frame seal");
    owned=1;enable=1;''')
    f.write_bytes(s.encode())
    t=d/'nes_region595_rpc.tcl'
    t.write_bytes(replace(t.read_text(),'set duration 2000','set duration 800000').encode())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('board','arm','archive','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--rescan',action='store_true')
    a=p.parse_args();a.last=906
    checked_board(a.board);a.out.mkdir(parents=True,exist_ok=False)
    def emit(d):
        sources(d)
        f=d/'nes_region595.sv'
        body=pack(value_header(variants(f.read_text())['crc_address']))
        if a.rescan:
            body=body.replace('module nes_region595(','''module nes_region595(input wire summary_hit,input wire [63:0] summary_data,
 input wire [15:0] captured_crc,output wire read_summary,output wire [4:0] read_group,''')
            body=body.replace('endmodule'," assign read_summary=0;assign read_group=0;\nendmodule")
        else:
            body=cached(body)
        f.write_bytes(body.encode())
        f=d/'nes_spi595.sv';f.write_bytes(response(f.read_text()).encode())
        (d/(CORE+'.sv')).write_bytes(collector(a.board,True).encode())
        shutil.copy(ROOT/'rtl'/TAP,d/TAP)
    def bench(d,out):
        instrument(d,out)
        if a.rescan:
            f=d/'nes_region595_tb.sv'
            f.write_bytes(replace(f.read_text(),'if(query && kind==0 && dut.phase==0)$fatal(1,"duplicate scan");','').encode())
    simulate(a,emit,bench,partial(exercise,normal_only=a.rescan))


if __name__=='__main__':
    main()
