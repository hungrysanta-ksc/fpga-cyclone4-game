# SPDX-License-Identifier: MIT
"""Retain the38 source/receipt/display STOP guards on the common SPI owner."""
import inspect
import guard_nes_joint269 as old
from nes_delta231 import once
from nes_joint270 import patch_files,joint_ports,top_bus,JOINT_BIND

def prepare(d,last):
 src,pins,stats=old.prepare(d,last);patch_files(d)
 p=d/'nes_joint266.sv';p.write_text(joint_ports(p.read_text()),encoding='utf-8',newline='\n')
 p=d/'joint266_tb.sv';s=p.read_text();s=once(s,' nes_joint266 dut(',top_bus('host_clk','reset','ss','sck','mosi')+"assign plan_status270=184'd0;assign plan_crc270=1'b0;\n nes_joint266 dut("+JOINT_BIND);p.write_text(s,encoding='utf-8',newline='\n')
 src['nes_spi270.sv']=(d/'nes_spi270.sv').read_text();return src,pins,stats

def main():
 ns=dict(old.__dict__);ns.update(prepare=prepare,__file__=__file__)
 exec(compile(inspect.getsource(old.main),'guard270-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
