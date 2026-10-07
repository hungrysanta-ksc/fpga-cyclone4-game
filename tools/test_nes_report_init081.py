# SPDX-License-Identifier: MIT
"""Actual081 command GPIO/init path, exact080 runtime and legacy rejection."""
from pathlib import Path
import argparse, json, re, shutil, subprocess
from nes_report081_prepare import PIN, sha
from nes_diag_recovery_checks import function
ROOT = Path(__file__).resolve().parents[1]
def main():
    p = argparse.ArgumentParser()
    for n in ['evidence080','gcc','out']: p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--mode',choices=['normal','no-crc','post-fault-clock'],default='normal')
    a=p.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=False);e=a.evidence080.resolve()
    assert sha(e/'manifest.json')==PIN
    manifest=json.loads((e/'manifest.json').read_bytes())['files'];used={}
    def copy(n,target=None):
        k='work/arm-02/source/src/'+n;assert sha(e/k)==manifest[k];used[k]=manifest[k]
        shutil.copy2(e/k,o/(target or n))
    for n in ['nes_diag_runtime.c','nes_diag_runtime.h','nes_menu_return.c','nes_menu_return.h','nes_menu076.h','smc.h','diskio.h','integer.h','ff.c','ff.h','ffconf.h']:copy(n)
    (o/'unicode').mkdir();copy('ccsbcs.c','unicode/ccsbcs.c')
    f=o/'nes_menu_return.c';s=f.read_text();f.write_text(s[:s.index('uint32_t nes_return_copy_menu(')],encoding='utf-8')
    copy('stm32f4xx/sdnative.c','input-sdnative.c');raw=(o/'input-sdnative.c').read_text();bodies=[]
    for name in ['nes_diag_sd_error','nes_diag_sd_reset','nes_diag_sd_failed','getbits','make_crc7','sdn_status','sdn_initialize']:
        m=re.search(r'^(?:static inline void|static void|static uint32_t|void|bool|DSTATUS) '+name+r'\([^;{}]*\)\s*\{',raw,re.M);assert m,name
        bodies.append(function(raw[m.start():],name))
    (o/'native.inc').write_text(''.join(bodies),encoding='utf-8')
    shutil.copy2(ROOT/'src/nes/firmware/nes_report_init081.inc',o/'nes_report_init081.inc')
    shutil.copy2(ROOT/'src/nes/firmware/nes_report_disk081.c',o/'nes_report_disk081.c')
    f=o/'nes_report_init081.inc';s=f.read_text()
    if a.mode=='no-crc':
        assert s.count('if(!valid)')==1;s=s.replace('if(!valid)','if(false&&!valid)')
    if a.mode=='post-fault-clock':
        old='if(!report_guard081()||!nes_return_delay(2,false)||!report_owned081())return false;'
        assert s.count(old)==1;s=s.replace(old,'if(!report_guard081())return false;\n (void)nes_return_delay(2,false);')
    f.write_text(s,encoding='utf-8',newline='\n')
    for n,s in {
      'config.h':'#pragma once\n#include <stdint.h>\n#include <stdbool.h>\n#ifdef _WIN32\n#include <windows.h>\n#include <crtdbg.h>\n#endif\nstruct fake_nvic{uint32_t ISER[8];};\nextern struct fake_nvic nvic;\n#define NVIC (&nvic)\n#define OTG_FS_IRQn 67\n',
      'fileops.h':'/* Actual FatFS mount; disk payload is a modeled VBR. */\n',
      'uart.h':'#include <stdio.h>\n/* No UART on this report initialization/mount route. */\n',
      'memory.h':'/* No SRAM in this initializer-only test. */\n'
    }.items():(o/n).write_text(s,encoding='utf-8')
    shutil.copy2(ROOT/'tests/nes-functional/report_init081_host.c',o/'host.c');shutil.copy2(__file__,o/'executed-driver.py')
    cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-format','-ffunction-sections','-fdata-sections','-I.','host.c','nes_diag_runtime.c','nes_menu_return.c','ff.c','unicode/ccsbcs.c','nes_report_disk081.c','-Wl,--gc-sections','-o','host.exe']
    with (o/'compile.log').open('wb') as log:subprocess.run(cmd,cwd=o,stdout=log,stderr=subprocess.STDOUT,check=True)
    with (o/'run.log').open('wb') as log:r=subprocess.run([str(o/'host.exe')],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    text=(o/'run.log').read_text(errors='replace')
    if a.mode=='normal':assert r.returncode==0 and 'PASS081' in text,text[-3000:]
    else:
        needle='!sdn_report_initialize081()&&commands==n' if a.mode=='no-crc' else '!nes_return_failed()'
        assert r.returncode!=0 and 'Assertion' in text and needle in text,text[-3000:]
    record=dict(mode=a.mode,exit=r.returncode,checks=int(re.search(r'checks=(\d+)',text)[1]) if a.mode=='normal' else None,
                inputs=used,physical=False,files={p.relative_to(o).as_posix():sha(p) for p in o.rglob('*') if p.is_file()})
    (o/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(text[-700:])
if __name__=='__main__':main()
