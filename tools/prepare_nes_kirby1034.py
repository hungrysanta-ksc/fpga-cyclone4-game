"""Build a passive four-transaction observer on the routed MMC1032 board sources."""
import argparse
import shutil
from pathlib import Path

from prepare_nes_kirby1027 import replace

PROBES = Path(__file__).resolve().parents[2] / 'probes'


def prepare(dest):
    original = PROBES / 'nes-kirby1032/board-bus'
    shutil.copytree(original, dest)

    def edit(name, old, new):
        replace(dest / (name + '.sv'), old, new)

    # ps is the registered plan_seal after the complete SPI transaction.
    # plan_taken below is the consumer in the NES domain, a separate event.
    edit('nes_tile_bulk206', 'module nes_tile_bulk206(', 'module nes_tile_bulk206(output reg group1034,')
    edit('nes_tile_bulk206', ' wire input_ok=', '''
 always @(posedge nes_clk) group1034<=!sc && plan_taken && (announced || slength==0);
 wire input_ok=''')
    for name in ('nes_direct206', 'nes_live_joint'):
        edit(name, f'module {name}(', f'module {name}(output wire accepted1034,group1034,')
    edit('nes_direct206', ' assign ret905=', ' assign accepted1034=ps;\n assign ret905=')
    edit('nes_direct206', 'bulk(.', 'bulk(.group1034(group1034),.')
    conduit = '.group1034(group1034),.accepted1034(accepted1034),'
    for name, instance in [('nes_live_joint','direct_path'),('fxpak_nes_screen137_top','core'),
                           ('fxpak_nes_screen137_top','screen_status'),('nes_screen_status151','trace')]:
        edit(name, instance+'(.', instance+'('+conduit+'.')
    edit('fxpak_nes_screen137_top',' wire [2:0] evt905',' wire accepted1034,group1034; wire [2:0] evt905')
    for name in ('nes_display1010','nes_screen_status151'):
        edit(name, f'module {name}(', f'module {name}(input wire accepted1034,group1034,')
    name = 'nes_display1010'
    edit(name, ' always @(posedge clk) begin\n  if(|events)', '''
 // Independent write ports allow accept and return on the same edge.
 (* ramstyle="M9K" *) reg [7:0] accepts1034[0:3],returns1034[0:3];
 reg [7:0] aq1034,rq1034,last_group1034;
 reg [2:0] n1034;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] gs1034;
 reg gp1034,group_seen1034;
 wire start1034=gs1034[1] && !gp1034;
 always @(posedge clk) begin
  gs1034<={gs1034[0],group1034}; gp1034<=gs1034[1];
  aq1034<=accepts1034[index[1:0]]; rq1034<=returns1034[index[1:0]];
  if(clear_record || first_e9)begin n1034<=0;group_seen1034<=0;end
  else begin
   if(accepted1034 && n1034<5)begin
    if(n1034<4)accepts1034[n1034[1:0]]<=now[7:0];
    n1034<=n1034+1'b1;
   end
   if(returned && chunks<4)returns1034[chunks[1:0]]<=now[7:0];
   if(start1034)begin last_group1034<=now[7:0];group_seen1034<=1;end
  end
 end
 always @(posedge clk) begin
  if(|events)''')
    edit(name, 'if(first_e9 || returned || writer!=writer_previous || header || retired ||',
         'if(accepted1034 || start1034 || first_e9 || returned || writer!=writer_previous || header || retired ||')
    edit(name, 'if(complete && (first_e9 ||', 'if(complete && (accepted1034 || start1034 || first_e9 ||')
    # 8..11 and 24..27 deliberately aligned for the synchronous RAM read address.
    # Move ACK to 28..29, read old slot 4 there. DMA occurrence stays in flags.
    edit(name, 'q<=stamps[index[3:1]];', "q<=stamps[index>=28 ? 3'd4 : index[3:1]];")
    edit(name, "6:reply<=origin[7:0];7:reply<={6'b0,origin[9:8]};",'''6:reply<=origin[7:0];7:reply<=anchor[7:0];
  8,9,10,11:reply<=aq1034;
  24,25,26,27:reply<=rq1034;
  28:reply<=q[7:0];29:reply<=q[15:8];''')
    edit(name, "  8:reply<=anchor[7:0];9:reply<={6'b0,anchor[9:8]};\n  10:reply<=published[7:0];11:reply<={6'b0,published[9:8]};", '')
    edit(name, '16,18,20,22,24:', '16,18,22:')
    edit(name, '17,19,21,23,25:', '17,19,23:')
    edit(name, '  30:reply', '''  20:reply<=last_group1034;
  21:reply<={group_seen1034,n1034,anchor[9:8],origin[9:8]};
  30:reply''')
    edit(name, "1:reply<=8'ha1;", "1:reply<=8'ha4;")
    edit(name, 'reg [15:0] previous_show;', 'reg show_bank;')
    edit(name, 'show_event?3:dma_event?', 'show_event?(show_bank?3:0):dma_event?')
    edit(name, 'if(|events) stamps[write_slot]<=begin_frame?previous_show:now;',
         'if(ack_event || show_event || seal_event) stamps[write_slot]<=now;')
    edit(name, "index>=28 ? 3'd4 : index[3:1]", "index>=28 ? 4 : index[3:1]==0 ? (show_bank?3:0) : index[3:1]==3 ? (show_bank?0:3) : 1")
    edit(name, 'clock_count<=0;live<=0;', 'show_bank<=0;clock_count<=0;live<=0;')
    edit(name, 'previous_show<=now;', 'show_bank<=!show_bank;')
    with (dest/'board.sdc').open('a') as sdc:
        sdc.write('\nset s1034 [cdc181_exact {nes_live_joint:core|nes_direct206:direct_path|nes_tile_bulk206:bulk|group1034}]\n'
                  'set d1034 [cdc181_exact {nes_screen_status151:screen_status|nes_display1010:trace|gs1034[0]}]\n'
                  'set_max_delay 11.904 -from $s1034 -to $d1034\nset_false_path -hold -from $s1034 -to $d1034\n')


def arm(dest):
    from prepare_nes_trial802 import rename_edition
    source = PROBES / 'nes-kirby1032/link'
    shutil.copytree(source, dest)
    names = dest.parent / 'edition'
    rename_edition(source/'src', names, 1032, 1034)
    for file in names.iterdir():
        shutil.copy2(file, dest/'src'/file.name)
    budget = dest / 'src/nes_budget210.c'
    replace(budget, 'edition=1032;', 'edition=1034;')
    replace(budget, 'h[1]==0xa1', 'h[1]==0xa4')
    input_timestamps(dest)
    sampling(dest)


def sampling(dest):
    budget=dest/'src/nes_budget210.c'
    replace(budget,'if(used && log->rows[used-1].tick/40==tick/40)return;', '''if(mode900==0){
  if(tick<5500)return;
  unsigned width=tick<5750?10:5;
  if(used && log->rows[used-1].tick/width==tick/width)return;
 }else if(used && log->rows[used-1].tick/40==tick/40)return;''')


def input_timestamps(dest):
    # Reuse the old aggregate D1 field for the last checked D2 response.
    # The last D0 still has to confirm token advancement before publishing.
    rx = dest/'src/nes_native165.c'
    replace(rx, 'uint32_t t[4];', 'uint32_t t[5];')
    replace(rx, 'if(begin)begin|=', 't[4]=nes_cost471_now();\n if(begin)begin|=')
    budget = dest/'src/nes_budget210.c'
    replace(budget, 'a->d1+=t[1]-t[0];', 'a->d1=t[4];')
    replace(budget, 'a->restore+=t[2]-t[1];', 'if(begin)a->restore=t[1]-t[0];')
    replace(budget, '(struct mark900){nes_cost471_now(),g,1}', '(struct mark900){log900p->ingress[82].end,g,1}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dest', type=Path)
    parser.add_argument('--arm', action='store_true')
    args = parser.parse_args()
    (arm if args.arm else prepare)(args.dest)
