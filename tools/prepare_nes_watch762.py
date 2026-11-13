# SPDX-License-Identifier: MIT
"""Build a diagnostic 753 receiver and the matching 707D board project."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from build_nes_trace_replay import Code
from build_nes_static751 import codec, pack
from nes_raw506 import once, sha

ROOT = Path(__file__).resolve().parents[1]


def receiver(client, raw, out):
    body = bytearray((client/'body.bin').read_bytes())
    assert sha(client/'body.bin')=='74818b9f1ff02db6be843f4355f74ad57d42d99ea6f4cefbbbe9ba643e16b693'
    labels = json.loads((client/'labels.json').read_text())
    entry = 0x7e2000 + len(body)
    c = Code(entry)
    c.labels.update(labels)
    # Original caller is A8, X/Y16. Leave all non-map jobs on the normal path.
    c.emit(0xc0,0,6)                         # CPY #1536
    c.branch(0xd0,'normal')
    c.emit(0xc2,0x20)
    c.absolute(0xad,0x4302)
    c.emit(0x29,0,0x70,0xc9,0,0x50)
    c.branch(0xd0,'normal16')
    c.emit(0x48)                              # original map kind for retirement
    c.absolute(0xad,0x4302)
    c.absolute(0x8d,0x6006)                   # low then high arm the source cursor
    c.emit(0xe2,0x20,0xa9,1)
    c.absolute(0x8d,0x420b)
    c.absolute(0xad,0x6006)                   # DONE only after last comparison
    c.branch(0x30,'verified')
    c.emit(0xc2,0x20,0x68)                    # discard kind, keep return stack
    c.emit(0xa9,1,0)
    c.absolute(0x8d,0x1236)
    c.absolute(0x20,labels['invalidate635']&65535)
    c.jump('stop523')
    c.label('verified')
    c.absolute(0x4c,0x2f29)
    c.label('normal')
    c.emit(0xc2,0x20)
    c.label('normal16')
    c.absolute(0x4c,0x36a2)
    offset = 0x2f24 - codec.DEST
    assert body[offset:offset+3] == bytes.fromhex('4ca036')
    body[offset:offset+3] = bytes([0x4c,entry&255,(entry>>8)&255])
    body.extend(c.finish())
    with patch.object(codec,'pack',pack):
        codec.build(raw,out,edit_body=lambda *_:bytes(body),allow_extension=True,prefix_sizes=[512],
                    medium_pages=True,boot_bytes=320,fast_backrefs=True)
    shutil.copyfile(client/'labels.json',out/'labels.json')


def edit(p, *pairs):
    s=p.read_text()
    for old,new in pairs:
        s=once(s,old,new)
    p.write_text(s,encoding='utf8',newline='\n')


def board(base, client, out):
    manifest=json.loads((base/'inputs707.json').read_text())
    out.mkdir(parents=True,exist_ok=False)
    for name,digest in (manifest['base']|manifest['changed']).items():
        assert sha(base/name)==digest,name
        dst=out/name
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(base/name,dst)
    shutil.copyfile(client/'sink-program.hex',out/'sink-program.hex')
    shutil.copyfile(ROOT/'tests/nes-functional/nes_map_watch762.sv',out/'nes_map_watch762.sv')
    pins=(ROOT/'src/fpga/pin.qsf').read_text().splitlines()
    loc=[s for s in pins if ('SNES_PA_IN[' in s or 'SNES_PAWR_IN' in s)
         and ('set_location_assignment' in s or 'IO_STANDARD' in s)]
    assert len(loc)==18
    with (out/'board.qsf').open('a') as stream:
        stream.write('\n'+'\n'.join(loc)+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_map_watch762.sv\n')
    edit(out/'fxpak_nes_screen137_top.sv',
         ('input wire CLKIN,SNES_SYSCLK,','input wire CLKIN,SNES_SYSCLK,SNES_PAWR_IN,input wire [7:0] SNES_PA_IN,'),
         ('wire sink_miso,sink_selected','wire receive762; wire sink_miso,sink_selected'),
         ('nes_sink_bridge165 sink(','nes_sink_bridge165 sink(.periph_addr(SNES_PA_IN),.pawr_n(SNES_PAWR_IN),.receive762(receive762),'),
         ('consumer_oe&&!status_receive','consumer_oe&&!status_receive&&!receive762'))
    edit(out/'nes_sink_bridge165.sv',
         ('input wire clk,raw_reset','input wire [7:0] periph_addr,input wire pawr_n,output wire receive762,\n input wire clk,raw_reset'),
         (' wire ready,aw,ap,mp;', ''' wire pass762,bad762,seal_block,listen762,armlo,armhi,consume762;
 wire ref_begin,ref_bank,ref_literal,ref_invalidate,ref_flush,ref_busy;wire [11:0] ref_addr;wire [7:0] ref_data;
 wire [7:0] arm_data; wire beat762,read762;wire [23:0] src762;wire [7:0] port762,byte762;
 wire ready,aw,ap,mp;'''),
         (' wire bus_oe,bus_dir;', ''' // Receive only. Cartridge-driven cycles retain exclusive output ownership.
 assign receive762=!raw_cancel&&!stop&&!fault&&listen762&&!pawr_n&&!read_n&&write_n&&address[23:16]==8'h7f;
 nes_map_watch762 watch(.clk(clk),.reset(session_reset),.stop(stop||fault),
  .begin_frame(ref_begin),.target_bank(ref_bank),.literal(ref_literal),.invalidate(ref_invalidate),.flush(ref_flush),.reference_busy(ref_busy),
  .reference_address(ref_addr),.reference_byte(ref_data),.consume(consume762),.arm_low(armlo),.arm_high(armhi),.command_byte(arm_data),
  .beat(beat762),.source_address(src762),.source_read(read762),.peripheral(port762),.wire_byte(byte762),
  .listening(listen762),.passed(pass762),.failed(bad762),.seal_block(seal_block));
 wire bus_oe,bus_dir;'''),
         ('nes_sink_bus165 bus(','''nes_sink_bus165 bus(.pa(periph_addr),.pawr_n(pawr_n),.bad762(bad762),.pass762(pass762),
  .consume762(consume762),.armlo(armlo),.armhi(armhi),.arm_data(arm_data),.beat762(beat762),.port762(port762),.byte762(byte762),
  .read762(read762),.src762(src762),'''),
         ('nes_sink_spi165 endpoint(','''nes_sink_spi165 endpoint(.ref_begin(ref_begin),.ref_bank(ref_bank),.ref_literal(ref_literal),
  .ref_invalidate(ref_invalidate),.ref_flush(ref_flush),.ref_busy(ref_busy),.ref_addr(ref_addr),.ref_data(ref_data),.bad762(bad762),.seal_block(seal_block),'''))
    # Reference bytes come from the same CRC-checked SPI transaction as the
    # queue entry. A failed SPI CRC poisons the session before use. A fresh
    # BEGIN is not allowed by the ARM until previous final ACK+EA.
    edit(out/'nes_sink_spi165.sv',
         ('input wire clk,reset,enable','''output wire ref_begin,ref_bank,ref_literal,ref_invalidate,ref_flush,ref_busy, input wire bad762,seal_block,
 output wire [11:0] ref_addr,output wire [7:0] ref_data,
 input wire clk,reset,enable'''),
         (" wire [8:0] expected_length={1'b0,payload_size}+9'd16;",''),
         (' wire ours=', ''' wire [8:0] expected_length={1'b0,payload_size}+9'd16;
 reg ref_begin_op,ref_copy_op,ref_fill_op,ref_section,ref_aligned,ref_fullrow;
 reg [11:0] ref_cursor;
 // Hold eligibility through the SS rising-edge decision. A bad CRC latches
 // endpoint fault on the same edge on which this transaction releases the port.
 assign ref_busy=command==8'he1&&can_write&&byte_count>=3&&ref_section&&(!ss[1]||!prev_ss);
 wire ref_tick=!ss[1]&&sck[1]&&!prev_sck&&bit_count==7&&command==8'he1&&can_write;
 assign ref_begin=ref_tick&&ref_begin_op&&byte_count==19;
 assign ref_bank=incoming[0];
 assign ref_literal=ref_tick&&ref_copy_op&&ref_section&&ref_aligned&&byte_count>=17&&byte_count<=expected_length;
 assign ref_invalidate=ref_tick&&ref_fill_op&&ref_section&&byte_count==17;
 assign ref_flush=ref_tick&&ref_section&&byte_count==17&&
  ((ref_copy_op&&!ref_aligned)||(ref_fill_op&&!ref_fullrow)||(!ref_copy_op&&!ref_fill_op&&!ref_begin_op));
 assign ref_addr=ref_cursor;assign ref_data=incoming;
 always @(posedge clk)if(ref_tick)begin
  case(byte_count)
   1:begin ref_begin_op<=incoming==1;ref_copy_op<=incoming==2;ref_fill_op<=incoming==4;end
   2:ref_section<=incoming==2;
   11:begin ref_cursor[7:0]<=incoming;ref_aligned<=incoming[5:0]==0;end
   12:begin ref_cursor[11:8]<=incoming[3:0];ref_aligned<=ref_aligned&&incoming[7:4]==0;end
   13:ref_aligned<=ref_aligned&&incoming[5:0]==0&&incoming!=0;
   15:ref_fullrow<=ref_cursor[5:0]==0&&incoming==64;
   16:ref_fullrow<=ref_fullrow&&incoming==0;
   default:if(ref_literal)ref_cursor<=ref_cursor+1'b1;
  endcase
 end
 wire ours='''),
         ('if(map_progress&&!stop','if(bad762)fault<=1;\n   if(map_progress&&!stop'),
         ('if(!packet_ready||ack_mask', "if((ack_work[15:0]==16'h0301&&(seal_block||stop||bad762))||!packet_ready||ack_mask"),
         ('if(checking&&enable&&!fault)','if(checking&&enable&&!fault&&!bad762&&!stop)'))
    edit(out/'nes_sink_bus165.sv',
         ('input wire clk,reset,active,stop,fault,','''input wire clk,reset,active,stop,fault,pass762,bad762,pawr_n,input wire [7:0] pa,
 output wire armlo,armhi,consume762,beat762,read762,output wire [7:0] arm_data,byte762,port762,output wire [23:0] src762,'''),
         ("address[4:0]<=5'd5","address[4:0]<=5'd7"),
         ("16'h6001:control_data={(stop||fault)","16'h6006:control_data={pass762&&!stop&&!fault,7'd0};\n  16'h6001:control_data={(stop||fault||bad762)"),
         (' wire local_bank=', ''' (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] pawr_pipe;
 reg pawr_last;reg [7:0] pa_meta,pa_sync,pa_last;
 always @(posedge clk)begin
  pawr_pipe<={pawr_pipe[0],pawr_n};pawr_last<=pawr_pipe[1];
  pa_meta<=pa;pa_sync<=pa_meta;pa_last<=pa_sync;
 end
 // At the synchronized trailing edge use the last sample taken while /PAWR was low.
 assign beat762=pawr_pipe[1]&&!pawr_last;
 assign src762=address_previous;assign read762=!read_previous&&write_previous;
 assign byte762=data_previous;assign port762=pa_last;
 wire arm_write=active&&!reset&&!stop&&!fault&&write_sync&&!write_previous&&read_previous;
 assign consume762=read_sync&&!read_previous&&write_previous&&address_previous==24'h006006;
 assign arm_data=data_previous;
 assign armlo=arm_write&&address_previous==24'h006006;
 assign armhi=arm_write&&address_previous==24'h006007;
 wire local_bank='''))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('board','client','raw','out'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    receiver(a.client,a.raw,a.out/'client')
    board(a.board,a.out/'client',a.out/'board')
