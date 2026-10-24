# SPDX-License-Identifier: MIT
"""NES346 single final-record source and accepted-byte host executor."""
from nes_delta231 import once


def source(d):
 from nes_record344 import apply as record
 from nes_hybrid340 import apply as hybrid
 hybrid(d);record(d)
 p=d/'nes_core257.sv';s=p.read_text()
 s=once(s,"  if(kind==RUN340)a_addr={1'b0,rec_i}-9'd4;",'')
 s=once(s,"a_addr={2'd0,run340};a_we=", "a_addr=9'd260+{2'd0,run340};a_we=")
 assert 'if(kind==RUN340)case(rec_i)' not in s
 a=s.index('    case(build_i)\n     0:a_w={kind==SHIFT,block_id};')
 s=s[:a]+s[a:].replace('    case(build_i)', '''    if(kind==RUN340)case(build_i)
     0:a_w=8'd64+{4'd0,region340};
     1:a_w=offset340[7:0];2:a_w={5'd0,offset340[10:8]};
     default:a_w={repeat340,6'd0}+{1'b0,run340}-8'd1;
    endcase
    else case(build_i)''',1)
 s=once(s,"   emit_record(RUN340,rep==2?8'd6:rep==1?8'd5:{1'b0,n}+8'd4);", "   kind<=RUN340;record_length<=rep==2?8'd6:rep==1?8'd5:{1'b0,n}+8'd4;\n   record_flush<=0;rec_i<=0;build_i<=0;state<=BUILD344;")
 p.write_text(s,newline='\n')


def host(d):
 p=d/'nes_mux260.sv';s=p.read_text()
 s=once(s,' reg [8:0] manifest_byte313;', " reg [11:0] expanded325;\n wire [8:0] manifest_byte313=expanded325[8:0];")
 s=once(s,'reg [31:0] seed325;reg [11:0] expanded325;reg zero325;', 'reg [31:0] seed325;reg zero325;')
 s=once(s,'manifest_byte313<=0;','')
 s=once(s,'manifest_byte313<=(header[0]==15||header[0]==3)?0:manifest_at;', "expanded325<=(header[0]==15||header[0]==3)?12'd0:{3'd0,manifest_at};")
 s=once(s,'prelude_mode<=1;active305.span<=32;at<=0;', 'prelude_mode<=1;active305.span<=32;expanded325<=0;at<=0;')
 # Replace destination execution blocks before renaming their references.
 a=s.index('     PUT:if(');b=s.index('     SEAL:',a)
 s=s[:a]+'''     ISSUE346:if(meta346?range_ready:prelude_mode?mready:put_ready)begin
      if(meta346&&canonical_bad332)failed<=1;
      else begin
       if(prelude_mode&&expanded325==14)scroll_length[7:0]<=held;
       if(prelude_mode&&expanded325==15)scroll_length[10:8]<=held[2:0];
       state<=meta346?WAIT346:NEXT346;
      end
     end
     WAIT346:if(range_ready)state<=NEXT346;
     NEXT346:begin
      if(meta346)begin
       if(!display_byte313)expanded325<=expanded325+1'b1;
       state<=SUPPLY346;
      end else if(expanded325+1==(prelude_mode?length:repeat325?output325:length))
       state<=prelude_mode?PREWAIT:SEAL;
      else begin
       expanded325<=expanded325+1'b1;
       if(repeat325&&!prelude_mode)state<=ISSUE346;
       else begin parser_address<=parser_address+1'b1;state<=PREAD;end
      end
     end
'''+s[b:]
 a=s.index('     MISSUE313:');b=s.index('     MNEXT313:',a)
 s=s[:a]+s[b:]
 # Retained checked supplier has no destination cursor advancement.
 s=s.replace('MNEXT313','SUPPLY346').replace('MISSUE313','ISSUE346').replace('MWAIT313','WAIT346')
 s=once(s,'PCAP=6,PUT=7,','PCAP=6,')
 s=once(s,' localparam EXPAND325=57;', '')
 s=once(s,' wire metadata313=', ' localparam NEXT346=57;\n wire meta346=header[0]==10||header[0]==11||header[0]==15;\n wire metadata313=')
 s=s.replace('state<=EXPAND325','state<=ISSUE346').replace('state<=PUT','state<=ISSUE346')
 s=once(s,'(state==PUT||state==EXPAND325)&&owner==MAP&&!prelude_mode', 'state==ISSUE346&&owner==MAP&&!prelude_mode&&!meta346')
 s=once(s,'state==EXPAND325?seed325', 'repeat325&&!prelude_mode?seed325')
 s=once(s,'prelude_mode&&state==PUT', 'prelude_mode&&state==ISSUE346')
 # Shared execution states must not select expected RAM for ordinary writes.
 s=once(s,'state==SUPPLY346||state==ISSUE346||state==WAIT346', 'state==SUPPLY346||(meta346&&(state==ISSUE346||state==WAIT346||state==NEXT346))')
 s=once(s,'header[0]!=3&&state==ISSUE346', 'meta346&&state==ISSUE346&&range_ready')
 for dead in ('PUT:', 'EXPAND325', 'MISSUE313', 'MWAIT313', 'MNEXT313', 'manifest_byte313<='):
  assert dead not in s,dead
 p.write_text(s,newline='\n')


def native(d):
 from nes_hybrid340 import native as compatible
 compatible(d)
 # N5v3 places OBJ after GEO: retain checked bitmap and deferred OBJ decode,
 # but restore336 batching exactly (no340 slot1 prefix or344 BG split).
 p=d/'nes_planner285.c';s=p.read_text()
 a=s.index(' /* First BG prefix is irrevocable');b=s.index(' return batch_count285+reserve_plans293<15||flush285();',a)
 s=s[:a]+s[b:]
 s=once(s,'unsigned bytes=batch_size285+reserve_bytes293,plans=batch_count285+reserve_plans293;\n if(!flush285())return false;', 'unsigned bytes=batch_size285,plans=batch_count285;\n if(!flush285())return false;')
 p.write_text(s,newline='\n')
