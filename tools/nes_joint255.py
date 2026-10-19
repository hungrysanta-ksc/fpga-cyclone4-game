# SPDX-License-Identifier: MIT
"""One-word query prefetch and consumed-byte receipt boundary candidates.

The sink valid/ready port is a same-clock accepted-byte boundary. It is not
the SPI packet arbiter, a physical SNES bus or final-display acknowledgement.
"""
import re
from nes_delta231 import once
from nes_joint254 import sources as old_sources


def prefetch(s):
    s=s.replace('WAITACK,Q_WAIT,Q_LOAD,V_CLEARALL','WAITACK,V_CLEARALL')
    s=once(s,' reg [2:0] q_section;', '''
 reg [2:0] q_section;
 reg q_have,q_pending;
 wire [12:0] q_cursor=state==FSTORE?cursor+13'd1:cursor;
 wire q_want=live&&!output_phase&&!raw_mode&&state!=IDLE&&q_cursor<4385&&q_cursor!=4320&&!q_have&&!q_pending;
 wire q_synthetic=cursor==4320||cursor>=4385;
 wire q_last=q_section==2?cursor[2:0]==7:q_section==3?cursor[1:0]==3:
             (q_section==0||q_section==4)?cursor[0]:1'b1;
 ''')
    a=s.index(' always @*begin\n  q_section=');b=s.index(' assign query=',a)
    decode=s[a:b].replace('cursor','q_cursor')
    s=s[:a]+decode+s[b:]
    s=s.replace('(live&&state==FETCH&&q_first&&q_active)','(q_want&&q_active)')
    s=s.replace('live&&(state==Q_LOAD||(state==FETCH&&!q_first))','live&&state==FETCH&&(q_have||q_synthetic)')
    s=s.replace('q_held<=0;digest<=0;', 'q_held<=0;q_have<=0;q_pending<=0;digest<=0;')
    s=s.replace('q_raw_seen<=0;admitted_raw<=patch_count;', 'q_raw_seen<=0;q_have<=0;q_pending<=0;admitted_raw<=patch_count;')
    a=s.index('    FETCH:');b=s.index('    FSTORE:',a)
    capture=s[s.index('    Q_WAIT:if(raw_response)begin',a):b]
    capture=capture.replace('    Q_WAIT:if(raw_response)begin','    if(q_pending&&raw_response)begin\n     q_pending<=0;')
    capture=capture.replace('state<=Q_LOAD;', 'q_have<=1;')
    s=s[:a]+'''    FETCH:if(in_valid)begin
     if(cursor>=4398||(cursor==4320&&(!q_normal||q_raw_seen!=admitted_raw)))begin fault<=3;base_valid<=0;end
     else begin new_byte<=q_value;state<=FSTORE;end
     if(!q_synthetic)begin q_held<={8'd0,q_held[63:8]};if(q_last)q_have<=0;end
    end
'''+s[b:]
    s=s.replace("     q_held<={8'd0,q_held[63:8]};\n     cursor", '     cursor')
    s=once(s,'   else if(!fault)case(state)', '''   else if(!fault)begin
    if(q_want)begin if(q_active)q_pending<=1;else begin q_held<=0;q_have<=1;end end
'''+capture+'\n    case(state)')
    s=once(s,'   endcase\n  end\n end\nendmodule', '   endcase\n   end\n  end\n end\nendmodule')
    return s


PORTS='''
 input wire stream_valid,input wire [7:0] stream_data,output wire stream_ready,
 output wire sink_valid,input wire sink_ready,output wire [7:0] sink_data,
 output wire [1:0] sink_kind,output wire [11:0] sink_unit,output wire [4:0] sink_lane,
'''


def receipt(s):
    # Source cursor is dead during output. Clearing and manifest scanning have
    # disjoint lifetimes; both replace their old independent counters.
    s=s.replace('reg [9:0] v_cursor,v_check_index,v_addr;', 'reg [9:0] v_addr;')
    s=s.replace('v_cursor<=0;v_check_index<=0;', '')
    s=s.replace('v_cursor<=396;v_check_index<=0;', 'cursor<=396;')
    s=re.sub(r'\bv_cursor\b|\bv_check_index\b','cursor',s)
    s=s.replace('V_CLEARALL:if(cursor==817)state<=IDLE;', 'V_CLEARALL:if(cursor==817)begin cursor<=0;state<=IDLE;end ')
    s=s.replace('end else state<=V_ACTIVE;end else cursor', 'end else begin cursor<=0;state<=V_ACTIVE;end end else cursor')
    s=s.replace('else if(cursor==331)state<=V_ACTIVE;', 'else if(cursor==331)begin cursor<=0;state<=V_ACTIVE;end ')
    # B port is idle during receipt operations. Read validity with receipt on
    # the same edge, then commit both on RWRITE. Context remains disjoint.
    s=once(s,'assign ram_b_addr=output_phase?context_addr:', 'assign ram_b_addr=output_phase?(receipt_b?receipt_b_addr:context_addr):')
    s=once(s,'assign ram_b_we=output_phase?context_write:b_we;assign ram_b_w=output_phase?context_data:b_w;',
           'assign ram_b_we=output_phase?(receipt_b_write||context_write):b_we;assign ram_b_w=output_phase?(receipt_b?ram_b_q|v_mask:context_data):b_w;')
    s=once(s,' wire [9:0] context_addr;wire context_write;', ''' wire [9:0] context_addr;wire context_write;
 wire receipt_b=(state==V_RREAD||state==V_RWRITE)&&!v_mapmode||state==V_CHECKREAD||state==V_CHECKTEST;
 wire [9:0] receipt_b_addr=(v_bank?10'd166:10'd0)+
       ((state==V_CHECKREAD||state==V_CHECKTEST)?cursor[9:0]:{1'b0,v_bit_at[11:3]});
 wire receipt_b_write=!reset&&!abort_source&&!fault&&lease_ok&&state==V_RWRITE&&!v_mapmode&&(ram_a_q&v_mask)==0;''')
    s=s.replace('V_RWRITE:if(v_q&v_mask)fault<=2;else if(v_mapmode)advance_range();else state<=V_VREAD;',
                'V_RWRITE:if(v_q&v_mask)fault<=2;else advance_range();')
    s=s.replace('else if(v_q!=v_value)fault<=3;else state<=V_CHECKVALIDREAD;', 'else if(v_q!=v_value||ram_b_q!=255)fault<=3;else advance_check();')
    # Remove dead second-port passes, rather than retaining extra FSM bits.
    s=s.replace(',V_VREAD,V_VWRITE', '').replace(',V_CHECKVALIDREAD,V_CHECKVALIDTEST','')
    s=re.sub(r'\|\|state==V_(?:VREAD|VWRITE|CHECKVALIDREAD|CHECKVALIDTEST)','',s)
    s=re.sub(r'^   V_VREAD,V_VWRITE:.*\n|^   V_CHECKVALIDREAD,V_CHECKVALIDTEST:.*\n', '',s,flags=re.M)
    s=re.sub(r'^    V_VREAD:.*\n|^    V_VWRITE:.*\n|^    V_CHECKVALIDREAD:.*\n|^    V_CHECKVALIDTEST:.*\n','',s,flags=re.M)
    return s


def integrated(s):
    s=receipt(prefetch(s))
    s=once(s,' input wire clk,reset,abort_source,',PORTS+'\n input wire clk,reset,abort_source,') if ' input wire clk,reset,abort_source,' in s else once(s,' input wire clk,reset,abort_source,start,',PORTS+'\n input wire clk,reset,abort_source,start,')
    s=once(s,'WAITACK,V_CLEARALL', 'WAITACK,V_STREAM,V_CLEARALL')
    s=once(s,'assign output_phase=', 'assign output_phase=state==V_STREAM||')
    s=once(s,' wire changed=', STREAM_DECL+'\n wire changed=')
    s=once(s,'state<=V_RREAD;end\n     end else if(v_check_valid)', 'expanded<=0;state<=V_STREAM;end\n     end else if(v_check_valid)')
    s=s.replace('||!v_count||', '||!v_count||v_count>(v_map_range?32:16)||(!v_map_range&&v_first<1024&&v_first+v_count>1024)||(!v_map_range&&v_first<1152&&v_first+v_count>1152)||')
    s=once(s,'    V_RREAD:', '''    V_STREAM:if(stream_valid&&stream_ready)begin
     if(expanded+1==stream_length)state<=V_RREAD;else expanded<=expanded+1'b1;
    end
    V_RREAD:''')
    s=once(s,'else if(!fault&&v_display_ack', 'else if(!fault&&state==V_STREAM&&(v_begin_valid||v_range_valid||v_check_valid||v_finish_valid||h_start))fault<=9;\n   else if(!fault&&v_display_ack')
    return s


STREAM_DECL=r'''
 wire [4:0] stream_shift=v_mapmode?5'd1:(v_bit_at>=1024&&v_bit_at<1152)?5'd5:5'd4;
 wire [15:0] stream_length={4'd0,v_left}<<stream_shift;
 assign stream_ready=!reset&&!abort_source&&!fault&&lease_ok&&state==V_STREAM&&sink_ready;
 assign sink_valid=!reset&&!abort_source&&!fault&&lease_ok&&state==V_STREAM&&stream_valid;
 assign sink_data=stream_data;assign sink_kind={1'b0,v_mapmode};
 assign sink_unit=v_bit_at+(expanded>>stream_shift);
 assign sink_lane=expanded[4:0]&((5'd1<<stream_shift)-1'b1);
'''


ADAPTER=r'''
// Reference adapter holds descriptors separately from the unmodified254 core.
module nes_consume255(
 input wire clk,reset,cancel,lease_valid,other_command,input wire range_valid,map_range,input wire [11:0] first,count,
 input wire core_ready,output wire ready,output wire core_range_valid,output wire core_map_range,
 output wire [11:0] core_first,core_count,
 input wire stream_valid,input wire [7:0] stream_data,output wire stream_ready,
 output wire sink_valid,input wire sink_ready,output wire [7:0] sink_data,
 output wire [1:0] sink_kind,output wire [11:0] sink_unit,output wire [4:0] sink_lane,
 output reg fault
);
 localparam IDLE=0,STREAM=1,COMMIT=2,WAIT_CORE=3;
 reg [1:0] state;reg mode;reg [11:0] at,left;reg [9:0] consumed;
 wire live=!reset&&!cancel&&!fault&&(state==IDLE||lease_valid);
 wire [4:0] shift=mode?5'd1:(at>=1024&&at<1152)?5'd5:5'd4;
 wire [15:0] length={4'd0,left}<<shift;
 assign ready=live&&state==IDLE&&core_ready;
 assign core_range_valid=live&&state==COMMIT;assign core_map_range=mode;assign core_first=at;assign core_count=left;
 assign stream_ready=live&&state==STREAM&&sink_ready;assign sink_valid=live&&state==STREAM&&stream_valid;
 assign sink_data=stream_data;assign sink_kind={1'b0,mode};assign sink_unit=at+(consumed>>shift);
 assign sink_lane=consumed[4:0]&((5'd1<<shift)-1'b1);
 always @(posedge clk)begin
  if(reset)begin state<=IDLE;mode<=0;at<=0;left<=0;consumed<=0;fault<=0;end
  else if(cancel)fault<=1;
  else if(!fault)begin
   if((range_valid||other_command)&&state!=IDLE)fault<=1;
   case(state)
    IDLE:if(range_valid&&core_ready)begin
     if(!count||count>(map_range?32:16)||{1'b0,first}+{1'b0,count}>(map_range?2048:1312)||
        (!map_range&&first<1024&&first+count>1024)||(!map_range&&first<1152&&first+count>1152))fault<=1;
     else begin mode<=map_range;at<=first;left<=count;consumed<=0;state<=STREAM;end
    end
    STREAM:if(stream_valid&&stream_ready)begin if(consumed+1==length)state<=COMMIT;else consumed<=consumed+1'b1;end
    COMMIT:if(core_ready)state<=WAIT_CORE;
    WAIT_CORE:if(core_ready)state<=IDLE;
   endcase
  end
 end
endmodule
'''


def sources(variant='joint'):
    src=old_sources('joint');core=src['nes_core254.sv'];top=src['nes_joint254.sv']
    if variant=='joint':
        core=integrated(core)
        top=once(top,'input wire host_clk',PORTS.replace(' input wire','input wire').replace(' output wire','output wire')+'\ninput wire host_clk')
        pp=['stream_valid','stream_data','stream_ready','sink_valid','sink_ready','sink_data','sink_kind','sink_unit','sink_lane']
        top=once(top,'nes_core254 encoder(', 'nes_core254 encoder('+','.join('.'+n+'('+n+')' for n in pp)+',')
    else:
        core=once(core,' input wire clk,reset,abort_source,', ' output wire consume_lease_ok,\n input wire clk,reset,abort_source,')
        core=once(core,' wire live,lease_ok;', ' wire live,lease_ok;assign consume_lease_ok=lease_ok;')
        top=once(top,'nes_core254 encoder(', 'nes_core254 encoder(.consume_lease_ok(consume_lease_ok),')
        top=once(top,'input wire host_clk',PORTS.replace(' input wire','input wire').replace(' output wire','output wire')+'\ninput wire host_clk')
        top=top.replace('wire cancel=abort_source||fault!=0;', 'assign cancel=abort_source||fault!=0;')
        top=once(top,' wire [7:0] ram_a_q', ''' wire cancel,consume_lease_ok;
 wire adapter_fault,crange,cmap,cready,aready;wire [11:0] cfirst,ccount;
 assign v_ready=aready;
 nes_consume255 adapter(.clk(clk),.reset(reset),.cancel(cancel),.lease_valid(consume_lease_ok),.other_command(v_begin_valid||v_check_valid||v_finish_valid||h_start),.range_valid(v_range_valid),.map_range(v_map_range),.first(v_first),.count(v_count),
  .core_ready(cready),.ready(aready),.core_range_valid(crange),.core_map_range(cmap),.core_first(cfirst),.core_count(ccount),
  .stream_valid(stream_valid),.stream_data(stream_data),.stream_ready(stream_ready),.sink_valid(sink_valid),.sink_ready(sink_ready),
  .sink_data(sink_data),.sink_kind(sink_kind),.sink_unit(sink_unit),.sink_lane(sink_lane),.fault(adapter_fault));
 wire [7:0] ram_a_q''')
        for n,x in [('v_range_valid','crange'),('v_map_range','cmap'),('v_first','cfirst'),('v_count','ccount'),('v_ready','cready')]:top=top.replace('.'+n+'('+n+')','.'+n+'('+x+')')
        top=top.replace('cf?cf:sf||hf?', "cf?cf:adapter_fault?4'd9:sf||hf?")
        for n in ('v_begin_valid','v_check_valid','v_finish_valid','h_start'):
            top=top.replace('.'+n+'('+n+')','.'+n+'('+n+'&&aready)')
        src['nes_consume255.sv']=ADAPTER
    src['nes_core254.sv']=core;src['nes_joint254.sv']=top
    return {n.replace('254','255'):s.replace('254','255') for n,s in src.items()}
