# SPDX-License-Identifier: MIT
"""Clock-local execution ownership, on top of measured319.

The checker keeps independent evidence/cursors and predicates. Its receipt and
manifest RAM sequence is owned by the host FSM; source owns plan decode phase.
No RAM, mailbox or clock domain is merged.
"""
import re
from nes_delta231 import once

def apply(d):
    # Receipt/check/display validation operations run in the HOST state register.
    phases=['V_RREAD','V_RWRITE','V_PREAD','V_PWRITE','V_CHECKREAD','V_CHECKTEST',
            'V_PCHECKREAD','V_PCHECKTEST','D_READ','D_CHECK']
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'module nes_validator278(', 'module nes_validator278(input wire [3:0] ram_phase321,output reg [3:0] ram_next321,')
    s=once(s,'state_t state;', '''state_t control_state321;
 wire [5:0] state=ram_phase321==1?V_RREAD:ram_phase321==2?V_RWRITE:
  ram_phase321==3?V_PREAD:ram_phase321==4?V_PWRITE:
  ram_phase321==5?V_CHECKREAD:ram_phase321==6?V_CHECKTEST:
  ram_phase321==7?V_PCHECKREAD:ram_phase321==8?V_PCHECKTEST:
  ram_phase321==9?D_READ:ram_phase321==10?D_CHECK:control_state321;
 always @*begin
  ram_next321=ram_phase321;
  case(ram_phase321)
   1:ram_next321=2;
   2:if(crc_covered287&&(v_q&v_mask)==0)ram_next321=v_mapmode?(next_byte283>=v_end283?0:1):3;
   3:ram_next321=4;
   4:ram_next321=next_byte283>=v_end283?0:1;
   5:ram_next321=6;
   6:begin
    if(!map_phase305&&cursor<144)begin if((v_value&~v_q)==0)ram_next321=0;end
    else if(!map_phase305&&cursor<166)ram_next321=(v_raw==0&&cursor>=148)?0:7;
    else if(v_q==v_value&&(v_initialized[v_bank]||v_q==255))ram_next321=0;
   end
   7:ram_next321=8;
   8:if(checked_byte==v_value&&ram_q==255)ram_next321=0;
   9:ram_next321=10;
   10:if(!display_bad)ram_next321=0;
   default:;
  endcase
 end''')
    # The effective state has forward references in combinational feedback;
    # place the feedback process after predicate declarations, before tasks.
    a=s.index(' always @*begin\n  ram_next321=');b=s.index('\n end',a)+len('\n end')
    feedback=s[a:b];s=s[:a]+s[b:]
    s=once(s,' task advance_range;',feedback+'\n task advance_range;')
    s=re.sub(r'\bstate<=','control_state321<=',s)
    # Launch operations keep control_state at ACTIVE; host owns their phase.
    for phase in phases:
        s=s.replace('control_state321<='+phase+';','')
    s=re.sub(r'(V_PREAD|V_CHECKREAD|V_PCHECKREAD|D_READ):(?=\s*\n)', r'\1:begin end',s)
    s=re.sub(r'else[ \t]*\n', 'else begin end\n',s)
    # No separate ACTIVE return update while external execution is running.
    s=s.replace('control_state321<=V_ACTIVE;',"if(ram_phase321==0)control_state321<=V_ACTIVE;")
    assert all('control_state321<='+x not in s for x in phases)
    p.write_text(s,newline='\n')
    # Route the host's phase directly to the host-clock checker.
    p=d/'nes_joint257.sv';s=p.read_text()
    s=once(s,'module nes_joint257(', 'module nes_joint257(input wire [3:0] ram_phase321,output wire [3:0] ram_next321,')
    s=once(s,'nes_validator278 validator(', 'nes_validator278 validator(.ram_phase321(ram_phase321),.ram_next321(ram_next321),')
    p.write_text(s,newline='\n')
    p=d/'nes_joint266.sv';s=p.read_text()
    s=once(s,'wire [8:0] manifest_at282;', 'wire [3:0] ram_phase321,ram_next321;\nwire [8:0] manifest_at282;')
    for target in (' flow(', 'nes_joint257 core('):
        s=once(s,target,target+'.ram_phase321(ram_phase321),.ram_next321(ram_next321),')
    p.write_text(s,newline='\n')
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'output wire queue_admit319,', 'output wire [3:0] ram_phase321,input wire [3:0] ram_next321,output wire queue_admit319,')
    s=once(s,'reg [5:0] state;', 'reg [6:0] state;')
    names=['R'+x+'321' for x in phases]
    constants=' localparam '+','.join(n+'='+str(57+i) for i,n in enumerate(names))+';\n'
    decode=' assign ram_phase321='+''.join('state=='+n+'?4\'d'+str(i+1)+':' for i,n in enumerate(names))+"4'd0;\n"
    # Constants before any state reference; wire assignment after state decl.
    s=once(s,' localparam NONE=0,TILE=1,MAP=2;',constants+' localparam NONE=0,TILE=1,MAP=2;')
    s=once(s,'reg [6:0] state;', 'reg [6:0] state;\n'+decode)
    s=once(s,'wire receipt_done313=state==XWAIT298&&range_ready;',"wire receipt_done313=ram_phase321!=0&&ram_next321==0&&header[0]!=3;")
    s=s.replace('||state==MWAIT313','||((ram_phase321!=0)&&header[0]==3)')
    s=once(s,'SEND:if(mready)state<=XWAIT298;', 'SEND:if(mready)state<=(range_valid||ordinary_range)?RV_RREAD321:CONSUME;')
    a=s.index('     XWAIT298:if(range_ready)begin');b=s.index('     MREAD313:',a)
    s=s[:a]+s[b:]
    a=s.index('     MWAIT313:if(range_ready)begin');b=s.index('     MNEXT313:',a)
    body=s[a+len('     MWAIT313:if(range_ready)begin'):b]
    assert body.rstrip().endswith('end')
    body=body.rstrip()[:-3]
    s=s[:a]+s[b:]
    task=' task advance_manifest321;begin'+body+' end endtask\n'
    # Move task before main sequential always, after declaration section.
    at=s.rindex(' always @(posedge host_clk or posedge rst)begin')
    s=s[:at]+task+s[at:]
    s=once(s,'else state<=MWAIT313;', 'else if(canonical_read313)state<=display_byte313?RD_READ321:RV_CHECKREAD321;else advance_manifest321();')
    branch='     '+','.join(names)+':begin\n      case(ram_next321)\n'
    branch+='       0:if(header[0]==3)advance_manifest321();else state<=CONSUME;\n'
    branch+=''.join('       '+str(i+1)+':state<='+n+';\n' for i,n in enumerate(names))
    branch+='       default:failed<=1;\n      endcase\n     end\n'
    s=once(s,'     MREAD313:state<=MCAP313;',branch+'     MREAD313:state<=MCAP313;')
    # Common queue RAM fetch for descriptor / payload / manifest. No three
    # independent read/capture phase chains; retain one request kind.
    bodies={}
    for start,end,key in [('     DCAP:begin','     DCHECK:',0),('     PCAP:begin','     TILEWAIT313:',1),('     MCAP313:begin','     MISSUE313:',2)]:
        a=s.index(start);b=s.index(end,a);t=s[a+len(start):b].rstrip();assert t.endswith('end');bodies[key]=t[:-3]
        s=s[:a]+s[b:]
    for old in ('DREAD:state<=DCAP;','PREAD:state<=PCAP;','MREAD313:state<=MCAP313;'):
        s=once(s,'     '+old,'')
    for old,key in [('DREAD',0),('PREAD',1),('MREAD313',2)]:
        s=s.replace('state<='+old+';',f'begin read_kind321<=2\'d{key};state<=RAM_READ321;end ')
    # Decode-dependent predicates still refer to logical read/capture phases.
    for old,key,capture in [('DREAD',0,False),('DCAP',0,True),('PREAD',1,False),('PCAP',1,True),('MREAD313',2,False),('MCAP313',2,True)]:
        s=s.replace('state=='+old, f'(state==RAM_{"CAP" if capture else "READ"}321&&read_kind321==2\'d{key})')
    s=once(s,'reg [6:0] state;', "localparam RAM_READ321=67,RAM_CAP321=68;reg [1:0] read_kind321;\n reg [6:0] state;")
    # No reset needed for kind before a request, but initialize for evidence.
    s=s.replace('state<=IDLE;', 'read_kind321<=0;state<=IDLE;',1)
    dispatch='     RAM_READ321:state<=RAM_CAP321;\n     RAM_CAP321:case(read_kind321)\n'
    dispatch+=''.join(f'      2\'d{k}:begin{v}end\n' for k,v in bodies.items())
    dispatch+='      default:failed<=1;\n     endcase\n'
    # Bodies were extracted before replacing their internal next-read edges.
    for old,key in [('DREAD',0),('PREAD',1),('MREAD313',2)]:
        dispatch=dispatch.replace('state<='+old+';',f'begin read_kind321<=2\'d{key};state<=RAM_READ321;end ')
    s=once(s,'     DCHECK:',dispatch+'     DCHECK:')
    for old in ('DREAD','DCAP','PREAD','PCAP','MREAD313','MCAP313','XWAIT298','MWAIT313'):
        assert not re.search(r'\b'+old+r':',s) and 'state<='+old+';' not in s,old
    p.write_text(s,newline='\n')
    source_plan(d)

def source_plan(d):
    # One NES phase register: source phase followed by plan WAIT/READ/... .
    coreports='input wire [2:0] plan_next321,input wire plan_reset321,output wire [2:0] plan_state321,output wire plan_phase321,'
    planports='output reg [2:0] plan_next321,output wire plan_reset321,input wire [2:0] plan_state321,input wire plan_phase321,'
    p=d/'nes_plan_batch206.sv';s=p.read_text()
    s=once(s,' input wire [9:0] plan_cursor319,',' '+planports+'\n input wire [9:0] plan_cursor319,')
    s=once(s,'reg [2:0] state;', 'wire [2:0] state=plan_state321;\n assign plan_reset321=nr||nc;')
    feedback=''' always @*begin
  plan_next321=state;
  if(nr||nc)plan_next321=WAIT;
  else case(state)
   WAIT:if(word_valid)plan_next321=READ;
   READ:if(read_cursor314<batch_length&&remaining!=0&&remaining<=16&&
     !(at>=16&&alt_index>=8)&&!(at>=16&&!plan_alt_mask[alt_index]))plan_next321=CAPTURE;
   CAPTURE:plan_next321=at==length-1?CHECK:READ;
   CHECK:if(shape_ok&&lease_ok&&!(bg_closed295&&(partial295||plan_kind==0||plan_kind==2)))plan_next321=plan_kind==3?ENDING:READY;
   READY:if(plan_valid&&plan_ready)plan_next321=RUN;
   RUN:if(tile_done)plan_next321=remaining==1?WAIT:READ;
   ENDING:if(end_valid&&end_ready)plan_next321=WAIT;
   default:plan_next321=WAIT;
  endcase
 end
'''
    s=once(s,'\n integer i;\n', '\n'+feedback+' integer i;\n')
    s=re.sub(r'state<=[^;]+;', '', s)
    # Removing state assignments can leave empty if branches: use begin/end.
    s=s.replace('else ;','else begin end')
    s=s.replace('else \n','else begin end\n')
    s=s.replace('if(at==length-1)else begin', 'if(at==length-1)begin end else begin')
    s=s.replace('if(remaining==1)\n', 'if(remaining==1)begin end\n')
    s=s.replace('READY:if(plan_valid&&plan_ready)\n', 'READY:begin end\n')
    s=once(s,'   case(state)', '   if(plan_phase321)case(state)')
    for wire in ('word_ready','plan_valid','end_valid','plan_zero319','plan_step319'):
        s=once(s,'assign '+wire+'=', 'assign '+wire+'=plan_phase321&&')
    p.write_text(s,newline='\n')
    p=d/'nes_core257.sv';s=p.read_text()
    s=once(s,'module nes_core257(', 'module nes_core257('+coreports)
    s=once(s,'D_FETCH,D_RETURN} state_t;', 'D_FETCH,D_RETURN,P_READ321,P_CAPTURE321,P_CHECK321,P_READY321,P_RUN321,P_END321} state_t;')
    s=once(s,'assign output_phase=state==V_IDLE;', '''assign plan_phase321=state==V_IDLE||state==P_READ321||state==P_CAPTURE321||state==P_CHECK321||state==P_READY321||state==P_RUN321||state==P_END321;
 assign plan_state321=state==P_READ321?3'd1:state==P_CAPTURE321?3'd2:state==P_CHECK321?3'd3:state==P_READY321?3'd4:state==P_RUN321?3'd5:state==P_END321?3'd6:3'd0;
 assign output_phase=plan_phase321;''')
    s=once(s,'    V_IDLE:begin', '    V_IDLE,P_READ321,P_CAPTURE321,P_CHECK321,P_READY321,P_RUN321,P_END321:begin')
    s=once(s,'     if(v_display_ack)state<=IDLE;', '''     if(plan_reset321)state<=V_IDLE;
     else case(plan_next321)
      0:state<=V_IDLE;1:state<=P_READ321;2:state<=P_CAPTURE321;
      3:state<=P_CHECK321;4:state<=P_READY321;5:state<=P_RUN321;6:state<=P_END321;
      default:begin fault<=6;state<=V_IDLE;end
     endcase
     if(v_display_ack)state<=IDLE;''')
    p.write_text(s,newline='\n')
    conn='.plan_next321(plan_next321),.plan_reset321(plan_reset321),.plan_state321(plan_state321),.plan_phase321(plan_phase321),'
    for name,anchor,target,ports in [
        ('nes_joint257.sv','module nes_joint257(','nes_core257 encoder(',coreports),
        ('nes_joint266.sv','input wire plan_zero319,','nes_joint257 core(',coreports),
        ('nes_plan_path267.sv','input wire [9:0] plan_cursor319,',' transport(',planports.replace('output reg','output wire')),
        ('nes_plan_rom267.sv','input wire [9:0] plan_cursor319,',' transport(',planports.replace('output reg','output wire'))]:
        p=d/name
        if not p.exists():continue
        s=p.read_text();s=once(s,anchor,anchor+ports if anchor.startswith('module') else ports+anchor)
        s=once(s,target,target+conn);p.write_text(s,newline='\n')
    for name,instances in [('nes_live_joint.sv',('native_joint267','retained_plan267')),('joint266_tb.sv',('dut','planrom'))]:
        p=d/name
        if not p.exists():continue
        s=p.read_text();s=once(s,'wire queue_admit319,','wire [2:0] plan_next321,plan_state321;wire plan_reset321,plan_phase321;\nwire queue_admit319,')
        for instance in instances:s=once(s,instance+'(',instance+'('+conn)
        p.write_text(s,newline='\n')
