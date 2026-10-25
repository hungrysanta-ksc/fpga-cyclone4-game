# SPDX-License-Identifier: MIT
"""Seven-tag version of actual361: 112 useful bytes in the same128B M9K."""
from nes_delta231 import once
def apply(d,board=False):
 p=d/'nes_chr_cache192.sv';s=p.read_text()
 for a,b in [('[0:4]','[0:6]'),('j<5','j<7'),('scan==4','scan==6'),('replacement==4','replacement==6')]:
  assert a in s;s=s.replace(a,b)
 p.write_text(s,newline='\n')
 p=d/'nes_spi270.sv';s=p.read_text()
 for a,b in [('count==24','count==28'),('count<22','count<26'),('22:request_value280','26:request_value280'),('23:request_value280','27:request_value280')]:s=once(s,a,b)
 p.write_text(s,newline='\n')
 p=d/'nes_plan_spi200.sv';s=once(p.read_text(),'count==24','count==28');p.write_text(s,newline='\n')
 p=d/('nes_plan_path267.sv' if board else 'nes_plan_rom267.sv');s=p.read_text()
 for a,b in [('[79:0] tags','[111:0] tags'),('count==24','count==28'),('incoming!=5','incoming!=7'),('count<22','count<26'),('cursor==79','cursor==111')]:s=once(s,a,b)
 p.write_text(s,newline='\n')
