# SPDX-License-Identifier: MIT
"""Whole frozen report/FatFS and077 native CMD17/24 C over a GPIO card model.

No ARM execution, card initialization, analog timing or installation approval.
Private frozen074/077 inputs are required; original archives are never edited.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from nes_diag_recovery_checks import function

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = {
    '074': '2be1006b6365414d2246e1dc38655126e3f2b00405871422f1f7a9626d37165b',
    '077': '8b4b5a9385dd7ced9a46b725d9e3a71f6877734b07febe3f0ec560f30842720c',
}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    for n in ['evidence074', 'evidence077', 'gcc', 'out']:
        p.add_argument('--'+n, type=Path, required=True)
    p.add_argument('--mode', choices=['normal', 'no-end', 'no-readback'], default='normal')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    out = a.out.resolve()
    inventories = {}
    for version in MANIFESTS:
        e = getattr(a, 'evidence'+version).resolve()
        assert sha(e/'manifest.json') == MANIFESTS[version]
        inventories[version] = (e, json.loads((e/'manifest.json').read_bytes())['files'])
    inputs = {}
    def copy(version, name, target=None):
        e, pins = inventories[version]
        key = 'arm/source/src/'+name
        assert sha(e/key) == pins[key], key
        inputs[version+'/'+name] = pins[key]
        dest = out/(target or name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(e/key, dest)
        return dest
    for n in ['ff.c', 'ff.h', 'ffconf.h', 'integer.h', 'diskio.h',
              'nes_diag_runtime.c', 'nes_diag_runtime.h', 'nes_menu_return.c',
              'nes_menu_return.h', 'nes_menu076.h', 'smc.h']:
        copy('077', n)
    copy('077', 'ccsbcs.c', 'unicode/ccsbcs.c')
    raw = copy('077', 'stm32f4xx/sdnative.c', 'input-sdnative.c').read_text()
    names = ['nes_diag_sd_error', 'nes_diag_sd_reset', 'nes_diag_sd_failed',
             'wiggle_fast_pos', 'wiggle_fast_neg', 'wiggle_fast_neg1', 'wiggle_fast_pos1',
             'get_and_check_datacrc', 'wait_busy', 'send_command_fast', 'make_crc7',
             'cmd_fast', 'send_datablock', 'nes_diag_sd_response', 'nes_diag_sd_read',
             'sdn_read', 'nes_return_sd_write', 'sdn_write', 'sdn_ioctl']
    bodies = []
    for name in names:
        m = re.search(r'^(?:static inline void|static void|static bool|static DRESULT|int|void|bool|DRESULT) '+name+r'\([^;{}]*\)\s*\{', raw, re.M)
        assert m, name
        bodies.append(function(raw[m.start():], name))
    native = raw[:raw.index('#include')]+''.join(bodies)
    if a.mode == 'no-end':
        guard = '  if(nes_diag_active()&&!BITBAND(SD_DAT0REG->GPIO_I, SD_DAT0BIT)){nes_diag_sd_error(NES_DIAG_SD_RESPONSE);return;}\n'
        assert native.count(guard) == 1
        native = native.replace(guard, '')
    (out/'native.inc').write_text(native, encoding='utf-8', newline='\n')
    for n in ['nes_sd_inventory.h', 'nes_sd_inventory.c', 'nes_sd_inventory_log.c',
              'nes_sd_inventory_log073.h', 'nes_sd_fault074.h']:
        copy('074', n)
    if a.mode == 'no-readback':
        f = out/'nes_sd_inventory_log.c'
        s = f.read_text()
        assert s.count('||memcmp(data,report+pos,n)') == 1
        f.write_text(s.replace('||memcmp(data,report+pos,n)', ''), encoding='utf-8', newline='\n')
    for n, content in {
        'config.h': '#include <stdio.h>\n', 'uart.h': '/* no UART */\n',
        'fileops.h': '#include "ff.h"\n',
        'memory.h': '#include <stdint.h>\nuint16_t sram_writeblock(void *,uint32_t,uint16_t);\nuint16_t sram_readblock(void *,uint32_t,uint16_t);\n',
    }.items():
        (out/n).write_text(content, encoding='utf-8')
    shutil.copy2(ROOT/'tests/nes-functional/report_session078_host.c', out/'host.c')
    shutil.copy2(__file__, out/'executed-driver.py')
    cmd = [str(a.gcc), '-std=c11', '-O2', '-Wall', '-Wextra', '-ffunction-sections',
           '-fdata-sections', '-D__USE_MINGW_ANSI_STDIO=1', '-I.', 'host.c', 'ff.c',
           'unicode/ccsbcs.c', 'nes_diag_runtime.c', 'nes_menu_return.c',
           'nes_sd_inventory.c', 'nes_sd_inventory_log.c', '-Wl,--gc-sections', '-o', 'host.exe']
    with (out/'compile.log').open('wb') as f:
        subprocess.run(cmd, cwd=out, stdout=f, stderr=subprocess.STDOUT, check=True)
    with (out/'session.log').open('wb') as f:
        result = subprocess.run([str(out/'host.exe')], cwd=out, stdout=f, stderr=subprocess.STDOUT, timeout=120)
    log = (out/'session.log').read_text(errors='replace')
    if a.mode == 'normal':
        assert result.returncode == 0 and 'PASS078' in log, log[-3000:]
    else:
        needle = 'result==8' if a.mode == 'no-end' else 'result==7'
        assert result.returncode != 0 and 'Assertion' in log and needle in log, log[-3000:]
    record = dict(mode=a.mode, exit=result.returncode, inputs=inputs,
                  checks=int(re.search(r'PASS078 checks=(\d+)', log)[1]) if a.mode=='normal' else None,
                  physical=False, arm_executed=False, model='GPIO card, prepared media, host CRC primitives and clock',
                  executed_files={f.relative_to(out).as_posix():sha(f) for f in out.rglob('*') if f.is_file()})
    (out/'result.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:record[k] for k in ['mode','exit','checks','physical']}))

if __name__ == '__main__':
    main()
