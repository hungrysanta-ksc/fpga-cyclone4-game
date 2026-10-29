# SPDX-License-Identifier: MIT
"""Actual479 loader/verify/programmer/run136 and FatFS, explicit modeled peers.

No native game execution, RTL, ARM CPU or physical board timing in this test.
The user's ROM stays private and is supplied at runtime, never generated in C.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def once(s, before, after):
    assert s.count(before) == 1, before[:120]
    return s.replace(before, after)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['build', 'rom', 'out']:
        p.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    assert sha(a.rom) == 'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
    d = a.out.resolve()
    assert str(d).isascii() and not d.exists()
    d.mkdir(parents=True)
    prod = BASE / 'probes/nes-nrom418/arm476-02/src'
    host = BASE / 'probes/nes-run136/evidence/initial/host04'
    for f in host.glob('*.h'):
        shutil.copyfile(f, d / f.name)
    for n in ['ff.c', 'ff.h', 'ffconf.h', 'diskio.h', 'nes_run136.h']:
        shutil.copyfile(prod / n, d / n)
    (d / 'unicode').mkdir()
    shutil.copyfile(prod / 'ccsbcs.c', d / 'unicode/ccsbcs.c')
    # Reuse the existing modeled programmer pins/observer peers, replacing both
    # executable loader and run136 with the exact new selected source below.
    fixture = BASE / 'probes/nes-nrom414/run03-loader.c'
    s = fixture.read_text()
    s = once(s, '#include "nes_nrom406.h"', '#include "nes_mmc479.h"')
    s = once(s, 'filedata[24592]', 'original[0x60010],filedata[0x60010]')
    s = once(s, 'BASE_FAILURE=8};', 'BASE_FAILURE=8,BAD_CRC=9,NROM_ID=10,SHORT_FILE=11,LONG_FILE=12,MIRROR=13,TRAINER=14,BAD_CHR=15,BAD_FLAGS7=16,RESERVED=17,EXPECTED_CHR32=18,STALE_READ_TAG=19};')
    start = s.index('/* SPDX-License-Identifier: MIT */', s.index('#include "full408.inc"'))
    end = s.index('bool nes_game149_transfer(', start)
    run = (a.build / 'nes_run136.inc').read_text()
    run = once(run, '#include "nes_runtime_board165.inc"', '''
/* Explicit native model: run136 orchestration only, no game processing. */
static bool native_session165(const struct nes_rom_spi_io *io,uint32_t epoch){
 (void)io;assert(epoch==0x5a04eed7u);nes_run136.first=1;nes_run136.last=2;return true;
}
static bool nes_display_leave146(void){return true;}
''')
    s = s[:start] + run + '\n' + s[end:]
    s = once(s, 'reply_count=check_next;rx[3]=memory[check_next];', 'reply_count=check_next+(scenario==STALE_READ_TAG);rx[3]=memory[check_next];')
    start = s.index(" filedata[0]='N';")
    end = s.index(' if(test==BAD_HEADER)', start)
    s = s[:start] + ' memcpy(filedata,original,sizeof(filedata));\n' + s[end:]
    s = once(s, ' if(test==BAD_HEADER)filedata[6]=1;', ''' if(test==BAD_HEADER)filedata[6]=1;
 if(test==BAD_CRC)filedata[100]^=1;
 if(test==MIRROR)filedata[6]^=1;
 if(test==TRAINER)filedata[6]|=4;
 if(test==BAD_CHR)filedata[5]=1;
 if(test==BAD_FLAGS7)filedata[7]=8;
 if(test==RESERVED)filedata[8]=1;''')
    s = once(s, ' nrom_fatdisk_prepare(filedata,sizeof(filedata));', ''' nrom_fatdisk_prepare(filedata,sizeof(filedata));
 if(test==SHORT_FILE||test==LONG_FILE)mmc_fatdisk_size(sizeof(filedata)+(test==SHORT_FILE?-1:1));''')
    s = once(s, 'void nrom_fatdisk_mutate(uint32_t);', 'void nrom_fatdisk_mutate(uint32_t);\nvoid mmc_fatdisk_size(uint32_t);')
    s = once(s, 'board_id=test==WRONG_ID?0x74:0x78;', 'board_id=test==WRONG_ID?0x74:(test==NROM_ID?0x78:0x79);')
    s = once(s, 'int main(void){', '''int main(int argc,char **argv){
 assert(argc==2);FILE *input=fopen(argv[1],"rb");assert(input);
 assert(fread(original,1,sizeof(original),input)==sizeof(original));assert(fgetc(input)==EOF);assert(!fclose(input));''')
    s = once(s, 'i<=BASE_FAILURE', 'i<=STALE_READ_TAG')
    s = once(s, 'false,&p);', 'i==EXPECTED_CHR32,&p);')
    start = s.index('   assert(!memcmp(memory,filedata+16,16384));')
    end = s.index('  }else if(i==BAD_HEADER)', start)
    s = s[:start] + '   assert(!memcmp(memory,filedata+16,sizeof(memory)));\n' + s[end:]
    s = once(s, 'i==BAD_HEADER){', 'i==BAD_HEADER||i==BAD_CRC||(i>=SHORT_FILE&&i<=EXPECTED_CHR32)){')
    (d / 'host.c').write_text(s, newline='\n')
    disk_source = BASE / 'probes/nes-nrom412/loader01-disk.c'
    disk = disk_source.read_text().replace('49u*512u', '0x60010u')
    # The old tiny ROM used cluster51 for synthetic FPGA files. Move that file
    # beyond the full384KiB ROM chain rather than corrupting its FAT/data.
    disk = disk.replace('51*2', '802*2').replace('26,51', '26,802').replace('DATA_SECTOR+49', 'DATA_SECTOR+800')
    disk += '\nvoid mmc_fatdisk_size(uint32_t n){dword(media+ROOT_SECTOR*512u+28,n);}\n'
    (d / 'fat_disk.c').write_text(disk, newline='\n')
    source = (a.build / 'nes_h1_stm32.c').read_text()
    helpers = source[source.index('static uint32_t load_crc('):source.index('\nbool nes_mcu_load_probe(')]
    sd = source[source.index('static bool sd_query('):source.index('\n\n#include "nes_cf86_session094.h"')]
    body = source[source.index('bool nes_menu_sd_probe('):]
    (d / 'full408.inc').write_text(helpers + '\n' + sd + '\n' + body, newline='\n')
    gcc = 'C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
    command = [gcc, '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-Wno-unused-function', '-Wno-sign-compare', '-Wno-format', '-DNROM_USE_FATFS', '-I', str(d), '-I', str(a.build.resolve()), '-I', str(prod), str(d/'ff.c'), str(d/'unicode/ccsbcs.c'), str(a.build.resolve()/'nes_rom_verify.c'), str(prod/'nes_rom_spi.c'), str(d/'fat_disk.c'), str(d/'host.c'), '-o', str(d/'test.exe')]
    for name, args in [('compile', command), ('test', [str(d/'test.exe'), str(a.rom.resolve())])]:
        with (d / (name + '.log')).open('wb') as f:
            r = subprocess.run(args, cwd=d, stdout=f, stderr=subprocess.STDOUT, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode == 0, (d / (name + '.log')).read_text(errors='replace')[-8000:]
    log = (d / 'test.log').read_text()
    assert log.count('case=') == 20 and 'case=19' in log
    result = {'passed': True, 'scope': __doc__, 'cases': 20,
              'loader_sha256': sha(a.build/'nes_h1_stm32.c'), 'run136_sha256': sha(a.build/'nes_run136.inc'),
              'verify_sha256': sha(a.build/'nes_rom_verify.c'), 'FatFS_sha256': sha(prod/'ff.c'),
              'original_ROM_sha256': sha(a.rom), 'full_payload_compared': 0x60000,
              'fixture_base_sha256': sha(fixture), 'disk_base_sha256': sha(disk_source),
              'generated_test_sha256': sha(d/'host.c'), 'generated_disk_sha256': sha(d/'fat_disk.c'),
              'guards': ['CRC/header/length/mapper/mirroring/trainer/CHR/NES2/reserved', 'wrong NROM78 and legacy74 board', 'file mutation in transfer/readback', 'SPI write/readback/stale tag', 'STOP and base restoration failure'],
              'game_native_and_observer_are_modeled': True, 'physical_hardware': False}
    (d/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'passed': True, 'cases': 20, 'full_payload': 0x60000, 'scope': 'actual host loader/FatFS/programmer/run136; native/IO modeled'}))


if __name__ == '__main__':
    main()
