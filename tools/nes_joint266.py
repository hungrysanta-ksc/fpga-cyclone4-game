# SPDX-License-Identifier: MIT
"""H2-backed display view and four phase-RAM offset bytes; no display array."""
from nes_joint265 import sources as prior
from nes_delta231 import once


def sources():
 src=prior()
 ports='''input wire display_write,display_request,output wire display_request_ready,
 output wire display_response_valid,input wire display_response_ready,output wire [7:0] display_response,
 '''
 binds='''.display_write(display_write),.display_request(display_request),.display_request_ready(display_request_ready),
 .display_response_valid(display_response_valid),.display_response_ready(display_response_ready),.display_response(display_response),'''
 for name in ['nes_core257.sv','nes_joint257.sv']:
  s=src[name];s=once(s,'input wire v_begin_valid',ports+'input wire v_begin_valid')
  if name=='nes_joint257.sv':s=once(s,'nes_core257 encoder(', 'nes_core257 encoder('+binds)
  src[name]=s
 s=src['nes_core257.sv']
 s=once(s,'H_LENHIREAD,H_LENHI}', 'H_LENHIREAD,H_LENHI,D_READ,D_CHECK,D_FETCH,D_RETURN}')
 s=once(s,'state==H_LENHIREAD||state==H_LENHI;', 'state==H_LENHIREAD||state==H_LENHI||state==D_READ||state==D_CHECK||state==D_FETCH||state==D_RETURN;')
 s=once(s,' assign context_addr=state==V_IDLE?', ''' // Only offsets require new storage; all other display fields are H2 views.
 reg [9:0] display_addr;
 always @*begin
  display_addr=10'd864+{8'd0,h_count[1:0]};
  case(h_count[3:0])
   0:display_addr=835;1:display_addr=851;2:display_addr=852;
   3:display_addr=846;4:display_addr=847;
   5:display_addr=848;6:display_addr=849;7:display_addr=850;
   default:begin end
  endcase
 end
 assign display_request_ready=!reset&&!abort_source&&!fault&&lease_ok&&state==V_WAITDISPLAY&&h_count<12;
 assign display_response_valid=!reset&&!abort_source&&!fault&&lease_ok&&state==D_RETURN;
 assign display_response=v_value;
 reg display_bad;reg [7:0] display_expected;
 always @*begin
  display_bad=0;display_expected=0;
  case(rec_i)
   0:display_bad=v_value[3:0]!=0;
   1:display_bad={v_value,build_i}>16384;
   2:display_bad=v_value[4:0]!=0;
   3:display_bad={v_value,build_i}>4096;
   4:display_expected=0;5:display_expected=16;
   6:display_expected=0;7:display_expected=2;
   8:display_expected=32;9:display_expected=2;
   10:display_expected=v_raw?8'h5a:ram_b_q;
   11:display_expected=v_raw?8'h0d:ram_b_q;
   16:display_expected=8'h60;17:display_expected=8'h10;
   18:display_expected=ram_b_q;19:display_expected=0;
   20:display_expected=8'h72;21:display_expected=8'h24;
   22:display_expected=ram_b_q;23:display_expected=0;
   default:begin end
  endcase
  if((rec_i>=4&&rec_i<12)||rec_i>=16)display_bad=v_value!=display_expected;
 end
 assign context_addr=(state==D_FETCH||state==D_RETURN||state==V_WAITDISPLAY)?display_addr:
     (state==D_READ||state==D_CHECK)?(rec_i==10?10'd846:rec_i==11?10'd847:rec_i==18?10'd851:10'd852):state==V_IDLE?''')
 s=once(s,'   V_CLEARALL:begin v_addr=cursor;', '''   D_CHECK:begin v_addr=10'd864+{8'd0,rec_i[1:0]};v_we=rec_i>=12&&rec_i<16&&!display_bad;v_wdata=v_value;end
   V_CLEARALL:begin v_addr=cursor;''')
 s=once(s,'else begin v_bank<=v_target_bank;', 'else begin rec_i<=0;v_bank<=v_target_bank;')
 s=once(s,'     else if(h_start)begin', '''     else if(display_write)begin
      if(rec_i>=24||cursor!=0)fault<=7;else begin v_value<=v_check_value;state<=D_READ;end
     end else if(h_start)begin''')
 s=once(s,'h_kind==3&&cursor==422&&scroll_seen&&!digest_ready','h_kind==3&&cursor==422&&rec_i==24&&scroll_seen&&!digest_ready')
 s=once(s,'if(cursor!=0||!v_count', 'if(rec_i!=0||cursor!=0||!v_count')
 s=once(s,'if(cursor>=422)fault<=3;', 'if(rec_i!=24||cursor>=422)fault<=3;')
 s=once(s,'else begin seal_state<=1;state<=V_WAITDISPLAY;', 'else begin h_count<=0;seal_state<=1;state<=V_WAITDISPLAY;')
 s=once(s,'    V_WAITDISPLAY:if(v_display_ack)begin v_initialized[v_bank]<=1;seal_state<=0;state<=IDLE;end', '''    D_READ:state<=D_CHECK;
    D_CHECK:if(display_bad)fault<=7;else begin build_i<=v_value;rec_i<=rec_i+1'b1;state<=V_ACTIVE;end
    V_WAITDISPLAY:begin
     if(v_display_ack)begin
      if(h_count!=12)fault<=7;else begin v_initialized[v_bank]<=1;seal_state<=0;state<=IDLE;end
     end else if(display_request&&display_request_ready)state<=D_FETCH;
    end
    D_FETCH:begin v_value<=ram_b_q;state<=D_RETURN;end
    D_RETURN:if(display_response_ready)begin h_count<=h_count+1'b1;state<=V_WAITDISPLAY;end''')
 src['nes_core257.sv']=s
 s=src['nes_mux260.sv']
 flowports='''output wire display_write,display_request,input wire display_request_ready,
 input wire display_response_valid,output wire display_response_ready,input wire [7:0] display_response,
 '''
 s=once(s,' output wire range_valid', ' '+flowports+'output wire range_valid')
 s=once(s,'ORET=36,OTREAD=PREAD;', 'ORET=36,DREQ=37,DWAIT=38,DPRESENT=39,OTREAD=PREAD;')
 s=once(s,' reg [7:0] display_context[0:23];\n','')
 s=s.replace("24'h006088","24'h00607c")
 s=once(s,'wire consumer_ready=consumer_kind==2?', 'wire consumer_ready=consumer_kind==8?display_request_ready:consumer_kind==2?')
 s=once(s,' assign ordinary_range=', ''' assign display_write=consumer_event&&consumer_kind==7&&consumer_ready&&!rst;
 assign display_request=consumer_event&&consumer_kind==8&&consumer_ready&&!rst;
 assign ordinary_range=''')
 s=once(s,'.src_valid(state==OISSUE||state==SEND', '.src_valid(state==DREQ||state==OISSUE||state==SEND')
 s=once(s,'.src_data(state==OISSUE?consumer_word:', ".src_data(state==DREQ?{2'b10,4'd8,18'd0}:state==OISSUE?consumer_word:")
 s=once(s,' wire back_ready,bv;', ' wire back_ready,bv;wire [7:0] reply;assign display_response_ready=back_ready;')
 s=once(s,'#(.WIDTH(1)) receipt', '#(.WIDTH(8)) receipt')
 s=once(s,".src_valid(ns==3),.src_ready(back_ready),.src_data(1'b1),.dst_valid(bv),.dst_ready(state==WAIT_RECEIPT),.dst_data());", ".src_valid(ns==3||display_response_valid),.src_ready(back_ready),.src_data(display_response_valid?display_response:8'd1),.dst_valid(bv),.dst_ready(state==WAIT_RECEIPT||state==DWAIT),.dst_data(reply));")
 s=once(s,"8'h51:control=receipt_committed;", "8'h54:control=state==DPRESENT;8'h51:control=receipt_committed;")
 s=once(s,"if(state!=IDLE||manifest_phase!=2||!sealed_sync[1]||at>=24||ap!=24'h006070+at)failed<=1;\n     else at<=at+1'b1;", "if(state!=DPRESENT||manifest_phase!=2||!sealed_sync[1]||at>=12||ap!=24'h006070+at)failed<=1;\n     else begin at<=at+1'b1;if(at==11)state<=IDLE;else state<=DREQ;end")
 s=once(s,'||at!=24||','||at!=12||')
 s=once(s,"display_context[address-24'h006070]", 'held')
 s=once(s,'state==IDLE&&sealed_sync[1]&&manifest_phase==2', 'state==DPRESENT&&sealed_sync[1]&&manifest_phase==2')
 s=once(s,'if(opos<40)begin display_context[opos-16]<=qdata;state<=PREAD;end', "if(opos<40)event264(7,{10'd0,qdata},3'd3);")
 s=once(s,'     IDLE:if(qr&&have_identity)', '''     DREQ:if(mready)state<=DWAIT;
     DWAIT:if(bv)begin held<=reply;state<=DPRESENT;end
     DPRESENT:begin end
     IDLE:if(manifest_phase==2&&sealed_sync[1]&&at<12)state<=DREQ;
      else if(qr&&have_identity)''')
 src['nes_mux260.sv']=s
 s=src.pop('nes_joint265.sv').replace('nes_joint265','nes_joint266')
 s=once(s,' wire v_begin_valid', ''' wire display_write,display_request,display_request_ready,display_response_valid,display_response_ready;
 wire [7:0] display_response;
 wire v_begin_valid''')
 s=once(s,'flow(.nes_clk', 'flow('+binds+'.nes_clk')
 s=once(s,'core(.v_begin_valid', 'core('+binds+'.v_begin_valid')
 src['nes_joint266.sv']=s
 return src
