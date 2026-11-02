# SPDX-License-Identifier: MIT
"""Add a checked discontinuity marker on the existing tile mailbox of board MMC558."""
import argparse
from pathlib import Path
import json
import shutil
from nes_raw506 import once,sha


def prepare(base,out):
    pins=json.loads((Path(__file__).resolve().parents[1]/'analysis/trial558-verification.json').read_text())['inputs']
    out.mkdir(parents=True,exist_ok=False)
    for name in ('rtl','sys'):
        shutil.copytree(base/name,out/name)
    for src in base.iterdir():
        if src.is_file() and src.suffix.lower() in ('.v','.sv','.vh','.vhd','.qsf','.qpf','.sdc','.mif','.hex','.qip','.tcl','.ver','.inc'):
            shutil.copyfile(src,out/src.name)
    for name in ('nes_direct206.sv','nes_tile_bulk206.sv'):
        assert sha(out/name)==pins[name]
    top=out/'nes_direct206.sv'
    s=once(top.read_text(),'wire tr,td,tv,otready;', '''wire tile_plan_ready,permit;
 wire tr=tile_plan_ready&&permit;
 wire td,tv,otready;''')
    s=once(s,'.plan_valid(pv),.plan_ready(tr),.plan_kind(pk)', '.plan_valid(pv&&permit),.plan_ready(tile_plan_ready),.plan_kind(pk)')
    s=once(s,'.tile_valid(tv),.tile_ready(otready)', '''.plan_valid(pv),.plan_taken(pv&&tr),.plan_kind(pk),.plan_slot(slot),.plan_generation(pg),.plan_permit(permit),
  .tile_valid(tv),.tile_ready(otready)''')
    top.write_text(s,newline='\n')
    bulk=out/'nes_tile_bulk206.sv'
    s=once(bulk.read_text(),' input wire tile_valid,',''' input wire plan_valid,plan_taken,input wire [1:0] plan_kind,input wire [9:0] plan_slot,
 input wire [15:0] plan_generation,output wire plan_permit,
 input wire tile_valid,''')
    s=once(s,' nes_native_mailbox206 #',''' // A held, validated next plan identifies the boundary before any of its
 // ROM reads. Serialize the marker behind the preceding completed tile.
 reg announced;
 wire split=slength!=0 && plan_generation==sgen &&
   (skind!=(plan_kind==1) || {1'b0,plan_slot}!={1'b0,sslot}+11'd1);
 wire announce=plan_valid && split && !announced;
 assign plan_permit=!split || (announced && box_ready);
 always @(posedge nes_clk or posedge sr)
   if(sr)announced<=0;
   else if(!sc)begin
     if(plan_taken)announced<=0;
     else if(announce&&!sending&&box_ready)announced<=1;
   end
 // 00/01 are completed BG/OBJ tiles, 10 is END, 11 closes only the chunk.
 nes_native_mailbox206 #''')
    s=once(s,'.src_valid(sending&&!sc),.src_ready(box_ready),.src_data({ending,skind,sgen,sslot,slength})',
           '.src_valid((sending||announce)&&!sc),.src_ready(box_ready),.src_data({sending?ending:1\'b1,sending?(skind&&!ending):1\'b1,sgen,sslot,slength})')
    s=once(s,'ending<=1;sgen<=end_generation;', 'ending<=1;slength<=0;sgen<=end_generation;')
    s=once(s,'else begin end_sealed<=1;sealed_generation<=frame_gen;in_frame<=0;end',
           'else if(!wkind)begin end_sealed<=1;sealed_generation<=frame_gen;in_frame<=0;end')
    bulk.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
