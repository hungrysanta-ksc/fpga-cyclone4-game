# SPDX-License-Identifier: MIT
import inspect
from pathlib import Path
import check_nes_final332 as old

if __name__=='__main__':
 s=inspect.getsource(old.main).replace('.h_valid(h_valid),.h_data(h_data)', '.legacy_h_valid(h_valid),.legacy_h_data(h_data)')
 s=s.replace('nes_validator278 dut(', "nes_validator278 dut(.read359(34'd0),.ready359(),.private359(),")
 # Preserve the eight established independent final/raw0/STOP/reset cases.
 driver=Path(__file__).with_name('check_nes_final336.py').read_text().replace('s=inspect.getsource(old.main)', 's='+repr(s))
 exec(compile(driver,'final359','exec'),dict(__name__='__main__',__file__=__file__))
