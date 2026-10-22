# SPDX-License-Identifier: MIT
"""One queue cursor/port owner and state-owned receipt completion."""
from nes_delta231 import once
from nes_slice302c import native as previous

CONNECT='.reader_at303(reader_at303),.reader_step303(reader_step303),'

def apply(d):
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'input wire [7:0] exec_addr298,','output wire [8:0] reader_at303,input wire reader_step303,')
    s=once(s,'reg [7:0] at,held,parser_address;','reg [7:0] at,held;reg [8:0] reader303;\n assign reader_at303=reader303;')
    s=s.replace('parser_address','reader303')
    s=once(s,'exec_busy298?exec_addr298:reader303','reader303[7:0]')
    # A single host-clock register owns queue reads in every internal phase.
    # NORMAL hands only the address port to SNES; its CRC observer stays live.
    s=once(s,'    case(state)', '''    if(state!=NORMAL)begin
     if(exec_start298&&exec_kind298!=0)reader303<=9'd16;
     else if(exec_busy298&&reader_step303)reader303<=reader303+1'b1;
    end
    case(state)''')
    p.write_text(s,newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'output wire [7:0] exec_addr298,','input wire [8:0] reader_at303,output wire reader_step303,')
    s=once(s,'E_CERT298,E_SEAL298}', 'E_CERT298,E_SEAL298,E_DONE303,E_DISPLAY_DONE303}')
    s=once(s,'reg executing298,complete298;reg [8:0] packet_at298;', 'reg executing298;wire [8:0] packet_at298=reader_at303;')
    s=once(s,'assign exec_done298=complete298&&!reset&&!abort_source&&!fault;', 'assign exec_done298=(state==E_DONE303||state==E_DISPLAY_DONE303)&&!reset&&!abort_source&&!fault;')
    s=once(s,'assign exec_addr298=packet_at298[7:0];', 'assign reader_step303=state==E_CAP298&&packet_at298<exec_length298&&!reset&&!abort_source&&!fault;')
    s=s.replace('complete298<=0;','').replace('packet_at298<=0;','').replace('packet_at298<=16;','').replace("packet_at298<=packet_at298+1'b1;",'')
    s=once(s,'executing298<=0;complete298<=1;', 'executing298<=0;state<=E_DONE303;')
    s=s.replace('complete_execution298();state<=V_ACTIVE;', 'complete_execution298();')
    s=once(s,'state<=V_WAITDISPLAY;complete_execution298();', 'complete_execution298();state<=E_DISPLAY_DONE303;')
    s=once(s,'    E_READ298:state<=E_CAP298;', '    E_DONE303:state<=V_ACTIVE;\n    E_DISPLAY_DONE303:state<=V_WAITDISPLAY;\n    E_READ298:state<=E_CAP298;')
    p.write_text(s,newline='\n')
    for name in ('nes_joint257.sv','nes_joint266.sv','nes_joint267_board.sv'):
        p=d/name
        if not p.exists():continue
        s=p.read_text().replace('.exec_addr298(exec_addr298),',CONNECT)
        s=s.replace('exec_data298,exec_addr298;', 'exec_data298;wire [8:0] reader_at303;wire reader_step303;')
        # Core boundary passes signals between flow and validator unchanged.
        s=s.replace('output wire [7:0] exec_addr298,','input wire [8:0] reader_at303,output wire reader_step303,')
        p.write_text(s,newline='\n')


def observe(s):
    return once(s,' task clear_output;', '''
 reg [8:0] reader_prev303;reg normal_prev303;
 always @(posedge host_clk)begin
  if(!reset&&active263)begin
   if(dut.flow.state==dut.flow.NORMAL&&dut.exec_busy298)$fatal(1,"queue port has two owners");
   if(normal_prev303&&dut.flow.state==dut.flow.NORMAL&&dut.flow.reader303!=reader_prev303)$fatal(1,"SNES owner changed internal cursor");
   if(dut.reader_step303&&!dut.exec_busy298)$fatal(1,"unowned queue read completion");
   if(dut.exec_done298&&dut.core.ram_b_we)$fatal(1,"receipt completion before final RAM write");
  end
  reader_prev303<=dut.flow.reader303;normal_prev303<=!reset&&dut.flow.state==dut.flow.NORMAL;
 end
 task clear_output;''')


def native(d):
    previous(d)
    p=d/'nes_refill267.c';s=p.read_text()
    # Unknown credit requires a checked progress response before computing.
    # A known full plan bank can hide computation; a writable bank must drain.
    s=once(s,'static int work302(void){','''unsigned supply303(void){
 return plan_at267<plan_bytes267&&(!plan_cache282||(plan_flags282&1));
}
static int work302(void){''')
    s=once(s,'slices302<2048&&pending302()&&!progress302()', 'slices302<2048&&pending302()&&!supply303()&&!progress302()')
    p.write_text(s,newline='\n')
