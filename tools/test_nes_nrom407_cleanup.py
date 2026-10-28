# SPDX-License-Identifier: MIT
"""Run exact generated 227 cleanup block with modeled ownership/hardware."""
import argparse
import json
import subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
a=p.parse_args();a.build=a.build.resolve();d=a.out.resolve()
assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
s=(a.build/'nes_h1_stm32.c').read_text();body=s[s.index('bool nes_menu_sd_probe('):]
cleanup=body[body.index('cleanup:'):]
assert cleanup.rstrip().endswith('}') and cleanup.count('cleanup:')==1
cleanup=cleanup.replace('cleanup:', '',1)
wrapper='''static bool test_cleanup407(struct sd_report *report,bool opened,bool changed_fpga,bool begin_sent,bool usb_irq_enabled) {
 struct nes_mcu_load_report *r=&report->load;FIL file={0};
 const struct nes_rom_spi_io io={0};struct nes_rom_spi_status status={0};
'''+cleanup
(d/'cleanup407.inc').write_text(wrapper,newline='\n')
prod=BASE/'probes/nes-repeat227/arm01/src';test=ROOT/'tests/nes-nrom407/cleanup_tb.c'
args=['C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe','-std=c99','-O2','-Wall','-Wextra','-Werror',
      '-I',str(d),'-I',str(prod),str(test),'-o',str(d/'test.exe')]
with(d/'compile.log').open('wb') as f:r=subprocess.run(args,cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,(d/'compile.log').read_text(errors='replace')
with(d/'test.log').open('wb') as f:r=subprocess.run([str(d/'test.exe')],cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0 and 'NROM407 227 cleanup block PASS' in (d/'test.log').read_text()
result={'passed':True,'generated_loader':sha(a.build/'nes_h1_stm32.c'),'extracted_cleanup':sha(d/'cleanup407.inc'),'test':sha(test),
        'scope':'exact 227 cleanup block with modeled status, STOP, configuration and token; not physical IO or whole loader'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
