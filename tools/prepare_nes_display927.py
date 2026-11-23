"""Build the passive MMC927 observer on the installed MMC925 board sources."""
import argparse
import shutil
from pathlib import Path
from types import SimpleNamespace

from prepare_nes_frame900 import QUARTUS, ROOT, fit, image


def board(temp,source=None):
    src=source or temp/'nes-board925/board925'
    dest=temp/'nes-trial816-board927'
    dest.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(src/sub,dest/sub)
    for file in src.iterdir():
        if file.suffix in ('.sv','.v','.vhd','.qpf','.qsf','.sdc','.hex','.tcl'):
            shutil.copyfile(file,dest/file.name)
    shutil.copyfile(ROOT/'tests/nes-functional/nes_display927.sv',dest/'nes_display927.sv')
    qsf=dest/'board.qsf'
    qsf.write_text(qsf.read_text().replace('SYSTEMVERILOG_FILE nes_supply905.sv',
                                           'SYSTEMVERILOG_FILE nes_display927.sv'))
    sdc=dest/'board.sdc'
    text=sdc.read_text()
    a=text.index('foreach i {0 1 2} {\n set src905')
    assert text[a:].strip().endswith('set_false_path -hold -from $src905 -to $dst905\n}')
    sdc.write_text(text[:a])  # Only the removed NES-domain observer pins.
    status=dest/'nes_screen_status151.sv'
    s=status.read_text()
    a=s.index(' nes_supply905 trace(')
    b=s.index(' assign selected=',a)
    status.write_text(s[:a]+""" wire dest927=pa_prev==8'h18 || pa_prev==8'h19 || pa_prev==8'h22 || pa_prev==8'h04;
 nes_display927 trace(.clk(clk),.reset(reset),.active(active_sync[1]),.first_e9(first905),.writer(writer903),
   .begin_frame(tr_retired && tr_op==1),.seal(tr_head && tr_data==3),
   .dma(wr_end && !rd_previous && addr_sync[23:16]==8'h7f && dest927),
   .port_code(pa_prev==8'h18 ? 2'd0 : pa_prev==8'h19 ? 2'd1 : pa_prev==8'h22 ? 2'd2 : 2'd3),
   .show(wr_end && pa_prev==0),.ack(tr_retired && tr_op==3),.generation(tr_gen),
   .query(trace_byte && byte_count==0 && incoming==8'h78),.index(byte_count),.reply(trace_reply));
"""+s[b:])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('task',choices=('board','fit','image'))
    p.add_argument('temp',type=Path)
    p.add_argument('--source',type=Path,help='routed MMC925 source directory for a separate build root')
    args=p.parse_args()
    if args.task=='board': board(args.temp,args.source)
    elif args.task=='fit': fit(args.temp,927,QUARTUS)
    else: image(SimpleNamespace(board=args.temp/'nes-trial816-board927',out=args.temp/'nes-image927',
                                quartus=QUARTUS,number='927'))
