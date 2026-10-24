# SPDX-License-Identifier: MIT
"""Move packet interpretation out of the independent receipt checker.

Applied to the measured 312 source. This is a development transformation,
not a claim that the ordinary consumer or canonical manifest is complete.
"""
from nes_delta231 import once


def apply(d):
    p=d/'nes_validator278.sv';s=p.read_text()
    a=s.index(' reg executing298');b=s.index(' reg [15:0] crc_mask287;',a)
    s=s[:a]+''' assign exec_busy298=1'b0;
 assign exec_done298=1'b0;
 assign exec_addr298=8'd0;
'''+s[b:]
    s=s.replace(',E_READ298,E_CAP298,E_NEXT298,E_ZERO298,E_CERT298,E_SEAL298','')
    a=s.index(' wire requirements307=');b=s.index(' reg [11:0] v_bit_at',a)
    s=s[:a]+s[b:]
    s=s.replace('if(executing298)complete_execution298();','')
    s=s.replace('if(executing298)state<=E_NEXT298;else state<=V_ACTIVE;','state<=V_ACTIVE;')
    s=s.replace('   executing298<=0;complete298<=0;packet_at298<=0;rle_left298<=0;rle_zero298<=0;\n','')
    s=s.replace('executing298<=0;complete298<=0;','')
    s=s.replace('   complete298<=0;\n','')
    a=s.index('     end else if(exec_start298&&exec_kind298!=0)');b=s.index('     end else if(v_range_valid)',a)
    s=s[:a]+s[b:]
    s=s.replace('      if(exec_start298)executing298<=1;\n','')
    s=s.replace('if(executing298)state<=E_CERT298;else state<=V_ACTIVE;','state<=V_ACTIVE;')
    s=s.replace('if(executing298)state<=E_SEAL298;else state<=V_ACTIVE;','state<=V_ACTIVE;')
    a=s.index('    E_READ298:');b=s.index('    default:fault<=6;',a)
    s=s[:a]+s[b:]
    assert not any(x in s for x in ('executing298','packet_at298','rle_left298','complete_execution298','E_READ298'))
    p.write_text(s,newline='\n')

    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'reg [7:0] at,held,parser_address;', 'reg [7:0] at,held;reg [8:0] parser_address;')
    s=once(s,'localparam XBEGIN298=40,XWAIT298=41;', '''localparam XBEGIN298=40,XWAIT298=41;
 localparam MREAD313=42,MCAP313=43,MNEXT313=44,MISSUE313=45,
  MWAIT313=46,MDONE313=47,MHASH313=48,MHASHWAIT313=49,
  MCERT313=50,MCERTWAIT313=51,MFINISH313=52,MSEALWAIT313=53;
 reg [7:0] run_left313;reg run_zero313;
 reg [8:0] manifest_byte313;
 reg display_byte313;
''')
    s=once(s,'wire [7:0] qaddr=', '''wire requirements313=header[0]==15&&header[1]==1;
 wire rle313=header[0]==11||(requirements313&&parser_address>40);
 wire [9:0] run_end313={1'b0,manifest_byte313}+{3'd0,qdata[6:0]}+10'd1;
 wire metadata313=state>=MREAD313&&state<=MSEALWAIT313;
 wire receipt_done313=state==XWAIT298&&range_ready;
 wire [7:0] qaddr=''')
    s=s.replace('state==XWAIT298&&exec_done298','state==XWAIT298&&range_ready')
    # No checker-owned packet address or completion handshake remains.
    s=s.replace('exec_busy298?exec_addr298:', '')
    a=s.index(' assign exec_start298=');b=s.index(' assign display_request=',a)
    s=s[:a]+''' assign exec_start298=0;assign exec_kind298=0;
 assign exec_op298=0;assign exec_length298=0;assign exec_data298=0;
 assign display_write=state==MISSUE313&&display_byte313&&range_ready&&!rst&&!fault;
'''+s[b:]
    s=once(s,'assign ordinary_byte=tap_byte278?tap_value278:qdata;', 'assign ordinary_byte=metadata313?held:tap_byte278?tap_value278:qdata;')
    s=once(s,'assign ordinary_stream=0;assign ordinary_check=0;assign ordinary_finish=0;', '''assign ordinary_stream=0;
 assign ordinary_check=state==MISSUE313&&!display_byte313&&range_ready&&!rst&&!fault;
 assign ordinary_finish=state==MFINISH313&&range_ready&&!rst&&!fault;''')
    s=once(s,'assign ordinary_hash_start=tap_start278&&range_ready&&!rst;', 'assign ordinary_hash_start=(tap_start278||state==MHASH313||state==MCERT313)&&range_ready&&!rst&&!fault;')
    s=once(s,"assign ordinary_hash_kind=tap_raw278?2'd0:2'd1;", "assign ordinary_hash_kind=state==MHASH313?2'd3:state==MCERT313?2'd2:tap_raw278?2'd0:2'd1;")
    s=once(s,'state<=IDLE;owner<=NONE;failed<=0;', 'state<=IDLE;owner<=NONE;failed<=0;run_left313<=0;run_zero313<=0;manifest_byte313<=0;display_byte313<=0;')
    a=s.index('     XBEGIN298:if(range_ready)');b=s.index('\n     default:;',a)
    s=s[:a]+'''     XBEGIN298:if(range_ready)begin
      run_left313<=0;run_zero313<=0;parser_address<=16;
      manifest_byte313<=header[0]==15?0:manifest_at;
      state<=header[0]==3?MHASH313:MREAD313;
     end
     XWAIT298:if(range_ready)begin
      if(header[0]==12||header[0]==14)state<=CONSUME;
      else begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=IDLE;end
     end
     MREAD313:state<=MCAP313;
     MCAP313:begin
      if({1'b0,parser_address}>=qlen)failed<=1;
      else if((header[0]==11&&parser_address==16)||(requirements313&&parser_address==40))begin
       if(qdata!=(requirements313?1:3)||qlen<(requirements313?42:18))failed<=1;
       else begin parser_address<=parser_address+1'b1;state<=MREAD313;end
      end else if(rle313&&run_left313==0)begin
       if(run_end313>(requirements313?166:256)||
          (!qdata[7]&&{1'b0,parser_address}+{2'd0,qdata[6:0]}+9'd2>qlen))failed<=1;
       else begin run_left313<={1'b0,qdata[6:0]}+1'b1;run_zero313<=qdata[7];
        parser_address<=parser_address+1'b1;state<=MNEXT313;end
      end else begin
       held<=qdata;parser_address<=parser_address+1'b1;
       display_byte313<=header[0]==15&&parser_address<40;
       if(rle313)run_left313<=run_left313-1'b1;
       state<=MISSUE313;
      end
     end
     MISSUE313:if(range_ready)state<=MWAIT313;
     MWAIT313:if(range_ready)begin
      if(!display_byte313)manifest_byte313<=manifest_byte313+1'b1;
      state<=MNEXT313;
     end
     MNEXT313:begin
      if(run_zero313&&run_left313!=0)begin
       held<=0;display_byte313<=0;run_left313<=run_left313-1'b1;state<=MISSUE313;
      end else if({1'b0,parser_address}==qlen)begin
       if(run_left313!=0||(header[0]==15&&manifest_byte313!=166))failed<=1;
       else state<=MDONE313;
      end else state<=MREAD313;
     end
     MDONE313:begin qretire<=1;packet_seq<=packet_seq+1'b1;state<=IDLE;end
     MHASH313:if(range_ready)state<=MHASHWAIT313;
     MHASHWAIT313:if(range_ready)state<=MCERT313;
     MCERT313:if(range_ready)state<=MCERTWAIT313;
     MCERTWAIT313:if(range_ready)state<=MFINISH313;
     MFINISH313:if(range_ready)state<=MSEALWAIT313;
     MSEALWAIT313:if(sealed)begin at<=0;state<=MDONE313;end
'''+s[b:]
    p.write_text(s,newline='\n')


def observe(s):
    s=s.replace('dut.exec_busy298&&dut.core.validator.state==dut.core.validator.E_READ298',
                'dut.flow.state==dut.flow.MREAD313')
    s=s.replace('dut.flow.state==dut.flow.XWAIT298&&dut.exec_done298',
                'dut.flow.receipt_done313')
    s=s.replace('dut.exec_busy298&&dut.flow.header[0]!=12',
                'dut.flow.metadata313&&dut.flow.header[0]!=12')
    return s
