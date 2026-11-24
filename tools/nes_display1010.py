"""Build a passive alternative to the MMC966 tile-detail observer on the 964 project."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUARTUS = Path('C:/altera_lite/25.1std/quartus/bin64')


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(before)
    return text.replace(before, after)


def project(temp):
    src = temp/'nes-trial816-board964'
    dst = temp/'nes-display1010-boardD'
    ref = json.loads((ROOT/'analysis/trial966-package.json').read_bytes())
    if hashlib.sha256((src/'output_files/board.sof').read_bytes()).hexdigest() != ref['image']['SOF']:
        raise ValueError('different reference board')
    dst.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(src/sub, dst/sub)
    for f in src.iterdir():
        if f.suffix in ('.sv','.v','.vhd','.qpf','.qsf','.sdc','.hex','.tcl'):
            shutil.copyfile(f, dst/f.name)
    shutil.copyfile(ROOT/'tests/nes-functional/nes_display1010.sv',dst/'nes_display1010.sv')
    qsf = dst/'board.qsf'
    qsf.write_text(once(qsf.read_text(),'SYSTEMVERILOG_FILE nes_supply905.sv',
                        'SYSTEMVERILOG_FILE nes_display1010.sv'), newline='\n')
    sdc = dst/'board.sdc'
    s = sdc.read_text()
    a = s.index('foreach i {0 1 2} {\n set src905')
    b = s.index('\n}',a)+2
    s = s[:a]+'''set src1010 [cdc181_exact {nes_live_joint:core|nes_direct206:direct_path|nes_source_tile192:source|evt905[2]}]
set dst1010 [cdc181_exact {nes_screen_status151:screen_status|nes_display1010:trace|done_sync[0]}]
set_max_delay 11.904 -from $src1010 -to $dst1010
set_false_path -hold -from $src1010 -to $dst1010'''+s[b:]
    sdc.write_text(s,newline='\n')
    top = dst/'fxpak_nes_screen137_top.sv'
    s = top.read_text()
    # Declare the sink STOP signals before use so no implicit scalar is created.
    for decl in ('(* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] sink_rom_fault;',
                 'wire host_cancel_reset;'):
        s = once(s,decl,'')
        s = once(s,' wire tr_head', ' '+decl+'\n wire tr_head')
    s = once(s,'screen_status(.evt905','screen_status(.trace_cancel(host_cancel_reset || sink_rom_fault[1] || native_spi_fault || sink_fault),.evt905')
    top.write_text(s,newline='\n')
    status = dst/'nes_screen_status151.sv'
    s = once(status.read_text(),'module nes_screen_status151(', 'module nes_screen_status151(input wire trace_cancel,')
    a = s.index(' nes_supply905 trace(')
    b = s.index(' assign selected=',a)
    s = s[:a]+''' nes_display1010 trace(.clk(clk),.reset(reset),.active(active_sync[1]),.cancel(trace_cancel),
  .first_e9(first905),.writer(writer903),.returned(ret905),.tile_done(evt905[2]),
  .token(token903),.generation(tr_gen),.header(tr_head),.data(tr_data),.retired(tr_retired),.op(tr_op),
  .dma(wr_end && !rd_previous && addr_sync[23:16]==8'h7f &&
       (pa_prev==8'h18 || pa_prev==8'h19 || pa_prev==8'h22 || pa_prev==8'h04)),
  .show(wr_end && pa_prev==0),.query(trace_byte && byte_count==0 && incoming==8'h78),
  .index(byte_count),.reply(trace_reply));
'''+s[b:]
    status.write_text(s,newline='\n')
    return dst


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('--compile',action='store_true')
    args=p.parse_args()
    dst=project(args.temp)
    if args.compile:
        with (dst/'compile.log').open('wb') as log:
            subprocess.run([QUARTUS/'quartus_sh.exe','--flow','compile','board'],
                           cwd=dst,stdout=log,stderr=subprocess.STDOUT,check=True)
