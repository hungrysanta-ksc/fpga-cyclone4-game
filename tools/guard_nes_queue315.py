# SPDX-License-Identifier: MIT
import guard_nes_queue314 as old
from nes_test315 import reader
from nes_delta231 import once
old.old.TB=reader(old.old.TB,'record','record_valid','record_at','record_byte','ready','retire','reset')
old.old.TB=once(old.old.TB,'repeat(64)@(negedge clk);', 'repeat(64)begin @(negedge clk);if(at==0&&dut.write312)$fatal(1,"command still clears RAM");end')
old.old.TB=once(old.old.TB,'  passed();\n  restart();makepacket(2,0,2);sendpacket(0);', '''  release_slot();makepacket(2,3,2);sendpacket(1);
  if(record[119:80]!==0)$fatal(1,"stale token/count after slot reuse");
  passed();
  restart();makepacket(2,0,2);sendpacket(0);''')
if __name__=='__main__':old.old.main()
