# SPDX-License-Identifier: MIT
"""Run exact generated 227 loader validation/write blocks with mocked IO."""
import argparse
import json
import subprocess
from pathlib import Path
from nes_delta231 import BASE, ROOT, sha

p=argparse.ArgumentParser()
p.add_argument('--build',required=True,type=Path)
p.add_argument('--out',required=True,type=Path)
a=p.parse_args();a.build=a.build.resolve();d=a.out.resolve()
assert d.as_posix().isascii() and not d.exists()
d.mkdir(parents=True)
src=(a.build/'nes_h1_stm32.c').read_text()
helpers=src[src.index('static uint32_t load_crc('):src.index('\nbool nes_mcu_load_probe(')]
body=src[src.index('bool nes_menu_sd_probe('):]
pre=body[body.index(' if(!load_read(&file,header,sizeof(header),r))goto cleanup;'):body.index('\n configure116:')]
start=body.index(' if(!nes_checkpoint112("BEGIN_LOAD"')
end=body.index(' r->end_accepted=true;',start)+len(' r->end_accepted=true;')
transfer=body[start:end]
wrapper='''
static bool test_transfer407(FIL *input, struct nes_mcu_load_report *r) {
 FIL file=*input; uint8_t header[16],buffer[256];
 struct nes_nrom406_profile nrom={0};
 struct nes_rom_spi_io io={0};struct nes_rom_spi_status status={0};
 uint32_t total=0,expected_crc=0,crc=0xffffffffu;
 bool expected_chr32=false,opened=true,begin_sent=false;
 memset(r,0,sizeof(*r));
'''+pre+'''
 if(mutate)file.data[100]^=1;
'''+transfer+'''
cleanup:
 *input=file;(void)opened;(void)begin_sent;
 return r->result==NES_MCU_LOAD_OK && r->end_accepted;
}
'''
(d/'transfer407.inc').write_text(helpers+wrapper,newline='\n')
prod=BASE/'probes/nes-repeat227/arm01/src';test=ROOT/'tests/nes-nrom407/transfer_tb.c'
args=['C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',
      '-std=c99','-O2','-Wall','-Wextra','-Werror','-I',str(d),'-I',str(a.build),'-I',str(prod),
      str(a.build/'nes_nrom406.c'),str(test),'-o',str(d/'test.exe')]
with (d/'compile.log').open('wb') as f:
 r=subprocess.run(args,cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0,(d/'compile.log').read_text(errors='replace')
with (d/'test.log').open('wb') as f:
 r=subprocess.run([str(d/'test.exe')],cwd=d,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
assert r.returncode==0 and 'NROM407 exact 227 validation/write sections PASS' in (d/'test.log').read_text()
result={'passed':True,'generated_loader':sha(a.build/'nes_h1_stm32.c'),
        'extracted_blocks':sha(d/'transfer407.inc'),'test':sha(test),
        'scope':'exact generated 227 file validation and SPI-write loop with modeled file/SPI; no full loader STOP/base'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
