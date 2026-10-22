# SPDX-License-Identifier: MIT
"""Live short-status ARM and common source/output/plan SPI control replacement."""
from pathlib import Path
import inspect,shutil
import probe_nes_refill267 as old
from probe_nes_refill269 import prepare as prior_prepare
from nes_delta231 import ROOT,once,sha
from nes_joint270 import patch_files,pass_ports,joint_ports,top_bus,JOINT_BIND,PLAN_BIND

def prepare(*args,**kwargs):
 d=args[0];src,pins=prior_prepare(*args,**kwargs);patch_files(d)
 p=d/'nes_joint266.sv';p.write_text(joint_ports(p.read_text()),encoding='utf-8',newline='\n')
 p=d/'nes_plan_rom267.sv';p.write_text(pass_ports(p.read_text(),'nes_plan_spi200 endpoint('),encoding='utf-8',newline='\n')
 p=d/'joint266_tb.sv';s=p.read_text();s=once(s,' nes_joint266 dut(',top_bus('host_clk','reset','ss','sck','mosi')+' nes_joint266 dut('+JOINT_BIND)
 s=once(s,' nes_plan_rom267 planrom(', ' nes_plan_rom267 planrom('+PLAN_BIND);p.write_text(s,encoding='utf-8',newline='\n')
 src['nes_spi270.sv']=(d/'nes_spi270.sv').read_text()
 for n in ['nes_joint270.py','nes_output270.c','probe_nes_refill270.py']:
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(ROOT/'tools'/n)
 return src,pins

def build(d):
 old.build(d)
 # The compile wrapper retains the old filename/ABI, but bytes are the new C.
 (d/'nes_output264.c').write_bytes((ROOT/'tools/nes_output270.c').read_bytes())

def main():
 ns=dict(old.__dict__);ns.update(prepare=prepare,build=build,__file__=__file__,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'refill270-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
