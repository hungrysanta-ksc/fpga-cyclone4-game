# SPDX-License-Identifier: MIT
"""Full-length 410 cosimulation; host C, functional PSRAM, modeled RUN/base."""
import argparse
import sys
from pathlib import Path
from nes_delta231 import ROOT

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--timeout',type=int,default=43200)
a=p.parse_args();assert a.timeout>0
runner=(ROOT/'tools/test_nes_nrom410_prefix.py').read_text()
def once(s,old,new):
 assert s.count(old)==1,(old,s.count(old))
 return s.replace(old,new)
runner=once(runner,'assert 0<a.limit<=16384','assert a.limit==393216')
runner=once(runner,'if(tx[0]==NES_ROM_DATA && sent_data==TEST_LIMIT)return false;', '/* Full transfer: no injected prefix fault. */')
runner=once(runner,'if(tx[0]==NES_ROM_DATA)sent_data++;', '''if(tx[0]==NES_ROM_DATA){sent_data++;if(!(sent_data%4096)){printf("NROM411 WRITE %u\\n",sent_data);fflush(stdout);}}
 if(tx[0]==0x68 && !(tx[3]%4096) && tx[2]%16==0){printf("NROM411 ACK %u\\n", ((unsigned)tx[1]<<16)|((unsigned)tx[2]<<8)|tx[3]);fflush(stdout);}''')
runner=once(runner,'worker_code=(safe || p.sd.verified || sent_data!=TEST_LIMIT || !sticky || irq_count!=0);', 'worker_code=(!safe || !p.sd.verified || !p.sd.load.stop_ok || !p.sd.load.base_restored || sent_data!=TEST_LIMIT || sticky || irq_count!=1 || config_count!=2);')
runner=once(runner,"shutil.copyfile(ROOT/'tests/nes-nrom410/prefix_tb.sv',d/'prefix_tb.sv')", """bench=(ROOT/'tests/nes-nrom410/prefix_tb.sv').read_text()
start=bench.index('  if(loaded_bytes!==`TEST_LIMIT')
end=bench.index('  $finish;',start)
bench=bench[:start]+'''  if(loaded_bytes!==19'h60000 || !loaded || run_enable || fault || dut.verified)$fatal(1,"full final state");
  $display("PASS NROM411 full loader write readback START STOP, modeled base");
'''+bench[end:]
(d/'prefix_tb.sv').write_text(bench,newline='\\n')""")
runner=once(runner,'timeout=300,creationflags=',f'timeout={a.timeout},creationflags=')
runner=once(runner,"f'PASS NROM410 real C/FatFS to real RTL prefix bytes={a.limit}'", "'PASS NROM411 full loader write readback START STOP, modeled base'")
runner=once(runner,"'scope':'deliberately aborted before full load, actual 227 loader/FatFS host C to actual FPGA SPI/boot/loader and PSRAM pin model; no complete CRC/readback/START/STOP/base recovery or ARM execution'", "'scope':'full host C/FatFS loader with actual SPI/boot/loader/reader RTL and functional PSRAM; modeled identify/run/base, no ARM execution or physical hardware'")
sys.argv=['test_nes_nrom410_prefix.py','--build',str(a.build),'--out',str(a.out),'--limit','393216']
exec(compile(runner,str(ROOT/'tools/test_nes_nrom410_prefix.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom410_prefix.py')})
