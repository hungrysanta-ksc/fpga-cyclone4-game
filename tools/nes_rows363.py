# SPDX-License-Identifier: MIT
"""NES-local canonical rows, fixed dual-clock RAM ports and shared byte executor.

Apply to source338 + host359 + BG5/OBJ2. The previous query bridge is used
only to obtain its transport/start/final-lease wiring, then removed entirely.
"""
from nes_delta231 import ROOT,once
from nes_query356 import apply as migrate
from nes_cancel358 import apply as cancellation


def local_rows(original):
    a=original.index(' reg [10:0] q_maps;');b=original.index('\n\n\n assign output_phase',a)
    q=original[a:b]
    q=q.replace('state==FSTORE','state==STORE').replace('state==FETCH','state==FETCH')
    q=q.replace('live&&!output_phase&&state!=IDLE','live&&state!=IDLE&&state!=DRAIN')
    q=q.replace('assign query=raw_query||(q_want&&q_active);','assign query=q_want&&q_active;')
    q=q.replace('reg q_have,q_pending;', 'reg q_have;')
    q=q.replace("assign query_kind=raw_query?3'd7:q_section;assign query_index=raw_query?raw_index:{2'd0,q_index};", "assign query_kind=q_section;assign query_index={2'd0,q_index};")
    a=original.index('    if(q_want)');b=original.index('\n\n    case(state)',a)
    qr=original[a:b]
    qr=qr.replace('fault<=3','fault<=1')
    return '''// SPDX-License-Identifier: MIT
// Two leased rows. A descriptor is returned only after its final byte was
// consumed by the host codec. STOP drains both mailboxes and collector reply.
module nes_rows363(
 input wire clk,host_clk,reset,stop,start,collector_cancel358,display_phase,
 input wire [15:0] frame_generation,input wire [2:0] patch_count,
 input wire [7:0] object_count,exception_count,input wire [5:0] group_count,palette_count,
 output wire query,output wire [2:0] query_kind,output wire [12:0] query_index,
 output wire [15:0] query_generation,input wire raw_response,raw_hit,input wire [63:0] raw_data,
 output wire [9:0] ram_addr,output wire ram_we,output wire [7:0] ram_w,
 output wire row_valid,input wire row_take,output wire [30:0] row_data,
 output wire all_returned,output wire drained,output reg fault,
 input wire plan_zero,plan_step,output wire [9:0] plan_cursor
);
 localparam IDLE=0,FETCH=1,STORE=2,PUBLISH=3,SPACE=4,DRAIN=5;
 reg [2:0] state;reg active,slot,read_slot,finished;reg [12:0] cursor,raw_limit;
 reg [6:0] row_i,row_size,block_id;reg [7:0] value;
 reg [15:0] generation;reg [2:0] admitted_raw;reg q_pending;
 wire raw_mode=cursor>=4398;wire live=active&&!stop&&!fault;
 wire output_phase=display_phase;
 wire in_valid;wire [7:0] in_data;wire [12:0] in_offset;
 wire ready0,ready1,valid0,valid1;wire [30:0] data0,data1;
 wire publish=state==PUBLISH&&live;
 wire [30:0] descriptor={generation,block_id,row_size,slot};
 nes_native_mailbox206 #(.WIDTH(31)) row0(clk,host_clk,reset,publish&&!slot,ready0,descriptor,
  valid0,stop||(!read_slot&&row_take),data0);
 nes_native_mailbox206 #(.WIDTH(31)) row1(clk,host_clk,reset,publish&&slot,ready1,descriptor,
  valid1,stop||(read_slot&&row_take),data1);
 assign row_valid=(read_slot?valid1:valid0)&&!stop&&!fault;
 assign row_data=read_slot?data1:data0;
 always @(posedge host_clk or posedge reset)if(reset)read_slot<=0;
 else if(row_take&&row_valid)read_slot<=!read_slot;
 // Completion is a level, sampled after both returned descriptor credits.
 reg [1:0] returned_h,drained_h;
 wire returned_n=finished&&ready0&&ready1&&!q_pending;
 wire drained_n=stop&&collector_cancel358&&ready0&&ready1&&!q_pending;
 always @(posedge host_clk or posedge reset)if(reset)begin returned_h<=0;drained_h<=0;end
 else begin returned_h<={returned_h[0],returned_n};drained_h<={drained_h[0],drained_n};end
 assign all_returned=returned_h[1];assign drained=drained_h[1];
 assign ram_addr=(slot?10'd800:10'd640)+row_i;
 assign ram_we=live&&state==STORE;assign ram_w=value;
 assign plan_cursor=cursor[9:0];
''' + q + '''
 always @(posedge clk)begin
  if(reset)begin
   state<=IDLE;active<=0;slot<=0;finished<=0;cursor<=0;raw_limit<=0;
   row_i<=0;row_size<=66;block_id<=0;value<=0;generation<=0;admitted_raw<=0;fault<=0;
   q_maps<=0;q_objects<=0;q_exceptions<=0;q_palettes<=0;q_mode<=0;q_normal<=0;
   q_raw_seen<=0;q_held<=0;q_have<=0;q_pending<=0;
  end else if(stop)begin
   active<=0;state<=DRAIN;q_have<=0;cursor<=0;
   if(raw_response||collector_cancel358)q_pending<=0;
  end else if(!fault)begin
''' + qr + '''
   if(display_phase)begin
    if(plan_zero)cursor<=0;else if(plan_step)cursor<=cursor+13'd1;
   end
   case(state)
    IDLE:if(start)begin
     active<=1;finished<=0;cursor<=0;row_i<=0;row_size<=66;block_id<=0;
     generation<=frame_generation;admitted_raw<=patch_count;raw_limit<={2'd0,patch_count,8'd0};
     q_maps<={group_count,5'd0}+group_count;q_objects<=object_count;q_exceptions<=exception_count;
     q_palettes<=palette_count==1?32:64;q_mode<=0;q_normal<=0;q_raw_seen<=0;q_have<=0;q_pending<=0;
     state<=SPACE;
    end
    SPACE:if(slot?ready1:ready0)state<=FETCH;
    FETCH:if(in_valid)begin
     if(cursor>=4398+raw_limit||(cursor==4320&&(!q_normal||q_raw_seen!=admitted_raw)))fault<=1;
     else begin value<=q_value;state<=STORE;end
     if(!q_synthetic)begin q_held<={8'd0,q_held[63:8]};if(q_last)q_have<=0;end
    end
    STORE:begin cursor<=cursor+13'd1;
     if(row_i+1==row_size)state<=PUBLISH;else begin row_i<=row_i+1'b1;state<=FETCH;end
    end
    PUBLISH:if(slot?ready1:ready0)begin
     slot<=!slot;row_i<=0;block_id<=block_id+1'b1;
     row_size<=cursor<2112?66:cursor==4352?46:64;
     if(cursor==4398+raw_limit)begin finished<=1;active<=0;state<=DRAIN;end
     else state<=SPACE;
    end
    DRAIN:if(display_phase&&returned_n)begin
     // The final input byte is no longer a source cursor after lease handoff.
     if(!plan_step&&!plan_zero&&cursor>=4398)cursor<=0;
     if(!start)state<=IDLE;
    end
    default:begin end
   endcase
  end
 end
endmodule
'''


def apply(d,board=False):
    original=(d/'nes_core257.sv').read_text()
    migrate(d);cancellation(d,board=board)
    p=d/'nes_core257.sv';s=p.read_text()
    s=once(s,'module nes_core257(','''module nes_core257(
 input wire row_valid363,rows_done363,input wire [30:0] row_data363,output wire row_take363,
 output wire read_req363,read_take363,output wire [7:0] read_q363,
 input wire read_valid363,input wire [7:0] read_data363,
''')
    # The canonical query frontend is moved, not copied into both domains.
    a=s.index(' reg [10:0] q_maps;');b=s.index('\n\n\n assign output_phase',a)
    s=s[:a]+''' wire q_pending=0,q_have=0;
 assign query=0;assign query_kind=0;assign query_index=0;assign query_generation=generation;
 assign in_valid=live&&state==FETCH&&read_valid363;
 assign in_offset=cursor;assign in_data=read_data363;
 wire [9:0] row_address363=(row_data363[0]?10'd800:10'd640)+row_i;
 assign row_take363=in_valid&&row_i+1==row_size;
 assign read_take363=live&&read_valid363&&(state==FETCH||(state==SBYTE&&byte_ready));
 assign read_q363=ram_a_q;
''' +s[b:]
    s=s.replace('mask_acc,new_byte,old1','mask_acc,old1')
    s=once(s,' reg [2:0] admitted_raw;', ' wire [7:0] new_byte=read_data363;\n reg [2:0] admitted_raw;')
    s=once(s,' assign ram_a_addr=', ' assign read_req363=live&&!mask_pending278&&((state==FETCH&&row_valid363)||state==SBYTE);\n assign ram_a_addr=')
    s=s.replace('IDLE,HEADER,FETCH,FSTORE,BLOCKEND,REQUEST,SREAD,SBYTE,','IDLE,HEADER,FETCH,BLOCKEND,REQUEST,SBYTE,')
    s=s.replace('state==FSTORE','(state==FETCH&&in_valid)')
    s=once(s,"assign ram_a_addr={1'b1,mask_pending278?mask_address278:a_addr};", "assign ram_a_addr=state==FETCH&&!in_valid&&!mask_pending278?row_address363:{1'b1,mask_pending278?mask_address278:a_addr};")
    s=once(s,'assign byte_valid=live&&state==SBYTE;', 'assign byte_valid=live&&state==SBYTE&&read_valid363;')
    s=once(s,'state==WAITACK&&transport_empty;', 'state==WAITACK&&transport_empty&&rows_done363;')
    s=once(s,'\n   FSTORE:begin', '\n   FETCH:if(in_valid)begin')
    s=once(s,'  out_byte=a_q;', '  out_byte=read_data363;')
    import re
    s=re.sub(r'q_maps<=0;q_objects<=0;q_exceptions<=0;q_palettes<=0;q_mode<=0;q_normal<=0;q_raw_seen<=0;q_held<=0;q_have<=0;q_pending<=0;','',s)
    s=s.replace('new_byte<=0;','')
    a=s.index('    if(q_want)');b=s.index('    case(state)',a);s=s[:a]+s[b:]
    a=s.index('      q_maps<=');b=s.index('admitted_raw<=patch_count;',a);s=s[:a]+'      '+s[b:]
    a=s.index('    FETCH:if(in_valid)begin');b=s.index('     cursor<=cursor+1\'b1;',a)
    s=s[:a]+'''    FETCH:if(in_valid)begin
     if(!row_valid363||row_data363!={generation,block_id,row_size,row_data363[0]})begin fault<=3;base_valid<=0;end
''' +s[b:]
    s=s.replace('state<=SREAD','state<=SBYTE').replace('    SREAD:state<=SBYTE;\n','')
    s=s.replace('SBYTE:if(byte_ready)', 'SBYTE:if(byte_ready&&read_valid363)')
    s=s.replace('mask_acc<=0;q_have<=0;q_pending<=0;', 'mask_acc<=0;')
    p.write_text(s,newline='\n')
    p=d/'nes_joint257.sv';s=p.read_text()
    s=once(s,'module nes_joint257(','''module nes_joint257(
 output wire read_req363,read_take363,output wire [7:0] read_q363,
 input wire read_valid363,input wire [7:0] read_data363,
''')
    s=once(s,'always @(posedge host_clk)begin aq<=','always @(posedge clk)begin aq<=')
    s=once(s,'wire raw_response,raw_hit;wire [63:0] raw_data;', 'wire raw_response=0,raw_hit=0;wire [63:0] raw_data=0;')
    a=s.index(' nes_query355 query356(');b=s.index('\nwire record_last319;',a)
    s=s[:a]+'''
 wire row_valid363,row_take363,rows_done363;wire [30:0] row_data363;
 wire [9:0] source_addr363,check_addr363;wire source_we363,check_we363;wire [7:0] source_w363,check_w363;
 // Initial checker clear precedes admission; afterwards port B is phase-owned.
 assign ram_b_addr=!init278||output_phase?check_addr363:source_addr363;
 assign ram_b_we=!init278||output_phase?check_we363:source_we363;
 assign ram_b_w=!init278||output_phase?check_w363:source_w363;
 assign query_active356=!cancel&&!owner_fault356;
 nes_rows363 rows363(.clk(clk),.host_clk(host_clk),.reset(reset),.stop(cancel),
  .start(start&&start_ready),.collector_cancel358(collector_cancel358),.display_phase(phase_n356[1]),
  .frame_generation(frame_generation),.patch_count(patch_count),.object_count(object_count),.exception_count(exception_count),
  .group_count(group_count),.palette_count(palette_count),.query(query),.query_kind(query_kind),.query_index(query_index),
  .query_generation(query_generation),.raw_response(response),.raw_hit(hit),.raw_data(data),
  .ram_addr(ram_a_addr),.ram_we(ram_a_we),.ram_w(ram_a_w),.row_valid(row_valid363),.row_take(row_take363),
  .row_data(row_data363),.all_returned(rows_done363),.drained(query_drained356),.fault(owner_fault356),
  .plan_zero(plan_zero319),.plan_step(plan_step319),.plan_cursor(plan_cursor319));
''' +s[b:]
    s=once(s,'encoder(','''encoder(.row_valid363(row_valid363),.row_take363(row_take363),.row_data363(row_data363),.rows_done363(rows_done363),
 .read_req363(read_req363),.read_take363(read_take363),.read_q363(read_q363),.read_valid363(read_valid363),.read_data363(read_data363),''')
    s=once(s,'.query_ready356(query_ready356)',".query_ready356(1'b0)")
    s=once(s,'.ram_a_q(ram_a_q)', '.ram_a_q(ram_b_q)')
    for x,y in [('.ram_a_addr(ram_a_addr)','.ram_a_addr(source_addr363)'),('.ram_a_we(ram_a_we)','.ram_a_we(source_we363)'),('.ram_a_w(ram_a_w)','.ram_a_w(source_w363)'),('.ram_addr(ram_b_addr)','.ram_addr(check_addr363)'),('.ram_we(ram_b_we)','.ram_we(check_we363)'),('.ram_w(ram_b_w)','.ram_w(check_w363)')]:s=once(s,x,y)
    a=s.index('// SPDX-License-Identifier: MIT',s.index('endmodule'));s=s[:a]+local_rows(original)
    p.write_text(s,newline='\n')
    shared(d)


def shared(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'(output wire [33:0] read359', '''(output wire read_req363,read_take363,output wire [7:0] read_q363,
 input wire read_valid363,input wire [7:0] read_data363,
 output wire load363,output wire [7:0] load_data363,output wire [33:0] read359''')
    # A single shared HOLD state replaces source FSTORE/SREAD and host PCAP/PUT.
    # Host metadata/display loads use the same byte register, never a second held.
    s=once(s,'PREAD=5,PCAP=6,PUT=7,','PREAD=5,')
    s=s.replace('OCAP=PCAP','OCAP=PREAD')
    s=s.replace('reg [7:0] at,held;', 'reg [7:0] at;wire [7:0] held=read_data363;')
    assert 'reg [7:0] at,held' not in s
    s=s.replace('held<=0;','').replace('held<=reply;','').replace('held<=qdata;','')
    s=once(s,'     PREAD:state<=PCAP;\n     PCAP:begin','     PREAD:if(read_valid363)begin')
    s=once(s,'      end else begin state<=PUT;end','''      end else if(prelude_mode?mready:put_ready)begin
       if(prelude_mode&&at==14)scroll_length[7:0]<=held;
       if(prelude_mode&&at==15)scroll_length[10:8]<=held[2:0];
       if(at+1==length)state<=prelude_mode?PREWAIT:SEAL;
       else begin at<=at+1'b1;parser_address<=parser_address+1'b1;end
      end''')
    a=s.index('     PUT:if(');b=s.index('     EXPAND325:',a);s=s[:a]+s[b:]
    # Captured queue data must remain stable through backpressure.
    a=s.index('     PREAD:if(read_valid363)');b=s.index('     TILEWAIT313:',a)
    s=s[:a]+s[a:b].replace('qdata','held')+s[b:]
    s=s.replace('state==PUT','(state==PREAD&&read_valid363&&normal363)')
    # Existing metadata and display paths explicitly load the shared register.
    s=once(s,' localparam IDLE=', ' wire normal363;\n localparam IDLE=')
    at=s.index('endmodule')
    s=s[:at]+''' assign normal363=header[0]!=1&&header[0]!=7&&(!repeat325||prelude_mode);
 assign read_req363=state==PREAD&&!rst&&!fault;
 assign read_take363=read_valid363&&read_req363&&(!normal363||(prelude_mode?mready:put_ready));
 assign read_q363=qdata;
 assign load363=(state==DWAIT&&bv)||state==MCAP313||(state==MNEXT313&&run_zero313&&run_left313!=0);
 assign load_data363=state==DWAIT?reply:state==MNEXT313?8'd0:qdata;
''' +s[at:]
    p.write_text(s,newline='\n')
    p=d/'nes_joint266.sv';s=p.read_text();at=s.index('wire [8:0] manifest_at282;')
    s=s[:at]+'''wire source_req363,source_take363,host_req363,host_take363,load363;
wire [7:0] source_q363,host_q363,read_data363,load_data363;wire read_valid363;
nes_byte363 executor363(host_clk,reset,abort_source||fault!=0,output_phase,
 source_req363,source_take363,source_q363,host_req363,host_take363,host_q363,
 load363,load_data363,read_valid363,read_data363);
''' +s[at:]
    s=once(s,'core(','''core(.read_req363(source_req363),.read_take363(source_take363),.read_q363(source_q363),
 .read_valid363(read_valid363&&!output_phase),.read_data363(read_data363),''')
    s=once(s,'flow(','''flow(.read_req363(host_req363),.read_take363(host_take363),.read_q363(host_q363),
 .read_valid363(read_valid363&&output_phase),.read_data363(read_data363),.load363(load363),.load_data363(load_data363),''')
    s+='''
// One physical RAM capture/HOLD register and execution state for both phases.
module nes_byte363(input wire clk,reset,stop,output_phase,
 input wire source_req,source_take,input wire [7:0] source_q,
 input wire host_req,host_take,input wire [7:0] host_q,
 input wire load,input wire [7:0] load_data,output wire valid,output reg [7:0] value);
 localparam IDLE=0,CAPTURE=1,HOLD=2;reg [1:0] state;
 wire request=output_phase?host_req:source_req,take=output_phase?host_take:source_take;
 assign valid=state==HOLD&&!stop;
 always @(posedge clk)begin
  if(reset||stop)begin state<=IDLE;value<=0;end
  else begin
   if(load)value<=load_data;
   case(state)
    IDLE:if(request)state<=CAPTURE;
    CAPTURE:begin value<=output_phase?host_q:source_q;state<=HOLD;end
    HOLD:if(take)state<=IDLE;
    default:state<=IDLE;
   endcase
  end
 end
endmodule
'''
    p.write_text(s,newline='\n')
