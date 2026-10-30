# SPDX-License-Identifier: MIT
"""Actual501/502 collector query and selected493 source exporter, one fixed PPU scene."""
import argparse,json,shutil
from pathlib import Path
import test_nes_capture502 as t
base=t.base

def prepare(a):
 a.guards=False;a.guard_list=None;a.edges=False;a.phase_sweep=True
 t.prepare(a)
 m=json.loads((a.out/'inputs.json').read_text())
 if a.prior:
  for n in ['nes_native_planes165.sv','nes_native_frame201.sv']:
   shutil.copy2(t.ROOT/'src/fpga/nes_capture501'/n,a.out/n);m['sources'][n]=base.sha(a.out/n)
 n='nes_native_export203.sv';shutil.copy2(a.board/n,a.out/n);m['sources'][n]=base.sha(a.out/n)
 p=a.out/'capture500_tb.sv';s=p.read_text()
 s=s.replace(' wire owned,geometry_valid;',""" reg [2:0] qkind=4;reg [12:0] qindex=0;
 reg export_enable=0;wire export_query,export_tx;wire [2:0] export_kind;wire [12:0] export_index;
 wire [15:0] export_generation;wire [95:0] export_data;wire [3:0] export_state,export_error;
 integer export_fd;reg export_done=0;
 nes_native_export203 producer(.clk(clk),.reset(reset),.enable(export_enable),
 .frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),
 .patch_count(patches),.row_count(rows),.object_count(objects),.exception_count(exceptions),.group_count(groups),.palette_count(palettes),
 .query(export_query),.query_kind(export_kind),.query_index(export_index),.query_generation(export_generation),
 .response(capture.response),.hit(capture.hit),.data(capture.data),
 .tx_valid(export_tx),.tx_ready(1'b1),.tx_data(export_data),
 .ack_valid(export_state==8),.ack_accept(1'b1),.ack_generation(generation),.observe_state177(export_state),.error(export_error));
 always @(posedge clk)if(export_enable && export_tx)begin
  $fwrite(export_fd,"%024h\\n",export_data);
  if(export_data[95:93]==7 && export_data[76:64]==3)export_done=1;
 end
 task dump_query(input integer kind,index,fd);
  begin qkind=kind;qindex=index;query_request=1;query_gen=generation;
   repeat(4)@(negedge clk);if(!capture.hit)$fatal(1,"query export failed %0d/%0d",kind,index);
   $fwrite(fd,"%0d %0d %016h\\n",kind,index,capture.data);
   query_request=0;repeat(2)@(negedge clk);
  end
 endtask
 wire owned,geometry_valid;""")
 declarations=' wire owned,geometry_valid;wire [24:0] errors,observe_errors;\n wire [7:0] rows,objects,exceptions,patch_errors;wire [5:0] groups,palettes;\n wire [2:0] patches;wire [15:0] generation;\n'
 assert s.count(declarations)==1
 s=s.replace(declarations,'').replace(' reg [2:0] qkind',declarations+' reg [2:0] qkind')
 s=s.replace(".query(query_request),.query_kind(3'd4),.query_index(13'd0),.query_generation(query_gen)",
 '.query(export_enable?export_query:query_request),.query_kind(export_enable?export_kind:qkind),.query_index(export_enable?export_index:qindex),.query_generation(export_enable?export_generation:query_gen)')
 s=s.replace('  $finish;',"""  if(!geometry_valid)$fatal(1,"source export needs valid frame");
  fd=$fopen({stimulus,".queries502.txt"},"w");
  $fwrite(fd,"COUNTS %0d %0d %0d %0d %0d %0d %0d\\n",groups*33,rows,objects,exceptions,224,palettes*32,patches);
  for(integer k=0;k<8;k++)begin
   if(k==0)ret=groups*33;else if(k==1 || k==4)ret=224;else if(k==2)ret=objects;else if(k==3)ret=exceptions;else if(k==5)ret=palettes*32;else if(k==7)ret=patches*256;else ret=0;
   for(integer i=0;i<ret;i++)dump_query(k,i,fd);
  end
  $fclose(fd);query_request=0;
  export_fd=$fopen({stimulus,".records502.txt"},"w");export_enable=1;
  while(!export_done)begin @(negedge clk);if(export_error)$fatal(1,"source error %0d",export_error);end
  $fclose(export_fd);$display("EXPORT502 passed generation=%0d patches=%0d",generation,patches);
  $finish;""")
 p.write_text(s,encoding='utf8',newline='\n');m['testbench_SHA256']=base.sha(p)
 (a.out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run'])
 for n in ['board','reference','out','questa-bin']:p.add_argument('--'+n,type=Path)
 p.add_argument('--prior',action='store_true');p.add_argument('--focus',default='f620-addr1-d3')
 a=p.parse_args()
 if a.mode=='prepare':prepare(a)
 else:
  base.FILES.extend(['planes501_reference.sv','nes_native_export203.sv']);t.eq.candidate.run(a)
