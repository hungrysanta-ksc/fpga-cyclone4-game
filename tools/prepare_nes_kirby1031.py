"""Build a passive ready-to-first-D1 observer on the MMC1030 board source."""
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT.parent / 'probes'
WORK = PROBES / 'nes-kirby1031'


def prepare(edition=1031):
    assert edition in (1031,1032)
    board = PROBES / ('nes-kirby1028/board-perf' if edition==1031 else 'nes-kirby1023/board')
    dst = PROBES / f'nes-kirby{edition}/board'
    endpoint = 'nes_native_spi165.sv'
    original = (board / endpoint).read_bytes()
    assert original == (PROBES / 'nes-kirby1023/board' / endpoint).read_bytes()
    data = original.decode()
    anchor = ' reg [7:0] status_crc;'
    field = "4:reply={7'd0,status_size[8]};"
    assert data.count(anchor) == data.count(field) == 1
    data = data.replace(anchor, '''
 // The D2 reply is sampled before retirement. Only report the age of a
 // fully read BEGIN block. D0 remains the authoritative nine-bit size.
 reg [21:0] first_wait;
 reg first_read;
 wire start_read=!ss[1] && sck[1] && !prev_sck && bit_count==7 &&
                 cursor==511 && incoming==8'hd1;
 always @(posedge clk) begin
  if(reset || !available || !has_header)begin
   first_wait<=0;
   first_read<=0;
  end else if(!first_read)begin
   if(start_read)first_read<=1;
   else if(!(&first_wait[21:15]))first_wait<=first_wait+1'b1;
  end
 end
 wire [6:0] ready_age=(command==8'hd2 && reading && has_header && read_seen)
                          ? first_wait[21:15] : 7'd0;
''' + anchor).replace(field, '4:reply={ready_age,status_size[8]};')
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        assert (dst / endpoint).read_bytes() == data.encode(), 'existing candidate differs'
    else:
        shutil.copytree(board, dst)
        (dst / endpoint).write_bytes(data.encode())
    return hashlib.sha256(data.encode()).hexdigest()


def shared_control():
    """Control board was one LAB over. Borrow the existing host telemetry clock."""
    work=PROBES/'nes-kirby1032'
    old=work/'board'
    dst=work/'board-shared'
    shutil.copytree(old,dst)
    def replace(name,old,new):
        p=dst/(name+'.sv')
        data=p.read_bytes()
        assert data.count(old.encode())==1, (name,old)
        p.write_bytes(data.replace(old.encode(),new.encode()))
    replace('nes_display1010','output reg [7:0] reply','output wire offer_phase,output reg [7:0] reply')
    replace('nes_display1010',' wire [15:0] now=', ' assign offer_phase=clock_count[14];\n wire [15:0] now=')
    replace('nes_screen_status151','output wire receive_write','output wire offer_phase,output wire receive_write')
    replace('nes_screen_status151','nes_display1010 trace(','nes_display1010 trace(.offer_phase(offer_phase),')
    replace('fxpak_nes_screen137_top','nes_live_joint core(','wire offer_phase;\n nes_live_joint core(.offer_phase(offer_phase),')
    replace('fxpak_nes_screen137_top','nes_screen_status151 screen_status(','nes_screen_status151 screen_status(.offer_phase(offer_phase),')
    replace('nes_live_joint','module nes_live_joint(','module nes_live_joint(input wire offer_phase,')
    replace('nes_live_joint','nes_native_spi165 native_spi(','nes_native_spi165 native_spi(.offer_phase(offer_phase),')
    replace('nes_native_spi165','input wire clk,reset,','input wire offer_phase,input wire clk,reset,')
    replace('nes_native_spi165','reg [21:0] first_wait;', '''reg [6:0] first_wait;
 reg prev_phase;
 always @(posedge clk)prev_phase<=offer_phase;''')
    replace('nes_native_spi165',"else if(!(&first_wait[21:15]))", "else if(offer_phase && !prev_phase && !(&first_wait))")
    replace('nes_native_spi165','? first_wait[21:15]', '? first_wait')


def bus_control():
    """Reuse MMC1027's verified bus sampling and frozen SPI73 boot reply."""
    from prepare_nes_kirby1027 import replace
    work=PROBES/'nes-kirby1032'
    dst=work/'board-bus'
    ref=PROBES/'nes-kirby1027/board-tag'
    shutil.copytree(work/'board',dst)
    for name in ('nes_sink_bridge165','nes_sink_bus165','nes_screen_status151'):
        shutil.copy2(ref/(name+'.sv'),dst/(name+'.sv'))
    status=dst/'nes_screen_status151.sv'
    replace(status,'input wire [1:0] edge1027,','')
    replace(status,'.edge1027({edge1027,evt905[1:0]}),.head_snapshot(snap903&&ready903),','')
    top=dst/'fxpak_nes_screen137_top.sv'
    replace(top,' wire [2:0] evt905',' wire [31:0] sampled_bus;\n wire [2:0] evt905')
    for inst in ('screen_status','sink'):
        replace(top,inst+'(.',inst+'(.sampled_bus(sampled_bus),.')


if __name__ == '__main__':
    import sys
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['board','arm','shared','bus'],default='board',nargs='?')
    parser.add_argument('--edition',type=int,choices=[1031,1032],default=1031)
    args=parser.parse_args()
    edition=args.edition
    if args.mode=='bus':
        assert edition==1032
        bus_control()
    elif args.mode=='shared':
        assert edition==1032
        shared_control()
    elif args.mode=='arm':
        from prepare_nes_kirby1029 import change
        from prepare_nes_trial802 import rename_edition
        parent = PROBES / 'nes-kirby1030/link'
        work=PROBES / f'nes-kirby{edition}'
        target = work / 'link'
        shutil.copytree(parent, target)
        rename_edition(parent/'src', work/'edition', 1030, edition)
        src = target/'src'
        for file in (work/'edition').iterdir():
            shutil.copy2(file, src/file.name)
        budget = src/'nes_budget210.c'
        change(budget, 'edition=1030;', f'edition={edition};')
        # A marked BEGIN carries the quantized age; entries reach the log
        # only after CRC, sequence, final D2 and the following D0 all pass.
        change(src/'nes_native165.c', '/* D2 replies before retirement.',
               'if(begin)begin|=(unsigned)(rx[5]&0xfe);\n /* D2 replies before retirement.')
        change(budget, '.gen=gen,.first=t[0]', '.gen=gen,.first=t[0],.bytes=(begin>>1)<<24')
    else:
        print(prepare(edition))
