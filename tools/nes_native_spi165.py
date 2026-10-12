# SPDX-License-Identifier: MIT
"""Bind packed native transport to existing pins; not an installable image."""
import shutil
from nes_game147 import ROOT
from nes_native_host165 import prepare as host_prepare,FILES as HOST_FILES,PORTS

FILES=HOST_FILES+['nes_native_spi165.sv']
BINDING='''
wire native_spi_miso,native_spi_selected,native_spi_fault;
assign out_spi_selected=native_boot_selected||native_spi_selected;
assign out_spi_miso=native_boot_selected&&!native_spi_selected?native_boot_miso:
 native_spi_selected&&!native_boot_selected?native_spi_miso:1'b0;
nes_native_spi165 native_spi(.clk(host_clk),.reset(reset),
 .SPI_SS(ext_SPI_SS),.SPI_SCK(ext_SPI_SCK),.SPI_MOSI(ext_SPI_MOSI),
 .selected(native_spi_selected),.miso(native_spi_miso),.fault(native_spi_fault),
 .record_valid(native_host_valid),.record_ready(native_host_ready),.record_data(native_host_data),
 .ack_valid(native_host_ack_valid),.ack_ready(native_host_ack_ready),
 .ack_accept(native_host_ack_accept),.ack_generation(native_host_ack_generation));
'''

def bulk_engine():
    s=(ROOT/'src/nes/firmware/nes_game149_spi.inc').read_text()
    pairs=[('bool nes_game149_transfer(const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8])',
            'bool nes_native165_bulk(const struct nes_rom_spi_io *io,const uint8_t *tx,uint8_t *rx,unsigned count)'),
           ('if(!io||!tx||!rx||','if(!count||count>259||!io||!tx||!rx||'),
           ('for(unsigned i=0;i<8;i++)','for(unsigned i=0;i<count;i++)')]
    for a,b in pairs:
        assert s.count(a)==1;s=s.replace(a,b)
    return s

def prepare(evidence,out):
    inputs=host_prepare(evidence,out);p=out/'nes_live_joint.sv';s=p.read_text()
    assert s.count(PORTS)==1
    internal=PORTS.replace(',input wire',';input wire').replace(',output wire',';output wire').replace('input wire','wire').replace('output wire','wire').replace(',\n',';\n')
    s=s.replace(PORTS,'').replace('wire native_tx_valid,',internal+'\nwire native_tx_valid,',1)
    s=s.replace('wire guard_allow,','wire native_boot_miso,native_boot_selected;\nwire guard_allow,',1)
    a='.spi_miso(out_spi_miso),.spi_selected(out_spi_selected)'
    assert s.count(a)==1;s=s.replace(a,'.spi_miso(native_boot_miso),.spi_selected(native_boot_selected)')
    # Only this SPI binding gets a bounded serial-transfer policy budget.
    a='nes_native_export165 native_export('
    assert s.count(a)==1;s=s.replace(a,'nes_native_export165 #(.MAX_CYCLES(4194304)) native_export(')
    a='nes_native_fill165 #(.WAIT_CYCLES(65536))'
    assert s.count(a)==1;s=s.replace(a,'nes_native_fill165 #(.WAIT_CYCLES(131072),.MAX_CYCLES(2097152))')
    assert s.count('endmodule')==1;s=s.replace('endmodule',BINDING+'\nendmodule');p.write_text(s)
    shutil.copy2(ROOT/'src/nes/diagnostic/nes_native_spi165.sv',out/'nes_native_spi165.sv')
    (out/'nes_native165_bulk.inc').write_text(bulk_engine())
    return inputs
