"""Passive last-tile timestamps and the ARM's independently accepted descriptor."""
import argparse
import shutil
from pathlib import Path
from types import SimpleNamespace

from prepare_nes_frame900 import ROOT, PROBES, QUARTUS, fit, image, replace
from prepare_nes_trial802 import rename_edition

WORK=PROBES/'nes-tile903'
BASE=PROBES/'nes-frame900/link901'


def board(temp):
    src=temp/'nes-trial816-board901'
    dst=temp/'nes-trial816-board903'
    dst.mkdir()
    for sub in ('rtl','sys'):
        shutil.copytree(src/sub,dst/sub)
    for f in src.iterdir():
        if f.suffix in ('.sv','.v','.vhd','.qpf','.qsf','.sdc','.hex','.tcl'):
            shutil.copyfile(f,dst/f.name)
    shutil.copyfile(ROOT/'tests/nes-functional/nes_tile_trace903.sv',dst/'nes_tile_trace903.sv')
    replace(dst/'board.qsf','SYSTEMVERILOG_FILE nes_frame900.sv','SYSTEMVERILOG_FILE nes_tile_trace903.sv')
    taps=('writer903','reader903','ready903','snap903','kind903','token903')
    verilog='wire writer903,reader903,ready903,snap903,kind903'
    args=lambda keys: ''.join(f'.{k}({k}),' for k in keys)
    replace(dst/'nes_bulk_aperture188.sv',' input wire clk, reset',' output wire writer903,reader903,\n input wire clk, reset')
    for module,port in [('nes_tile_bulk206','output wire writer903,reader903,'),
                        ('nes_plan_spi200','output wire snap903,'),
                        ('nes_direct206','output '+verilog+',output wire [31:0] token903,'),
                        ('nes_live_joint','output '+verilog+',output wire [31:0] token903,')]:
        replace(dst/(module+'.sv'),f'module {module}(',f'module {module}('+port)
    replace(dst/'nes_bulk_aperture188.sv',' assign begin_ready=',' assign writer903=writer,reader903=reader;\n assign begin_ready=')
    replace(dst/'nes_tile_bulk206.sv',' aperture(',' aperture('+args(taps[:2]))
    replace(dst/'nes_plan_spi200.sv',' assign selected='," assign snap903=live&&!ss[1]&&sck[1]&&!prev_sck&&bits==7&&count==0&&incoming==8'he8;\n assign selected=")
    p=dst/'nes_direct206.sv'
    replace(p,' nes_plan_spi200 endpoint(',' assign ready903=chunk_ready,kind903=chunk_kind,token903=consume_token;\n nes_plan_spi200 endpoint('+args(['snap903']))
    replace(p,' nes_tile_bulk206 bulk(',' nes_tile_bulk206 bulk('+args(taps[:2]))
    replace(dst/'nes_live_joint.sv','nes_direct206 direct_path(','nes_direct206 direct_path('+args(taps))
    p=dst/'fxpak_nes_screen137_top.sv'
    replace(p,' nes_live_joint core(',' '+verilog+';wire [31:0] token903;\n nes_live_joint core('+args(taps))
    replace(p,' nes_screen_status151 screen_status(',' nes_screen_status151 screen_status('+args(taps))
    p=dst/'nes_screen_status151.sv'
    replace(p,'module nes_screen_status151(','module nes_screen_status151(input '+verilog+',input wire [31:0] token903,')
    s=p.read_text()
    a,b=s.index(' nes_frame900 trace('),s.index('  .show(wr_end')
    p.write_text(s[:a]+""" nes_tile_trace903 trace(.clk(clk),.reset(reset),.active(active_sync[1]),
  .writer(writer903),.reader(reader903),.ready(ready903),.kind(kind903),.checked_token(token903),.e8(snap903),
  .issue(!ss_sync[1] && sck_sync[1]&&!sck_previous && bit_count==7 && byte_count==1 && command==8'he1 && incoming==7),
  .header(tr_head),.data(tr_data),.retired(tr_retired),.op(tr_op),.generation(tr_gen),
"""+s[b:],newline='\n')


def arm():
    src=BASE/'src'
    dst=WORK/'patch'
    rename_edition(src,dst,901,903)
    for name in ('nes_budget210.c','nes_frame900.h'):
        shutil.copyfile(src/name,dst/name)
    h=dst/'nes_frame900.h'
    replace(h,'wire[26];','wire[26],descriptor[12];')
    replace(h,'==42','==54')
    replace(h,'rows[194]','rows[151]')
    p=dst/'nes_budget210.c'
    replace(p,'unsigned char mode900;', '#include "nes_native_runtime165.h"\nextern struct nes_native_runtime165 native_runtime165;\nunsigned char mode900;')
    replace(p,'if(!w ||','if((w==1 && mode900!=1) || !w ||')
    replace(p,'r->bank=ack900.valid>>1;', '''r->bank=ack900.valid>>1;
 if(native_runtime165.plan.bulk_valid)memcpy(r->descriptor,native_runtime165.plan.bulk,12);''')
    replace(p,'edition=901','edition=903')
    replace(p,'capacity=194','capacity=151')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['arm','board','fit','image'])
    p.add_argument('temp',type=Path)
    a=p.parse_args()
    if a.action=='arm':arm()
    elif a.action=='board':board(a.temp)
    elif a.action=='fit':fit(a.temp,903,QUARTUS)
    else:image(SimpleNamespace(board=a.temp/'nes-trial816-board903',out=a.temp/'nes-tile903-image',quartus=QUARTUS,number='903'))
