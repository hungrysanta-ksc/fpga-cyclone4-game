# SPDX-License-Identifier: MIT
"""Bounded early requirements storage; credit release is not consumption."""
from nes_delta231 import once
from nes_joint303 import apply as reader
from nes_prepare309 import native as preparation


def native(d):
    preparation(d)
    p=d/'nes_native289.c';s=p.read_text()
    s=once(s,'unsigned preparation_pending309(void)', 'unsigned preparation_ready310(void){return prepared309==207;}\nunsigned preparation_pending309(void)')
    p.write_text(s,newline='\n')
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,'static unsigned phase(unsigned bit,unsigned error){','static unsigned early310(void);\nstatic unsigned phase(unsigned bit,unsigned error){')
    s=once(s,'if(!status(0,bit))return 0;}return fail(error);','if(!status(0,bit))return 0;if(bit==2&&!(status259[7]&2)&&!early310())return 0;}return fail(error);')
    a=s.index('   for(unsigned i=0;i<206;i++)wire259[i+1]=seal262[i];',s.index('if((p[0]==10||p[0]==11)'))
    b=s.index('   if(!send(encoded307))return 0;requirements264=1;',a)
    encoder=s[a:b]
    s=s[:a]+'   unsigned encoded307=encode310();\n'+s[b:]
    anchor='static unsigned begin,seal,requirements264;'
    helper='''static unsigned begin,seal,requirements264;
static unsigned encode310(void){
 const uint8_t *seal262=seal289;
'''+encoder+''' return encoded307;
}
extern unsigned preparation_ready310(void),supply303(void);
static unsigned early310(void){
 /* Called only after a checked phase-2 poll, outside io259, with no packet
  * under construction. DMA-ready and plan credit take priority. */
 if(requirements264||!begin||!preparation_ready310()||supply303()||batch_bytes260||
    (uint16_t)(state259.sent-state259.retired)>=4)return 1;
 unsigned n=encode310();
 if(wire259[2]!=1||n>106)return 1; /* retained late/raw fallback */
 wire259[2]=2;
 if(!send(n))return 0;
 requirements264=2;return 1;
}
'''
    s=once(s,anchor,helper)
    s=once(s,' const uint8_t *seal262=seal289;\n  if(n!=16','  if(n!=16')
    s=once(s,'if(requirements264&&p[0]!=10&&p[0]!=11)', 'if(requirements264==1&&p[0]!=10&&p[0]!=11)')
    p.write_text(s,newline='\n')


def apply(d):
    reader(d)
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'input wire reader_step303,','input wire reader_step303,input wire stored310,')
    s=once(s,'localparam XBEGIN298=40,XWAIT298=41;', 'localparam XBEGIN298=40,XWAIT298=41,REPLAY310=42,REPLAYWAIT310=43;')
    s=once(s,"header[1]==1?(qlen<42||qlen>206):1'b1", "header[1]==1?(qlen<42||qlen>206):header[1]==2?(qlen<42||qlen>106||stored310):1'b1")
    s=once(s,'(state==XBEGIN298||state==SEND', '(state==REPLAY310||state==XBEGIN298||state==SEND')
    s=once(s,'state==XBEGIN298?(header[0]==3', '(state==XBEGIN298||state==REPLAY310)?(header[0]==3')
    s=once(s,"assign exec_op298=header[0]==15&&header[1]==1?4'd4:header[0][3:0];", "assign exec_op298=(state==REPLAY310||state==REPLAYWAIT310)?4'd6:header[0]==15?(header[1]==2?4'd5:header[1]==1?4'd4:4'd15):header[0][3:0];")
    s=once(s,'else if(header[0]==15||header[0]==10||header[0]==11||header[0]==3)begin', '''else if((header[0]==10||header[0]==11)&&stored310)state<=REPLAY310;
      else if(header[0]==15||header[0]==10||header[0]==11||header[0]==3)begin''')
    s=once(s,'     XBEGIN298:if(range_ready)', '''     REPLAY310:if(range_ready)state<=REPLAYWAIT310;
     REPLAYWAIT310:if(exec_done298)state<=CHECK;
     XBEGIN298:if(range_ready)''')
    p.write_text(s,newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'output wire reader_step303,','output wire reader_step303,output reg stored310,')
    s=once(s,'wire requirements307=exec_op298==4;', '''reg [6:0] stored_length310;
 wire replay310=exec_op298==6;
 wire [8:0] length310=replay310?{2'd0,stored_length310}:exec_length298;
 wire [7:0] data310=replay310?ram_q:exec_data298;
 wire requirements307=exec_op298==4||replay310;''')
    # Decoder and reader use the admitted stored length only during replay.
    s=s.replace('packet_at298<exec_length298','packet_at298<length310')
    step=next(x for x in s.splitlines(True) if 'assign reader_step303=' in x)
    s=s.replace(step,'');s=s.replace('wire requirements307=exec_op298==4||replay310;', 'wire requirements307=exec_op298==4||replay310;\n'+step)
    start=s.index('    E_CAP298:');end=s.index('    E_ZERO298:',start)
    tail=s[start:end].replace('exec_length298','length310').replace('exec_data298','data310')
    tail=once(tail,'if(packet_at298>=length310)fault<=3;', '''if(packet_at298>=length310)fault<=3;
     else if(exec_op298==5)begin
      if(packet_at298+1==length310)begin stored310<=1;complete_execution298();end
      else state<=E_READ298;
     end''')
    tail=once(tail,'else begin complete_execution298();', 'else begin if(replay310)stored310<=0;complete_execution298();')
    s=s[:start]+tail+s[end:]
    s=once(s,"wire [9:0] run_end307=cursor+{3'd0,exec_data298[6:0]}","wire [9:0] run_end307=cursor+{3'd0,data310[6:0]}")
    s=once(s,'   V_CLEARALL,V_CLEARFRAME,V_RAWINVALID:', '''   E_READ298,E_CAP298:if(exec_op298==5||replay310)begin
    v_addr=10'd150+{1'b0,packet_at298};
    v_we=exec_op298==5&&state==E_CAP298&&packet_at298>=16&&packet_at298<length310;
    v_wdata=exec_data298;
   end
   V_CLEARALL,V_CLEARFRAME,V_RAWINVALID:''')
    s=once(s,'  if(reset)begin','  if(reset)begin stored310<=0;stored_length310<=0;')
    s=once(s,'end else if(abort_source)begin','end else if(abort_source)begin stored310<=0;')
    s=once(s,'active<=1;context_complete<=0;', 'stored310<=0;active<=1;context_complete<=0;')
    s=once(s,'if(exec_length298<=16||', '''if(exec_op298==5)begin
         if(stored310||map_phase305||cursor!=0||rec_i!=0||exec_length298<42||exec_length298>106)fault<=3;
         else begin stored_length310<=exec_length298[6:0];state<=E_READ298;end
        end else if(replay310)begin
         if(!stored310||map_phase305||cursor!=0||rec_i!=0)fault<=3;else state<=E_READ298;
        end else if(stored310||exec_length298<=16||''')
    s=once(s,'if((!map_phase305||cursor!=256)||rec_i!=24', 'if(stored310||(!map_phase305||cursor!=256)||rec_i!=24')
    p.write_text(s,newline='\n')
    for name in ('nes_joint257.sv','nes_joint266.sv','nes_joint267_board.sv'):
        p=d/name
        if not p.exists():continue
        s=p.read_text().replace('.reader_step303(reader_step303),','.reader_step303(reader_step303),.stored310(stored310),')
        s=s.replace('wire reader_step303;', 'wire reader_step303,stored310;')
        s=s.replace('output wire reader_step303,','output wire reader_step303,output wire stored310,')
        p.write_text(s,newline='\n')


def reference(d):
    p=d/'nes_producer264.c';s=p.read_text()
    s=once(s,'section!=1||a<42','(section!=1&&section!=2)||a<42')
    p.write_text(s,newline='\n')


def observe(s):
    s=once(s,'!((dut.core.ram_b_addr<166)', '!((dut.core.validator.exec_op298==5&&dut.core.validator.state==dut.core.validator.E_CAP298&&dut.core.ram_b_addr>=166&&dut.core.ram_b_addr<256)||(dut.core.ram_b_addr<166)')
    s=once(s,'   event267=cpu267[cpu_at267];cpu_at267++;', '''   event267=cpu267[cpu_at267];cpu_at267++;
   // Only physical sequence is rebound; bus events/timing remain fixed.
   if(event267[31:8]==24'h400002||event267[31:8]==24'h006012)event267[7:0]=dut.flow.packet_seq[7:0];
   if(event267[31:8]==24'h400003||event267[31:8]==24'h006013)event267[7:0]=dut.flow.packet_seq[15:8];''')
    return once(s,' task clear_output;', r"""
 integer stores310=0,replays310=0;
 always @(posedge host_clk)if(!reset&&active263)begin
  if(dut.flow.qretire&&dut.flow.header[0]==15&&dut.flow.header[1]==2)begin
   if(!dut.stored310||dut.core.validator.rec_i!=0||dut.core.validator.map_phase305||v_sealed)$fatal(1,"storage credit became consumption");
   stores310++;
   $fwrite(events261,"store310,%0d,%0d,%0d,%0t\n",f,dut.flow.packet_seq,dut.flow.queue.retired,$time);
  end
  if(dut.flow.state==dut.flow.REPLAYWAIT310&&dut.exec_done298)begin
   if(dut.stored310||!dut.core.validator.map_phase305||dut.core.validator.rec_i!=24||dut.flow.qretire)$fatal(1,"replay retired current map head");
   replays310++;
   $fwrite(events261,"replay310,%0d,%0d,%0d,%0t\n",f,dut.flow.packet_seq,dut.flow.queue.retired,$time);
  end
  if(dut.flow.state==dut.flow.REPLAYWAIT310&&!dut.flow.qr)$fatal(1,"replay lost map head");
  if(dut.exec_done298&&dut.core.ram_b_we)$fatal(1,"completion before RAM write");
 end
 task clear_output;""")
