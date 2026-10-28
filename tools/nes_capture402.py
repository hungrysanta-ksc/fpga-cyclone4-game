# SPDX-License-Identifier: MIT
"""RAM previous/rank with one-event-per-clock lookahead and same-rank bypass."""
from nes_delta231 import BASE,ROOT,once

def materialize():
 s=(BASE/'probes/nes-joint400/map01/nes_native_compact181.sv').read_text()
 # Keep reset/release/fault immediate. Delay the event and row-control lane
 # together, while synchronous RAMs prefetch from the raw lane.
 at=s.index(' // 1056*15')
 head=s[:at]
 for n in('begin_scene','end_scene','event_valid','event_data','row_commit','row_patched','committed_row'):
  import re
  head=re.sub(r'\b'+n+r'\b',n+'_raw402',head)
 pipe='''
 reg begin_scene,end_scene,event_valid,row_commit,row_patched;
 reg[63:0]event_data;reg[7:0]committed_row;
 always @(posedge clk)begin
  if(reset||release_scene)begin begin_scene<=0;end_scene<=0;event_valid<=0;row_commit<=0;row_patched<=0;event_data<=0;committed_row<=0;end
  else begin begin_scene<=begin_scene_raw402;end_scene<=end_scene_raw402;event_valid<=event_valid_raw402;event_data<=event_data_raw402;
   row_commit<=row_commit_raw402;row_patched<=row_patched_raw402;committed_row<=committed_row_raw402;end
 end
'''
 s=head+pipe+s[at:]
 s=once(s,' reg [14:0] previous[0:32];',' (* ramstyle="M9K, no_rw_check" *)reg[14:0]previous[0:32];reg[14:0]previous_q402;')
 s=once(s,' wire [5:0] previous_address=copy_busy?copy_column:column;\n wire [14:0] previous_value=previous[previous_address];',' wire[14:0]previous_value=previous_q402;')
 a=s.index(' reg [37:0] rank_key');b=s.index(' wire obj=',a)
 s=s[:a]+''' (* ramstyle="M9K, no_rw_check" *)reg[61:0]rank402[0:7];reg[61:0]rank_q402;
 wire[37:0]rank_key402=rank_q402[61:24];wire[7:0]rank_mask402=rank_q402[23:16],rank_row402=rank_q402[15:8];wire[6:0]rank_slot402=rank_q402[7:1];
'''+s[b:]
 for n in('rank_key','rank_mask','rank_row','rank_slot'):s=s.replace(n+'[rank]',n+'402')
 s=s.replace(' assign row_needs_patch=row_bad || column!=33;',''' wire bg_shape402=accept&&!invalid_extension&&row<224&&!obj&&row==row_count&&position<=32&&attribute<=3&&rank==0&&!copy_busy;
 wire previous_write402=bg_shape402&&position==column&&!row_bad;
 wire object_write402=accept&&!invalid_extension&&row<224&&obj&&!(rank_valid[rank]&&row<=rank_row402)&&!(!same_object&&object_count==128);
 wire[61:0]rank_data402={key,mask,row,(same_object?rank_slot402:object_count[6:0]),1'b0};
 // Predict the pending event for the pixel-row verdict, which is consumed
 // on the raw row_commit edge before the pipeline's register updates.
 assign row_needs_patch=row_bad||(bg_shape402&&position!=column)||((previous_write402?column+6'd1:column)!=33);
 wire copy_start402=active&&row_commit&&committed_row==row_count&&row_count<224&&!copy_busy&&!event_valid&&!row_patched&&changed&&selected_group<32;
 wire[5:0]previous_read402=row_commit_raw402?6'd0:copy_start402?6'd1:copy_busy?(copy_column==32?6'd0:copy_column+1'b1):event_data_raw402[38:33];
 always @(posedge clk)begin
  previous_q402<=previous[previous_read402];
  rank_q402<=object_write402&&event_data_raw402[52:50]==rank?rank_data402:rank402[event_data_raw402[52:50]];
  if(!reset&&!release_scene)begin
   if(previous_write402)previous[column]<=cell_value;
   if(object_write402)rank402[rank]<=rank_data402;
  end
 end''')
 s=once(s,'      previous[column]<=cell_value;','')
 for n in('rank_key','rank_mask','rank_row'):
  value=dict(rank_key='key',rank_mask='mask',rank_row='row')[n]
  s=s.replace(n+'402<='+value+';','')
 s=s.replace('rank_slot402<=object_count[6:0];','')
 s=once(s,"group_count<=group_count+1'b1;copy_busy<=1;copy_column<=0;", "group_count<=group_count+1'b1;copy_busy<=1;copy_column<=1;\n        maps[group_count*11'd33]<=previous_value;")
 # One physical map write address, including the first prefetched cell.
 # Two procedural write addresses plus a query read otherwise become a
 # three-port array and Quartus expands the whole map into logic registers.
 s=s.replace('maps[copy_base+copy_column]<=previous_value;','').replace("maps[group_count*11'd33]<=previous_value;",'')
 s=once(s,' always @(posedge clk)begin\n  response<=0;hit<=0;'," always @(posedge clk)if(!reset&&!release_scene&&(copy_start402||copy_busy))maps[copy_start402?group_count*11'd33:copy_base+copy_column]<=previous_value;\n always @(posedge clk)begin\n  response<=0;hit<=0;")
 a=s.index(' wire bg_shape402=');b=s.index(' reg [7:0] rank_valid;',a);lane=s[a:b];s=s[:a]+s[b:]
 s=once(s,' reg [14:0] map_q;',lane+' reg [14:0] map_q;')
 # Preserve the public module ABI; only the internal processing lane is
 # delayed. All generated raw-prefetch references become input references.
 import re
 names=('begin_scene','end_scene','event_valid','event_data','row_commit','row_patched','committed_row')
 for n in names:s=re.sub(r'\b'+n+r'\b',n+'_pipe402',s)
 for n in names:s=s.replace(n+'_raw402',n)
 assert all(x not in s for x in('rank_key[','rank_mask[','rank_row[','rank_slot['))
 return s

def apply(d):
 (d/'nes_native_compact181.sv').write_text(materialize(),newline='\n')

if __name__=='__main__':
 (ROOT/'src/fpga/nes_joint402/nes_native_compact181.sv').write_text(materialize(),newline='\n')
