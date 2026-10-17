# SPDX-License-Identifier: MIT
"""Grouped epoch equivalence, including flag invariant after every tested edge."""
import inspect
import test_nes_epoch217 as prior
from nes_epoch217_group import transform
from nes_board204 import replace

s=inspect.getsource(prior.main).replace('nes-loader217/source02','nes-loader217/source03')
s=replace(s,"s=saved.read_text();", "s=saved.read_text().replace(\"dut.serial=32'hffffffff;\",\"dut.serial=32'hffffffff;dut.all_ones=8'hff;\");")
s=replace(s,'  cases++;','''  for(integer k=0;k<8;k++)if(dut.all_ones[k]!==(&dut.serial[k*4+:4]))$fatal(1,"EPOCH217 flag invariant");
  cases++;''')
s=replace(s,'dut.serial=value;refdut.serial=value;','dut.serial=value;refdut.serial=value;for(integer k=0;k<8;k++)dut.all_ones[k]=(&value[k*4+:4]);')
s=replace(s,"wrong=new.read_text().replace('carry_in&!serial[epoch_bit]','carry_in&serial[epoch_bit]')",
 'wrong=new.read_text().replace("serial[group217*4+:4]+{3\'b0,carry_in}", "serial[group217*4+:4]+{2\'b0,carry_in,1\'b0}")')
s=replace(s,'wrong_gray_rejected=True,source_pins=', 'wrong_gray_rejected=True,flag_invariant=True,declared_extra_registers=8,source_pins=')
ns=dict(prior.__dict__);ns.update(transform=transform,__file__=__file__)
exec(compile(s,'epoch217_group','exec'),ns)
if __name__=='__main__':ns['main']()
