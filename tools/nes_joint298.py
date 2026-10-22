# SPDX-License-Identifier: MIT
"""Common host-clock descriptor/manifest/receipt executor; CRC observer stays live."""
from nes_delta231 import once

HOST_PORTS='''output wire exec_start298,output wire [1:0] exec_kind298,
 output wire [3:0] exec_op298,output wire [8:0] exec_length298,
 output wire [7:0] exec_data298,input wire exec_busy298,exec_done298,
 input wire [7:0] exec_addr298,
'''
ENGINE_PORTS='''input wire exec_start298,input wire [1:0] exec_kind298,
 input wire [3:0] exec_op298,input wire [8:0] exec_length298,
 input wire [7:0] exec_data298,output wire exec_busy298,exec_done298,
 output wire [7:0] exec_addr298,
'''
WIRES='''wire exec_start298,exec_busy298,exec_done298;wire [1:0] exec_kind298;
 wire [3:0] exec_op298;wire [8:0] exec_length298;wire [7:0] exec_data298,exec_addr298;
'''
CONNECT=''.join(f'.{n}({n}),' for n in ('exec_start298','exec_kind298','exec_op298','exec_length298','exec_data298','exec_busy298','exec_done298','exec_addr298'))

def observe(s):
    """Rebind passive assertions/counters to the new host-clock completion."""
    s=s.replace('dut.flow.ordinary_mode&&dut.flow.state==dut.flow.PREAD',
                'dut.exec_busy298&&dut.core.validator.state==dut.core.validator.E_READ298')
    s=s.replace('  if(dut.rv&&v_ready)receipt_start=$time;','')
    old='  if(dut.flow.state==dut.flow.WAIT_RECEIPT&&v_ready)begin receipt_ticks++;$fwrite(events261,"receipt,%0d,%0t,%0t\\n",f,$time,$time-receipt_start);end'
    assert old in s
    s=s.replace(old,'')
    return once(s,' task clear_output;', '''
 always @(posedge host_clk)if(!reset&&active263)begin
  if(dut.rv&&v_ready)receipt_start=$time;
  if(dut.flow.state==dut.flow.XWAIT298&&dut.exec_done298&&
     (dut.flow.header[0]==12||dut.flow.header[0]==14))begin
   receipt_ticks++;$fwrite(events261,"receipt,%0d,%0t,%0t\\n",f,$time,$time-receipt_start);
  end
  if(dut.exec_busy298&&dut.flow.header[0]!=12&&!dut.flow.qr)
   $fatal(1,"shared executor lost queue head");
 end
 task clear_output;''')

def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'output wire crc_reset287,',HOST_PORTS+'output wire crc_reset287,')
    s=once(s,'localparam NONE=0,','localparam XBEGIN298=40,XWAIT298=41;\n localparam NONE=0,')
    s=once(s,':parser_address;',':exec_busy298?exec_addr298:parser_address;')
    a=s.index(' reg ordinary_mode;');z=s.index(' wire [15:0] plen=',a)
    s=s[:a]+''' reg [10:0] scroll_length;reg [8:0] ordinary_reads;
 wire [8:0] manifest_at=manifest_at282;
 wire [1:0] manifest_phase=!begun?2'd0:sealed?2'd2:manifest_started282?2'd1:2'd0;
 reg tile_proven;
'''+s[z:]
    a=s.index(' wire manifest_byte282=');z=s.index(' assign mready=',a)
    s=s[:a]+''' // One command handshake; the engine owns encoded bytes and RAM completion.
 assign exec_start298=(state==XBEGIN298||state==SEND||state==OTILE||state==OSELECT)&&range_ready&&!rst&&!fault;
 assign exec_kind298=state==XBEGIN298?(header[0]==3?2'd2:2'd1):2'd0;
 assign exec_op298=header[0][3:0];assign exec_length298=qlen;assign exec_data298=qdata;
 assign display_write=0;
 assign display_request=state==DREQ&&display_request_ready&&!rst;
 assign ordinary_range=receipt_valid282&&range_ready&&!rst;
 assign ordinary_first=receipt_first282;assign ordinary_count=receipt_count282;
 assign ordinary_byte=tap_byte278?tap_value278:qdata;
 assign ordinary_stream=0;assign ordinary_check=0;assign ordinary_finish=0;
 assign ordinary_hash_start=tap_start278&&range_ready&&!rst;
 assign ordinary_hash_kind=tap_raw278?2'd0:2'd1;
 assign ordinary_hash_index=tap_relative278[7:4];assign ordinary_hash_byte=tap_byte278&&!rst;
'''+s[z:]
    s=once(s,'ordinary_mode<=0;opos<=0;oend<=0;scroll_length<=0;ordinary_reads<=0;tile_proven<=0;rle_left<=0;rle_zero<=0;',
           'scroll_length<=0;ordinary_reads<=0;tile_proven<=0;')
    a=s.index('     PREAD:begin');z=s.index('     PUT:if',a)
    s=s[:a]+'''     PREAD:state<=PCAP;
     PCAP:begin held<=qdata;state<=PUT;end
'''+s[z:]
    s=once(s,'SEND:if(mready)state<=WAIT_RECEIPT;\n     WAIT_RECEIPT:if(bv)state<=CONSUME;',
           'SEND:if(mready)state<=XWAIT298;')
    s=once(s,'      ordinary_mode<=1;','')
    s=once(s,'else begin opos<=16;oend<=206;state<=OREAD;parser_address<=16;end','else state<=XBEGIN298;')
    s=once(s,'else begin opos<=16;oend<=qlen;parser_address<=16;rle_left<=0;state<=OREAD;end','else state<=XBEGIN298;')
    s=once(s,'else begin state<=OISSUE;end','else state<=XBEGIN298;')
    a=s.index('     OTILE,OSELECT:');z=s.index('\n     default:;',a)
    s=s[:a]+'''     OTILE,OSELECT:if(range_ready)state<=XWAIT298;
     XBEGIN298:if(range_ready)state<=XWAIT298;
     XWAIT298:if(exec_done298)begin
      if(header[0]==12||header[0]==14)state<=CONSUME;
      else begin
       if(header[0]==3)at<=0;
       qretire<=1;packet_seq<=packet_seq+1'b1;state<=IDLE;
      end
     end
'''+s[z:]
    assert all(x not in s for x in ('ordinary_mode','opos','oend','rle_left','rle_zero'))
    p.write_text(s,newline='\n')

    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'module nes_validator278(', 'module nes_validator278('+ENGINE_PORTS)
    s=once(s,'D_FETCH,D_RETURN} state_t;', 'D_FETCH,D_RETURN,E_READ298,E_CAP298,E_NEXT298,E_ZERO298,E_CERT298,E_SEAL298} state_t;')
    s=once(s,' state_t state;', ''' state_t state;
 reg executing298,complete298;reg [8:0] packet_at298;reg [7:0] rle_left298;reg rle_zero298;
 assign exec_busy298=executing298&&!reset&&!abort_source&&!fault;
 assign exec_done298=complete298&&!reset&&!abort_source&&!fault;
 assign exec_addr298=packet_at298[7:0];
 task complete_execution298;
  begin executing298<=0;complete298<=1;end
 endtask
''')
    s=once(s,'if(next_byte283>=v_end283)state<=V_ACTIVE;',
           'if(next_byte283>=v_end283)begin state<=V_ACTIVE;if(executing298)complete_execution298();end ')
    s=once(s,'begin cursor<=cursor+1\'b1;state<=V_ACTIVE;end',
           "begin cursor<=cursor+1'b1;if(executing298)state<=E_NEXT298;else state<=V_ACTIVE;end")
    s=once(s,'   crc_mask287<=0;state<=V_CLEARALL;',
           '   executing298<=0;complete298<=0;packet_at298<=0;rle_left298<=0;rle_zero298<=0;\n   crc_mask287<=0;state<=V_CLEARALL;')
    s=once(s,'end else if(abort_source)begin if(!fault)',
           'end else if(abort_source)begin executing298<=0;complete298<=0;if(!fault)')
    s=once(s,'  else if(!fault)begin\n', '  else if(!fault)begin\n   complete298<=0;\n')
    # Existing independent range admission and RAM checks remain in this FSM.
    s=once(s,'end else if(v_range_valid)begin', '''end else if(exec_start298&&exec_kind298!=0)begin
      if(executing298)fault<=1;
      else begin
       executing298<=1;packet_at298<=16;rle_left298<=0;rle_zero298<=0;
       if(exec_kind298==1)begin
        if(exec_length298<=16||(exec_op298!=15&&exec_op298!=10&&exec_op298!=11))fault<=3;
        else state<=E_READ298;
       end else if(exec_kind298==2)begin
        if(cursor!=422||rec_i!=24||!scroll_seen||digest_ready)fault<=7;
        else begin checksum<=digest;h_count<=0;
         if(v_raw)state<=H_HASHREAD;else begin digest_ready<=1;state<=E_CERT298;end
        end
       end else fault<=6;
      end
     end else if(exec_start298&&exec_kind298==0&&!v_range_valid)begin
      complete_execution298();
     end else if(v_range_valid)begin
      if(exec_start298)executing298<=1;''')
    s=once(s,'rec_i<=rec_i+1\'b1;state<=V_ACTIVE;end',
           "rec_i<=rec_i+1'b1;if(executing298)state<=E_NEXT298;else state<=V_ACTIVE;end")
    s=once(s,'digest_ready<=1;state<=V_ACTIVE;end',
           'digest_ready<=1;if(executing298)state<=E_CERT298;else state<=V_ACTIVE;end')
    s=once(s,'certificate_ok<=1;state<=V_ACTIVE;end',
           'certificate_ok<=1;if(executing298)state<=E_SEAL298;else state<=V_ACTIVE;end')
    s=once(s,'    default:fault<=6;', '''    E_READ298:state<=E_CAP298;
    E_CAP298:begin
     if(packet_at298>=exec_length298)fault<=3;
     else if(exec_op298==11&&packet_at298==16)begin
      if(exec_data298!=3||exec_length298<18)fault<=3;
      else begin packet_at298<=packet_at298+1'b1;state<=E_READ298;end
     end else if(exec_op298==11&&rle_left298==0)begin
      if(manifest_at282+{2'd0,exec_data298[6:0]}+1>256||
         (!exec_data298[7]&&packet_at298+{2'd0,exec_data298[6:0]}+2>exec_length298))fault<=3;
      else begin
       rle_left298<={1'b0,exec_data298[6:0]}+1'b1;rle_zero298<=exec_data298[7];
       packet_at298<=packet_at298+1'b1;state<=E_NEXT298;
      end
     end else begin
      v_value<=exec_data298;packet_at298<=packet_at298+1'b1;
      if(exec_op298==11)rle_left298<=rle_left298-1'b1;
      if(exec_op298==15&&packet_at298<40)begin
       if(rec_i>=24||cursor!=0)fault<=7;else state<=D_READ;
      end else if(rec_i!=24||cursor>=422)fault<=3;
      else state<=V_CHECKREAD;
     end
    end
    E_NEXT298:begin
     if(rle_zero298&&rle_left298!=0)state<=E_ZERO298;
     else if(packet_at298==exec_length298)begin
      if(rle_left298!=0)fault<=3;else begin complete_execution298();state<=V_ACTIVE;end
     end else state<=E_READ298;
    end
    E_ZERO298:begin
     if(rec_i!=24||cursor>=422)fault<=3;
     else begin v_value<=0;rle_left298<=rle_left298-1'b1;state<=V_CHECKREAD;end
    end
    E_CERT298:begin checksum<=16'hffff;h_count<=0;state<=H_CERTREAD;end
    E_SEAL298:begin
     if(cursor!=422||!v_all_consumed||!certificate_ok)fault<=3;
     else begin h_count<=0;seal_state<=1;state<=V_WAITDISPLAY;complete_execution298();end
    end
    default:fault<=6;''')
    p.write_text(s,newline='\n')

    p=d/'nes_joint257.sv';s=p.read_text()
    s=once(s,'module nes_joint257(', 'module nes_joint257('+ENGINE_PORTS)
    s=once(s,'nes_validator278 validator(', 'nes_validator278 validator('+CONNECT)
    p.write_text(s,newline='\n')
    # Live and whole-board wrappers have the same ownership connections.
    p=d/'nes_joint266.sv';s=p.read_text()
    s=once(s,' wire crc_reset287;',WIRES+' wire crc_reset287;')
    s=once(s,' flow(.crc_reset287', ' flow('+CONNECT+'.crc_reset287')
    s=once(s,'nes_joint257 core(', 'nes_joint257 core('+CONNECT)
    p.write_text(s,newline='\n')
