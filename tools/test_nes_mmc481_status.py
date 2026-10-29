# SPDX-License-Identifier: MIT
"""Compile the selected ARM screen146 parser; check all v3 flags and reject v2.

Host ABI with a modeled SPI reply, not a boot or MCU timing simulation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arm', required=True, type=Path)
p.add_argument('--out', required=True, type=Path)
a = p.parse_args()
d = a.out.resolve()
d.mkdir(parents=True, exist_ok=False)
s = (a.arm/'nes_run136.inc').read_text(encoding='utf8')
begin = s.index('static bool screen146(')
parser = s[begin:s.index('\n}\n', begin)+3]
code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
struct nes_rom_spi_io { int unused; };
struct {uint8_t screen_valid,screen_stage,screen_error,screen_flags;
        uint16_t screen_frames;uint32_t screen_phase_mask;} nes_run136;
static uint8_t answer[8];static bool transport_ok=true;
static bool nes_rom_spi_transfer(const struct nes_rom_spi_io *io,const uint8_t *tx,uint8_t *rx){
 (void)io;assert(tx[0]==0x73);memcpy(rx,answer,8);return transport_ok;
}
''' + parser + r'''
int main(void){
 answer[1]=0xe6;answer[2]=3;answer[3]=0;answer[5]=0x12;answer[6]=0x34;answer[7]=3;
 for(unsigned flags=0;flags<256;flags++){
  nes_run136.screen_flags=0;answer[4]=flags;assert(screen146(NULL));
  assert(nes_run136.screen_valid&&nes_run136.screen_stage==3&&nes_run136.screen_flags==flags&&nes_run136.screen_frames==0x1234);
 }
 nes_run136.screen_flags=0;answer[4]=8;assert(screen146(NULL));
 answer[4]=16;assert(screen146(NULL));answer[4]=0;assert(screen146(NULL));
 assert(nes_run136.screen_flags==24);
 answer[7]=2;assert(!screen146(NULL));answer[7]=4;assert(!screen146(NULL));
 answer[7]=3;answer[1]=0xe5;assert(!screen146(NULL));answer[1]=0xe6;
 transport_ok=false;assert(!screen146(NULL));transport_ok=true;
 for(unsigned i=0;i<4;i++){answer[2]=0x31+i;assert(screen146(NULL));}
 assert(nes_run136.screen_phase_mask==15);
 puts("PASS MMC481 actual parser 256 flag combinations, 4 rejections, 4 phase milestones");return 0;
}
'''
(d/'test.c').write_text(code, encoding='utf8', newline='\n')
gcc = 'C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
for name, cmd in [('compile', [gcc, '-O2', '-std=c99', '-Wall', '-Wextra', '-Werror', 'test.c', '-o', 'test.exe']),
                  ('test', [str(d/'test.exe')])]:
    r = subprocess.run(cmd, cwd=d, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (d/(name+'.log')).write_bytes(r.stdout)
    assert r.returncode == 0, name
result = {'passed': True, 'scope': __doc__, 'flag_combinations': 256,
          'rejections': ['old v2', 'unknown v4', 'bad ID', 'transport failure'],
          'source_SHA256': hashlib.sha256((a.arm/'nes_run136.inc').read_bytes()).hexdigest()}
(d/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
print(json.dumps({'passed': True, 'flag_combinations': 256, 'rejections': 4}))
