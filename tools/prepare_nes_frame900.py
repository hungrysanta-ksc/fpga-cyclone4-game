"""Prepare the two matched hardware observers on their respective production boards."""
import argparse
import shutil
from pathlib import Path
from types import SimpleNamespace

from package_nes_trial704 import image, read, sha
from prepare_nes_trial802 import PROBES
from prepare_nes_trial816 import fit
from prepare_nes_frame862 import replace

ROOT=Path(__file__).resolve().parents[1]
WORK=PROBES/'nes-frame900'
QUARTUS=Path('C:/altera_lite/25.1std/quartus/bin64')
PARENTS={900:(872,872,'nes-trial872/link-credit','nes-trial872/client02'),
         901:(897,892,'nes-sram897/link','nes-trial890/client02')}


def board(temp,n):
    parent,project,_,client=PARENTS[n]
    src=temp/f'nes-trial816-board{project}'
    out=temp/f'nes-trial816-board{n}'
    expected=read(ROOT/f'analysis/trial{parent}-package.json')
    assert sha(PROBES/client/'sink165.sfc')==expected['client']
    assert (PROBES/client/'sink-program.hex').read_bytes()==(src/'sink-program.hex').read_bytes()
    out.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(src/sub,out/sub)
    for p in src.iterdir():
        if p.suffix in ('.sv','.v','.vhd','.qpf','.qsf','.sdc','.hex','.tcl'):
            shutil.copyfile(p,out/p.name)
    shutil.copyfile(ROOT/'tests/nes-functional/nes_frame900.sv',out/'nes_frame900.sv')
    pins=[s for s in (ROOT/'src/fpga/pin.qsf').read_text().splitlines()
          if ('SNES_PA_IN[' in s or 'SNES_PAWR_IN' in s) and
          ('set_location_assignment' in s or 'IO_STANDARD' in s)]
    assert len(pins)==18
    with (out/'board.qsf').open('a') as f:
        f.write('\n'+'\n'.join(pins)+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_frame900.sv\n')
    obs=out/'nes_run_observer134.sv'
    s=obs.read_text()
    obs.write_text(s[:s.index(' nes_ppu_history157 history(')]+
                   " assign pad_page=56'd0,history_page157=56'd0;\n"+s[s.index(' reg [7:0] reply;'):])
    top=out/'fxpak_nes_screen137_top.sv'
    replace(top,'input wire CLKIN,SNES_SYSCLK,','input wire CLKIN,SNES_SYSCLK,SNES_PAWR_IN,input wire [7:0] SNES_PA_IN,')
    ports='output wire tr_head,tr_section,tr_retired,output wire [7:0] tr_data,tr_op,output wire [15:0] tr_gen,'
    wires='wire tr_head,tr_section,tr_retired;wire [7:0] tr_data,tr_op;wire [15:0] tr_gen;'
    args='.tr_head(tr_head),.tr_section(tr_section),.tr_retired(tr_retired),.tr_data(tr_data),.tr_op(tr_op),.tr_gen(tr_gen),'
    replace(top,' nes_screen_status151 screen_status(',' '+wires+'\n nes_screen_status151 screen_status('+args+
            '.pawr_n(SNES_PAWR_IN),.port_id(SNES_PA_IN),')
    replace(top,'nes_sink_bridge165 sink(','nes_sink_bridge165 sink('+args)
    bridge=out/'nes_sink_bridge165.sv'
    replace(bridge,'module nes_sink_bridge165(', 'module nes_sink_bridge165('+ports)
    replace(bridge,'nes_sink_bus165 bus(','nes_sink_bus165 bus(.tr_head(tr_head),.tr_section(tr_section),.tr_data(tr_data),')
    replace(bridge,'nes_sink_spi165 endpoint(','nes_sink_spi165 endpoint(.tr_retired(tr_retired),.tr_op(tr_op),.tr_gen(tr_gen),')
    bus=out/'nes_sink_bus165.sv'
    replace(bus,'module nes_sink_bus165(','module nes_sink_bus165(output wire tr_head,tr_section,output wire [7:0] tr_data,')
    replace(bus,' wire local_bank=',""" wire tr_read=read_sync && !read_previous && packet_ready;
 assign tr_head=tr_read && address_previous==24'h400000;
 assign tr_section=tr_read && address_previous==24'h400001;
 assign tr_data=data_previous;
 wire local_bank=""")
    endpoint=out/'nes_sink_spi165.sv'
    replace(endpoint,'module nes_sink_spi165(','module nes_sink_spi165(output wire tr_retired,output wire [7:0] tr_op,output wire [15:0] tr_gen,')
    replace(endpoint,' wire idle_receipt=',""" reg previous_retired;
 always @(posedge clk) previous_retired<=retired[0];
 assign tr_retired=!reset && !fault && previous_retired!=retired[0];
 assign tr_op=ack_work[15:8],tr_gen=ack_work[79:64];
 wire idle_receipt=""")
    p=out/'nes_screen_status151.sv'
    replace(p,'input wire clk,reset,active,','input wire clk,reset,active,pawr_n,input wire [7:0] port_id,'+ports.replace('output','input'))
    replace(p,'reg [3:0] byte_count','reg [4:0] byte_count')
    replace(p,'byte_count!=9','byte_count!=31')
    replace(p,"command==8'h73&&","(command==8'h73||command==8'h78)&&")
    line='miso_hold<=reply[7-bit_count];' if parent==872 else 'miso_hold<=snapshot[55];'
    replace(p,line,line.replace('<=',"<=command==8'h78?trace_reply[7-bit_count]:".replace("78?","78 ? ")))
    replace(p,' assign selected=',""" (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] pawr_sync;
 reg pawr_prev;reg [7:0] pa_meta,pa_sync,pa_prev;
 always @(posedge clk)begin
  pawr_sync<={pawr_sync[0],pawr_n};pawr_prev<=pawr_sync[1];
  pa_meta<=port_id;pa_sync<=pa_meta;pa_prev<=pa_sync;
 end
 wire wr_end=pawr_sync[1]&&!pawr_prev;
 wire [7:0] trace_reply;
 nes_frame900 trace(.clk(clk),.reset(reset),.active(active_sync[1]),.header(tr_head),.section(tr_section),
  .data(tr_data),.retired(tr_retired),.op(tr_op),.generation(tr_gen),
  .dma(wr_end && !rd_previous && addr_sync[23:16]==8'h7f &&
       (pa_prev==8'h18 || pa_prev==8'h19 || pa_prev==8'h22 || pa_prev==8'h04)),
  .show(wr_end && pa_prev==0),.query(!ss_sync[1]&&sck_sync[1]&&!sck_previous&&bit_count==7&&
       byte_count==0&&incoming==8'h78),.index(byte_count),.reply(trace_reply));
 assign selected=""")


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=('board','fit','image'))
    p.add_argument('temp',type=Path)
    p.add_argument('edition',type=int,choices=PARENTS)
    a=p.parse_args()
    if a.action=='board':board(a.temp,a.edition)
    elif a.action=='fit':fit(a.temp,a.edition,QUARTUS)
    else:image(SimpleNamespace(board=a.temp/f'nes-trial816-board{a.edition}',
               out=a.temp/f'nes-frame900-final{a.edition}',quartus=QUARTUS,number=str(a.edition)))
