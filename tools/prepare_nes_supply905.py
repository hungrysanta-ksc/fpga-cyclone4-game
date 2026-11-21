"""Generate the passive supply observer against the physically tested MMC903 board."""
import argparse
import shutil
from pathlib import Path
from types import SimpleNamespace
from prepare_nes_frame900 import ROOT, PROBES, QUARTUS, fit, image, replace
from prepare_nes_trial802 import rename_edition

WORK=PROBES/'nes-supply905'
BASE=PROBES/'nes-tile903/link'

def board(temp):
    src=temp/'nes-trial816-board903'
    dst=temp/'nes-trial816-board905'
    dst.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(src/sub,dst/sub)
    for f in src.iterdir():
        if f.suffix in ('.sv','.v','.vhd','.qpf','.qsf','.sdc','.hex','.tcl'):
            shutil.copyfile(f,dst/f.name)
    shutil.copyfile(ROOT/'tests/nes-functional/nes_supply905.sv',dst/'nes_supply905.sv')
    constrain(dst)
    replace(dst/'board.qsf','SYSTEMVERILOG_FILE nes_tile_trace903.sv','SYSTEMVERILOG_FILE nes_supply905.sv')
    p=dst/'nes_source_tile192.sv'
    replace(p,' input wire cap_start,',' output reg [2:0] evt905,\n input wire cap_start,')
    replace(p,' assign drained=',' always @(posedge clk) evt905<=reset||stop ? 0 : {done,arb_request&&arb_ready,arb_request};\n assign drained=')
    # E9 opcode at the shared wire. Accepted-count zero identifies the first plan.
    p=dst/'nes_plan_spi200.sv'
    replace(p,'output wire snap903,','output wire first905,output wire snap903,')
    replace(p,' assign snap903='," assign first905=live&&!ss[1]&&sck[1]&&!prev_sck&&bits==7&&count==0&&incoming==8'he9&&accepted==0;\n assign snap903=")
    decl='wire [2:0] evt905,'
    more='wire first905,ret905,'
    width='wire [7:0] units905,'
    names=('evt905','first905','ret905','units905')
    conn=''.join('.%s(%s),'%(k,k) for k in names)
    for module in ('nes_direct206','nes_live_joint','nes_screen_status151'):
        direction='input ' if module=='nes_screen_status151' else 'output '
        replace(dst/(module+'.sv'),'module '+module+'(','module '+module+'('+direction+decl+direction+more+direction+width)
    p=dst/'nes_direct206.sv'
    replace(p,' assign ready903=',' assign ret905=consume&&chunk_ready&&consume_token==chunk_token,units905=chunk_length[11:4];\n assign ready903=')
    replace(p,' source(.cap_start',' source(.evt905(evt905),.cap_start')
    replace(p,'endpoint(.snap903','endpoint(.first905(first905),.snap903')
    replace(dst/'nes_live_joint.sv','direct_path(.writer903','direct_path('+conn+'.writer903')
    p=dst/'fxpak_nes_screen137_top.sv'
    replace(p,'nes_live_joint core(','wire [2:0] evt905; wire first905,ret905;wire [7:0] units905;\n nes_live_joint core('+conn)
    replace(p,'screen_status151 screen_status(','screen_status151 screen_status('+conn)
    p=dst/'nes_screen_status151.sv'
    s=p.read_text()
    a=s.index(' nes_tile_trace903 trace(');b=s.index(' assign selected=',a)
    p.write_text(s[:a]+""" wire trace_byte=!ss_sync[1]&&sck_sync[1]&&!sck_previous&&bit_count==7;
 nes_supply905 trace(.clk(clk),.reset(reset),.active(active_sync[1]),.first_e9(first905),
  .writer(writer903),.reader(reader903),.returned(ret905),.kind(kind903),.units(units905),
  .nes_events(evt905),.token(token903),.generation(tr_gen),
  .query(trace_byte&&byte_count==0&&incoming==8'h78),
  .set_page(trace_byte&&byte_count==1&&command==8'h78),.page_in(incoming),
  .index(byte_count),.reply(trace_reply));
"""+s[b:],newline='\n')

def constrain(dst):
    # Only the three asynchronous inputs to the first observer flop.
    # Their source pulse width is >=45 ns; keep route delay under one
    # destination period. The next two sampling flops stay fully timed.
    with (dst/'board.sdc').open('a') as f:
        f.write("""
foreach i {0 1 2} {
 set src905 [cdc181_exact [format {nes_live_joint:core|nes_direct206:direct_path|nes_source_tile192:source|evt905[%d]} $i]]
 set dst905 [cdc181_exact [format {nes_screen_status151:screen_status|nes_supply905:trace|meta[%d]} $i]]
 set_max_delay 11.904 -from $src905 -to $dst905
 set_false_path -hold -from $src905 -to $dst905
}
""")

if __name__=='__main__':
    import sys
    action=sys.argv[1]; temp=Path(sys.argv[2])
    if action=='board':board(temp)
    elif action=='fit':fit(temp,905,QUARTUS)
    elif action=='image':image(SimpleNamespace(board=temp/'nes-trial816-board905',out=temp/'nes-supply905-image',quartus=QUARTUS,number='905'))
