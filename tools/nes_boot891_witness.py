"""Replace only the stage-zero witness; keep the SPI73 wire format and bus ownership."""
import argparse
from pathlib import Path
import shutil

from nes_raw506 import once
from package_nes_trial872 import QUARTUS, ROOT, fit, read, sha


def witness(source):
    start=source.index(' reg [1:0] boot_e0;')
    end=source.index(' wire [7:0] status_error=',start)
    source=source[:start]+''' // Reset at FPGA configuration. Only count observations after the first E0.
 reg boot_armed;
 reg [6:0] boot_order;
 wire observed_read=boot_armed && !read_n && write_n && !romsel_n &&
                    addr_sync==address && addr_previous==address;
 wire vector_address=address[23:1]==23'h007ffe;
 wire vector_match=data_in==(address[0]?8'h80:8'h00);
'''+source[end:]
    source=once(source,'boot_e0<=0;boot_order<=0;','boot_armed<=0;boot_order<=0;')
    start=source.index('    if(!boot_order[0]')
    end=source.index('   end\n',start)
    source=source[:start]+'''    if(observed_read && vector_address)begin
     if(!address[0])boot_order[0]<=1;else boot_order[1]<=1;
     if(bus_drive && vector_match)begin
      if(!address[0])boot_order[2]<=1;else boot_order[3]<=1;
     end
     if(bus_drive && !vector_match)boot_order[4]<=1;
    end
    if(observed_read && bus_drive && address==24'h008000 && data_in==8'h78)
     boot_order[5]<=1;
    if(boot_armed && qualified && addr_previous==24'h007000)boot_order[6]<=1;
'''+source[end:]
    return once(source,"if(stage==0 && incoming==8'he0 && boot_e0<2)boot_e0<=boot_e0+1'b1;",
                "if(stage==0 && incoming==8'he0)boot_armed<=1;")


def serial_snapshot(source):
    """Shift the immutable SPI73 snapshot MSB first at the existing falling edge."""
    start=source.index(' always @* begin\n  case(byte_count)')
    end=source.index(' always @(posedge clk',start)
    source=source[:start]+source[end:]
    source=once(source,'reg miso_hold;reg [7:0] reply;','reg miso_hold;')
    return once(source,'if(!sck_sync[1]&&sck_previous)miso_hold<=reply[7-bit_count];',
                """if(!sck_sync[1]&&sck_previous && byte_count!=0)begin
     miso_hold<=snapshot[55];snapshot<={snapshot[54:0],1'b0};
    end""")


def sampled_status(source):
    """Compare data/drive/address sampled on the same host edge and settled at stage 2."""
    source=once(source,"wire vector_match=data_in==","wire vector_match=data_sync==")
    source=once(source,"if(bus_drive && vector_match)","if(drive_sync[1] && vector_match)")
    source=once(source,"if(bus_drive && !vector_match)","if(drive_sync[1] && !vector_match)")
    return once(source,"if(observed_read && bus_drive && address==24'h008000 && data_in==8'h78)",
                "if(observed_read && drive_sync[1] && addr_sync==24'h008000 && data_sync==8'h78)")


def compact_address_history(source):
    """Keep the previous equality and the only two decoded write addresses."""
    source=once(source,'reg [23:0] addr_meta,addr_sync,addr_previous;',
                'reg [23:0] addr_meta,addr_sync;\n reg addr_stable,was_stage,was_error;')
    source=once(source,'addr_previous<=0;','addr_stable<=1;was_stage<=0;was_error<=0;')
    source=once(source,'addr_previous<=addr_sync;',"""addr_stable<=addr_meta==addr_sync;
   was_stage<=addr_sync==24'h007000;was_error<=addr_sync==24'h007001;""")
    assert source.count('addr_previous==address')==2
    assert source.count("addr_previous==24'h007000")==2
    source=source.replace('addr_previous==address','addr_stable').replace("addr_previous==24'h007000",'was_stage')
    source=once(source,"addr_previous==24'h007001",'was_error')
    assert 'addr_previous' not in source
    return source


def synchronized_reads(source):
    source=once(source,' reg boot_armed;',""" reg boot_armed;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] select_sync;""")
    source=once(source,'boot_armed<=0;boot_order<=0;',"boot_armed<=0;boot_order<=0;select_sync<=2'b11;")
    source=once(source,'wr_sync<={wr_sync[0],write_n};','select_sync<={select_sync[0],romsel_n};wr_sync<={wr_sync[0],write_n};')
    start=source.index(' wire observed_read=')
    end=source.index(' wire [7:0] status_error=',start)
    source=source[:start]+""" wire observed_read=boot_armed && !rd_sync[1] && wr_sync[1] && !select_sync[1] && addr_stable;
 wire vector_address=addr_sync[23:1]==23'h007ffe;
 wire vector_match=data_sync==(addr_sync[0]?8'h80:8'h00);
"""+source[end:]
    assert source.count('if(!address[0])')==2
    return source.replace('if(!address[0])','if(!addr_sync[0])')


def prepare_board(temp,variant):
    base=temp/'nes-trial816-board890'
    dest=temp/f'nes-trial816-board{variant}'
    assert sha(base/'output_files/board.sof')==read(ROOT/'analysis/trial890-package.json')['board']['image']['SOF']
    dest.mkdir()
    for n in ('rtl','sys'):
        shutil.copytree(base/n,dest/n)
    for f in base.iterdir():
        if f.suffix in ('.sv','.v','.vhd','.qpf','.qsf','.sdc','.tcl','.hex'):
            if f.name=='nes_screen_status151.sv':
                status=witness(f.read_text())
                if variant in ('891B','891C','891D','891E'):
                    status=serial_snapshot(status)
                if variant in ('891C','891D','891E'):
                    status=sampled_status(status)
                if variant in ('891D','891E'):
                    status=compact_address_history(status)
                if variant=='891E':
                    status=synchronized_reads(status)
                (dest/f.name).write_text(status,newline='\n')
            else:
                shutil.copyfile(f,dest/f.name)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('--variant',choices=['891','891B','891C','891D','891E'],default='891')
    a=p.parse_args()
    prepare_board(a.temp,a.variant)
    fit(a.temp,a.variant,QUARTUS)
