# SPDX-License-Identifier: MIT
"""079 checkpoints around frozen report/FatFS/native077; modeled screen IO.

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
from nes_report079_prepare import writer079

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
    p.add_argument('--mode', choices=['normal', 'no-compare', 'no-reset', 'no-budget'], default='normal')
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
    (out/'native.inc').write_text(native, encoding='utf-8', newline='\n')
    for n in ['nes_sd_inventory.h', 'nes_sd_inventory.c', 'nes_sd_inventory_log.c',
              'nes_sd_inventory_log073.h', 'nes_sd_fault074.h']:
        copy('074', n)
    writer=out/'nes_sd_inventory_log.c'
    code=writer079(writer.read_text())
    writer.write_text(code,encoding='utf-8',newline='\n')
    for n in ['nes_report_checkpoint079.c','nes_report_checkpoint079.h']:
        shutil.copy2(ROOT/'src/nes/firmware'/n,out/n)
    checkpoint=out/'nes_report_checkpoint079.c'
    code=checkpoint.read_text()
    if a.mode=='no-compare':
        assert code.count('memcmp(line,back,33) || ')==1
        code=code.replace('memcmp(line,back,33) || ','')
    if a.mode=='no-reset':
        assert code.count(' snes_reset(1);\n if(!get_snes_reset()')==1
        code=code.replace(' snes_reset(1);\n if(!get_snes_reset()', ' /* mutation */\n if(!get_snes_reset()')
    if a.mode=='no-budget':
        code=code.replace(' if(!get_snes_reset() || !nes_return_io_step())', ' nes_return_log_allow(true);\n if(!get_snes_reset() || !nes_return_io_step())')
    checkpoint.write_text(code,encoding='utf-8',newline='\n')
    for n, content in {
        'config.h': '#ifndef MOCK_CONFIG_H\n#define MOCK_CONFIG_H\n#include <stdio.h>\n#include <stdint.h>\nstruct mock_nvic {uint32_t ISER[8];};\nextern struct mock_nvic checkpoint_nvic;\n#define NVIC (&checkpoint_nvic)\n#define OTG_FS_IRQn 67\n#endif\n',
        'snes.h':'#include <stdint.h>\nvoid snes_reset(int);\nuint8_t get_snes_reset(void);\n', 'uart.h': '/* no UART */\n',
        'fileops.h': '#include "ff.h"\n',
        'memory.h': '#define SRAM_CMD_ADDR 0xff1000u\n#include <stdint.h>\nuint16_t sram_writeblock(void *,uint32_t,uint16_t);\nuint16_t sram_readblock(void *,uint32_t,uint16_t);\n',
    }.items():
        (out/n).write_text(content, encoding='utf-8')
    source=ROOT/'tests/nes-functional/report_session078_host.c'
    host=source.read_text()
    inputs['public/host078']=sha(source)
    for name in ['sram_writeblock','sram_readblock']:
        host=re.sub(r'^uint16_t '+name+r'.*?\n','',host,flags=re.M)
    host=host.replace('static int during_blocktrans;', 'int during_blocktrans;')
    host=host.replace('uint32_t nes_diag_ticks(void)', 'static void reset_case(unsigned);\n#include "adapter.h"\nuint32_t nes_diag_ticks(void)')
    host=host.replace('return tick_origin+', 'return tick_origin+display_ticks+')
    host=host.replace('static void reset_case(unsigned fat32){','static void reset_case(unsigned fat32){\n checkpoint_reset();')
    host=host.replace(' assert(cmd_bits==48);',' assert(held&&!checkpoint_nvic.ISER[OTG_FS_IRQn>>5]);\n assert(cmd_bits==48);')
    host=host.replace('/HW005','/HW079')
    host=host.replace('printf("PASS078', 'checkpoint_tests();\n printf("PASS079')
    (out/'host.c').write_text(host,encoding='utf-8',newline='\n')
    shutil.copy2(ROOT/'tests/nes-functional/report_checkpoint079_adapter.h',out/'adapter.h')
    shutil.copy2(__file__, out/'executed-driver.py')
    cmd = [str(a.gcc), '-std=c11', '-O2', '-Wall', '-Wextra', '-ffunction-sections',
           '-fdata-sections', '-D__USE_MINGW_ANSI_STDIO=1', '-I.', 'host.c', 'ff.c',
           'unicode/ccsbcs.c', 'nes_diag_runtime.c', 'nes_menu_return.c',
           'nes_sd_inventory.c', 'nes_sd_inventory_log.c', 'nes_report_checkpoint079.c', '-Wl,--gc-sections', '-o', 'host.exe']
    with (out/'compile.log').open('wb') as f:
        subprocess.run(cmd, cwd=out, stdout=f, stderr=subprocess.STDOUT, check=True)
    with (out/'session.log').open('wb') as f:
        result = subprocess.run([str(out/'host.exe')], cwd=out, stdout=f, stderr=subprocess.STDOUT, timeout=120)
    log = (out/'session.log').read_text(errors='replace')
    if a.mode == 'normal':
        assert result.returncode == 0 and 'PASS079' in log, log[-3000:]
    else:
        needle={'no-compare':'r==8&&nes_return_failed()&&held',
                'no-reset':'result==0',
                'no-budget':'sdinv_write_report(text,sizeof(text),name,sizeof(name))==8'}[a.mode]
        assert result.returncode != 0 and 'Assertion' in log and needle in log, log[-3000:]
    if a.mode=='normal':
        timer=copy('077','stm32f4xx/timer.c','input-timer.c').read_text()
        definition=timer.index('bool nes_return_delay(unsigned time,bool milliseconds) {')
        (out/'timer.inc').write_text(function(timer[definition:],'nes_return_delay'),encoding='utf-8',newline='\n')
        shutil.copy2(ROOT/'tests/nes-functional/report_timer079_host.c',out/'timer-host.c')
        # MinGW resolves even unused COFF functions; retain the exact runtime
        # prefix and omit only unrelated menu-copy code from this timer unit.
        support=(out/'nes_menu_return.c').read_text()
        (out/'timer-return.c').write_text(support[:support.index('uint32_t nes_return_copy_menu(')],encoding='utf-8',newline='\n')
        cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-ffunction-sections',
             '-fdata-sections','-I.','timer-host.c','nes_diag_runtime.c','timer-return.c',
             '-Wl,--gc-sections','-o','timer.exe']
        with (out/'timer-compile.log').open('wb') as f:
            subprocess.run(cmd,cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
        with (out/'timer.log').open('wb') as f:
            subprocess.run([str(out/'timer.exe')],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=30)
        assert 'PASS079 TIMER checks=5' in (out/'timer.log').read_text()
    record = dict(mode=a.mode, exit=result.returncode, inputs=inputs,
                  checks=int(re.search(r'PASS079 checks=(\d+)', log)[1]) if a.mode=='normal' else None,
                  timer_checks=5 if a.mode=='normal' else None,
                  physical=False, arm_executed=False, model='GPIO card, SRAM/RESET/USB, TIM2 registers, prepared media, host CRC primitives and clock',
                  executed_files={f.relative_to(out).as_posix():sha(f) for f in out.rglob('*') if f.is_file()})
    (out/'result.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:record[k] for k in ['mode','exit','checks','physical']}))

if __name__ == '__main__':
    main()

