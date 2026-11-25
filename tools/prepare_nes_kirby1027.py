"""Instrument the verified Kirby board's existing 32-byte sampled header."""
from pathlib import Path
import argparse
import shutil


def replace(path, old, new):
    s = path.read_bytes().decode().replace('\r\n', '\n')
    if s.count(old) != 1:
        raise ValueError(f'{path}: expected exactly one {old!r}')
    path.write_bytes(s.replace(old, new).encode())


def board(base, out):
    out.mkdir(parents=True, exist_ok=False)
    for src in base.iterdir():
        if src.is_file() and src.suffix in {'.sv','.v','.vhd','.sdc','.tcl','.qsf','.qpf','.hex','.mif','.qip'}:
            shutil.copy2(src, out/src.name)
    for name in ('rtl','sys'):
        shutil.copytree(base/name, out/name)
    def edit(name, old, new):
        replace(out/(name+'.sv'),old,new)
    # Sample the actual foreground path at its native edge; requests that
    # only fill the speculative cache never set these two bits.
    edit('nes_e9_rows914',' input wire page963',' output wire fg1027, input wire page963')
    edit('nes_e9_rows914',' wire needed=', ' assign fg1027=foreground;\n wire needed=')
    edit('nes_source_tile192',' always @(posedge clk) evt905', ' wire fg1027;\n always @(posedge clk) evt905')
    edit('nes_source_tile192','{done,shared_req&&shared_ready,shared_req}', '{done,fg1027&&shared_ready,fg1027}')
    edit('nes_source_tile192',' ahead(.page963',' ahead(.fg1027(fg1027),.page963')
    # announced means a split marker was accepted before this plan. A
    # full 2048-byte aperture may also split within a contiguous slot run.
    edit('nes_tile_bulk206','module nes_tile_bulk206(', 'module nes_tile_bulk206(output reg [1:0] edge1027,')
    edit('nes_tile_bulk206',' wire input_ok=', ''' always @(posedge nes_clk)
  edge1027<=sc ? 2'b0 : {end_valid&&end_ready,plan_taken&&(announced||slength==0)};
 wire input_ok=''')
    for name in ('nes_direct206','nes_live_joint'):
        edit(name,f'module {name}(',f'module {name}(output wire [1:0] edge1027,')
    for name,instance in [('nes_direct206','bulk'),('nes_live_joint','direct_path'),('fxpak_nes_screen137_top','core')]:
        edit(name,instance+'(.',instance+'(.edge1027(edge1027),.')
    edit('fxpak_nes_screen137_top',' wire [2:0] evt905',' wire [1:0] edge1027; wire [2:0] evt905')
    edit('fxpak_nes_screen137_top','screen_status(.','screen_status(.edge1027(edge1027),.')
    edit('nes_screen_status151','(input wire trace_cancel','(input wire [1:0] edge1027,input wire trace_cancel')
    edit('nes_screen_status151',' trace(.clk',' trace(.edge1027({edge1027,evt905[1:0]}),.head_snapshot(snap903&&ready903),.clk')
    # The boot reply already has byte/bit cursors. Freeze it on the command
    # edge and reuse those cursors instead of shifting the whole 56-bit word.
    edit('nes_screen_status151',' reg miso_hold;', ''' reg miso_hold;
 reg [7:0] status_byte;
 always @* case(byte_count)
  1:status_byte=snapshot[55:48];2:status_byte=snapshot[47:40];
  3:status_byte=snapshot[39:32];4:status_byte=snapshot[31:24];
  5:status_byte=snapshot[23:16];6:status_byte=snapshot[15:8];
  7:status_byte=snapshot[7:0];default:status_byte=0;
 endcase''')
    edit('nes_screen_status151',"trace_reply[7-bit_count]:snapshot[55];snapshot<={snapshot[54:0],1'b0};",
         "trace_reply[7-bit_count]:status_byte[7-bit_count];")
    # Status capture runs before RUN admission. Only its synchronized
    # second stage is shared. Mask the sink's first two clocks after each
    # session reset to reproduce its original zero-initialized pipeline.
    edit('nes_screen_status151','(input wire [1:0] edge1027',
         '(output wire [31:0] sampled_bus,input wire [1:0] edge1027')
    edit('nes_screen_status151',' reg [23:0] addr_meta,addr_sync;',
         ' (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [23:0] addr_meta,addr_sync;')
    edit('nes_screen_status151','reg [7:0] data_meta,data_sync,data_previous;',
         '(* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [7:0] data_meta,data_sync;\n reg [7:0] data_previous;\n assign sampled_bus={addr_sync,data_sync};')
    edit('fxpak_nes_screen137_top',' wire [1:0] edge1027;', ' wire [31:0] sampled_bus;wire [1:0] edge1027;')
    for name,inst in [('fxpak_nes_screen137_top','screen_status'),('fxpak_nes_screen137_top','sink'),('nes_sink_bridge165','bus')]:
        edit(name,inst+'(.',inst+'(.sampled_bus(sampled_bus),.')
    for name in ('nes_sink_bridge165','nes_sink_bus165'):
        edit(name,f'module {name}(',f'module {name}(input wire [31:0] sampled_bus,')
    prefix=' (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg '
    edit('nes_sink_bus165',prefix+'[23:0] address_meta,address_sync;',
         " reg [1:0] sample_valid;\n wire [23:0] address_sync=sample_valid[1]?sampled_bus[31:8]:24'd0;")
    edit('nes_sink_bus165',prefix+'[7:0] data_meta,data_sync;',
         " wire [7:0] data_sync=sample_valid[1]?sampled_bus[7:0]:8'd0;")
    edit('nes_sink_bus165','address_meta<=0;address_sync<=0;address_previous<=0;data_meta<=0;data_sync<=0;',
         'sample_valid<=0;address_previous<=0;')
    edit('nes_sink_bus165','address_meta<=address;address_sync<=address_meta;',
         "sample_valid<={sample_valid[0],1'b1};")
    edit('nes_sink_bus165','data_meta<=data_in;data_sync<=data_meta;','')
    # The ROM tag already stores the same preceding address. Explicitly
    # cover asynchronous reset and its two filling clocks before reuse.
    edit('nes_sink_bus165','reg [23:0] address_previous;', "wire [23:0] address_previous=sample_valid[1]?tag:24'd0;")
    edit('nes_sink_bus165','sample_valid<=0;address_previous<=0;', 'sample_valid<=0;')
    edit('nes_sink_bus165',"sample_valid<={sample_valid[0],1'b1};address_previous<=address_sync;",
         "sample_valid<={sample_valid[0],1'b1};")
    edit('nes_display1010','(input wire clk','(input wire [3:0] edge1027,input wire head_snapshot,input wire clk')
    fragment=Path(__file__).with_name('nes_kirby1027_events.svh').read_text()
    edit('nes_display1010',' reg [15:0] q;', ' reg [15:0] q;\n'+fragment)
    # Alternate the two show slots in the existing timestamp RAM. The prior
    # show no longer needs a 16-bit copy in FFs and a full-width write mux.
    edit('nes_display1010','reg [15:0] previous_show;', 'reg show_bank;')
    edit('nes_display1010','show_event?3:dma_event?', 'show_event?(show_bank?3:0):dma_event?')
    edit('nes_display1010','if(|events) stamps[write_slot]<=begin_frame?previous_show:now;',
         'if(|events[4:1]) stamps[write_slot]<=now;')
    edit('nes_display1010','q<=stamps[index[3:1]];',
         'q<=stamps[index[3:1]==0?(show_bank?3:0):index[3:1]==3?(show_bank?0:3):index[3:1]];')
    edit('nes_display1010','clock_count<=0;live<=0;', 'show_bank<=0;clock_count<=0;live<=0;')
    edit('nes_display1010','previous_show<=now;', 'show_bank<=!show_bank;')
    # Reuse a single synchronous read port for the three low timestamp bytes.
    edit('nes_display1010','reg [9:0] origin,published,anchor;', 'reg [9:8] origin,published,anchor;')
    edit('nes_display1010','origin<=now[9:0]', 'origin<=now[9:8]')
    edit('nes_display1010','published<=now[9:0]', 'published<=now[9:8]')
    edit('nes_display1010','anchor<=now[9:0]', 'anchor<=now[9:8]')
    edit('nes_display1010','6:reply<=origin[7:0]', '6:reply<=anchor_q')
    edit('nes_display1010',"7:reply<={6'b0,origin[9:8]}","7:reply<=anchor_q")
    edit('nes_display1010',"8:reply<=anchor[7:0];9:reply<={6'b0,anchor[9:8]}",
         "8:reply<=anchor_q;9:reply<={seen_grant,seen_request,published[9:8],anchor[9:8],origin[9:8]}")
    edit('nes_display1010',"10:reply<=published[7:0];11:reply<={6'b0,published[9:8]}",
         "10,26,27,28:reply<=step_q;11,29:reply<=grant_q")
    edit('nes_display1010','read_ok<=complete && !bad;',
         'read_ok<=complete && !bad && (chunks==0 || (saw_group && saw_done && saw_end && returned_snapshot && !port_conflict));')
    # Drive the footer low on later events just like the existing done strobe.
    edit('nes_display1010','(first_e9 || returned || writer!=writer_previous || header ||\n',
         '(|event_rise || head_snapshot || first_e9 || returned || writer!=writer_previous || header ||\n')
    edit('nes_display1010','if(first_e9 || returned || writer!=writer_previous || header || retired',
         'if(|event_rise || head_snapshot || first_e9 || returned || writer!=writer_previous || header || retired')
    constraints=out/'board.sdc'
    with constraints.open('a') as f:
        for i in range(4):
            src = ('nes_source_tile192:source|evt905' if i<2 else 'nes_tile_bulk206:bulk|edge1027')+f'[{i%2}]'
            a='nes_live_joint:core|nes_direct206:direct_path|'+src
            b=f'nes_screen_status151:screen_status|nes_display1010:trace|event_meta[{i}]'
            f.write(f'\nset src1027 [cdc181_exact {{{a}}}]\nset dst1027 [cdc181_exact {{{b}}}]\n')
            f.write('set_max_delay 11.904 -from $src1027 -to $dst1027\nset_false_path -hold -from $src1027 -to $dst1027\n')


def arm(base, out):
    from prepare_nes_trial802 import rename_edition
    shutil.copytree(base, out)
    edition=out.parent/'edition'
    rename_edition(base/'src', edition, 1025, 1027)
    for path in edition.iterdir():
        shutil.copy2(path,out/'src'/path.name)
    replace(out/'src/nes_budget210.c','edition=1025;','edition=1027;')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('target', choices=('board','arm'))
    ap.add_argument('base',type=Path)
    ap.add_argument('out',type=Path)
    args=ap.parse_args()
    (board if args.target=='board' else arm)(args.base,args.out)
