# SPDX-License-Identifier: MIT
"""Actual main pending spans/full load_rom, reusing pinned097 native harness.

Peripheral side effects remain explicit models. No physical/whole-main claim.
"""
from pathlib import Path
import argparse, json, re, shutil, subprocess
from nes_spi_boot import ROOT, sha
from nes_diag_recovery_checks import function
from nes_menu098 import adapt, once

def definition(s, n):
    m = re.search(r'^(?:static )?(?:uint\d+_t|void|bool|int|enum \w+) '+n+r'\s*\([^;{}]*\)\s*\{', s, re.M)
    assert m, n
    return function(s[m.start():], n)

def main():
    p=argparse.ArgumentParser()
    for n in ['evidence094','evidence097','out','gcc']: p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--baseline',action='store_true')
    p.add_argument('--scenario',type=int,default=0)
    p.add_argument('--suite',action='store_true')
    p.add_argument('--geometry96',action='store_true')
    p.add_argument('--mutation',choices=['entry-address','copy-address','prepared','postrelease'])
    a=p.parse_args(); o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
    def write(n,s): (o/n).write_text(s,encoding='utf-8',newline='\n')
    pins={}; sources={}
    for num,e in [(94,a.evidence094),(97,a.evidence097)]:
        meta=json.loads((ROOT/f'analysis/{"session094" if num==94 else "config097"}-verification.json').read_bytes())
        assert sha(e/'manifest.json')==meta['manifest_sha256']
        pins[num]=json.loads((e/'manifest.json').read_bytes())['files']
    source=a.evidence097/('fat32-96-01' if a.geometry96 else 'suite03')
    # Prepared inputs are reused, not the previous compiled executable/results.
    for f in source.rglob('*'):
        if f.is_file() and (f.suffix in ['.c','.h','.inc','.packed','.raw','.bin','.nes']):
            key=source.name+'/'+f.relative_to(source).as_posix();assert sha(f)==pins[97][key]
            dest=o/f.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
            sources['097/'+key]=sha(f)
    src=a.evidence094/'arm04/src'
    def read(n):
        key='arm04/src/'+n;assert sha(src/n)==pins[94][key],key
        sources['094/'+key]=sha(src/n)
        dest=o/('original-'+n.replace('/','-'));shutil.copy2(src/n,dest)
        return (src/n).read_text()
    memory=read('memory.c'); main_c=read('main.c'); mh=read('memory.h')
    config=read('obj-nes-094/autoconf.h')
    assert '#define MENU_FILENAME   "/sd2snes/m3nu.bin"' in config
    rtc=read('stm32f4xx/rtc.h');read('stm32f4xx/rtc.c')
    enum=re.search(r'typedef enum \{[^}]+\} rtcstate_t;',rtc);assert enum
    write('rtc098-enum.inc',enum[0]+'\n')
    write('memory.c',memory)
    if not a.baseline: adapt(o)
    if a.mutation=='entry-address':write('memory.c',once((o/'memory.c').read_text(),'||base_addr!=SRAM_MENU_ADDR)','||base_addr)'))
    if a.mutation=='copy-address':write('nes_menu_return.c',once((o/'nes_menu_return.c').read_text(),'address==SRAM_MENU_ADDR','!address'))
    # All of load_rom, including unreachable branches, is compiled unchanged.
    write('load098.inc',definition((o/'memory.c').read_text(),'load_rom'))
    write('reliable098.inc',definition(memory,'sram_reliable'))
    pending=main_c[main_c.index('    if(nes_menu_diagnostic_pending()) {'):main_c.index('    while(get_cic_state() == CIC_FAIL)')]
    ready=main_c[main_c.index('nes_return_menu_ready:'):main_c.index('    while(!cmd) {')]
    body='static bool actual_main098(void){\n'+pending+'assert(!"pending path required");\n'+ready+'return true;\n}\n'
    if a.mutation=='prepared':body=once(body,'!nes_menu_diagnostic_prepared(nes_menu_size!=0 && sram_reliable())','false')
    if a.mutation=='postrelease':body=once(body,'nes_return_failed()||get_cic_state()==CIC_FAIL||!sram_reliable()||nes_return_failed()','false')
    write('main098.inc',body)
    defines='\n'.join(re.findall(r'^#define (?:SRAM_|LOADROM_|LOADRAM_|MENU_ADDR_).*',mh,re.M))+'\n'
    write('memory.h',(o/'memory.h').read_text()+defines)
    for n in ['cfg.h','sgb.h','cic.h']:write('actual-'+n,read(n))
    # Helpers preserve the actual configuration/status serialization and autoboot file read.
    snes=read('snes.c');cfg=read('cfg.c');fileops=read('fileops.c')
    write('helpers098.inc',''.join(definition(cfg,n) for n in ['cfg_load_to_menu','cfg_is_autoboot_enabled','cfg_is_r213f_override_enabled','cfg_is_onechip_transient_fixes','cfg_get_brightness_limit'])+definition(snes,'status_load_to_menu'))
    write('actual-snes.h',read('snes.h'))
    write('fileops098.inc',''.join(definition(fileops,n) for n in ['file_open','file_close']))
    fh=read('fileops.h');write('fileops098-defines.inc','\n'.join(re.findall(r'^#define (?:FILE_|AUTOBOOT_).*',fh,re.M))+'\n')
    fpga=read('fpga_spi.h');write('features098.inc','\n'.join(re.findall(r'^#define FEAT_.*',fpga,re.M))+'\n')
    host=(o/'config097_host.c').read_text()
    host=host.replace('static uint8_t menu_ram097[65536]','static uint8_t menu_ram097[0x1000000]')
    host=host.replace('static void file_close(void){file_res=f_close(&file_handle);}','')
    host=host.replace('#include "classify.inc"','')
    # Actual main reads autoboot after RESET release, before ownership leaves.
    # The earlier097 harness asserted RESET for its narrower pre-release IO.
    host=once(host,'if(measured096)assert(!irq&&reset_held);','if(measured096)assert(!irq&&nes_diag_active());')
    start=host.index('uint16_t sram_writeblock(');end=host.index('int main(int argc',start)
    write('host098-prefix.inc',host[:start])
    # The original platform model owns reset/UART/time; 098 overrides only reset.
    platform=(o/'platform.c').read_text()
    platform=platform.replace(definition(platform,'snes_reset'),'void snes_reset(int);\n')
    write('platform.c',platform)
    write('card.c',(o/'card.c').read_text()+'''\nvoid card_autoboot098(void){
      const uint8_t name[]="/example.sfc\\n";put_file096("/sd2snes/autoboot.cfg",name,sizeof(name)-1);
      nes_return_reset();commands=read_commands=write_commands=commits=rises=falls=read_nibbles=0;
    }\n''')
    shutil.copy2(ROOT/'tests/nes-functional/menu098_host.c',o/'host098.c')
    shutil.copy2(__file__,o/'executed-driver.py');shutil.copy2(ROOT/'tools/nes_menu098.py',o/'executed-adapter.py')
    cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-ffunction-sections','-fdata-sections','-I.',
         '-DGBC_SAVE_G12','-DGBC_DUMP_G12','card.c','host098.c','ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c','-Wl,--gc-sections','-o','host.exe']
    with (o/'compile.log').open('wb') as f:subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT,check=True)
    cases=[]
    for sc in (list(range(15))+list(range(20,29)) if a.suite else [a.scenario]):
        log=o/f'case-{sc}.log'
        with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),str(sc),str(int(a.baseline)),*[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        text=log.read_text(errors='replace')
        if a.mutation:assert r.returncode!=0 and 'Assertion' in text,text[-3000:]
        else:assert r.returncode==0 and 'PASS098' in text,text[-3000:]
        cases.append(dict(scenario=sc,exit=r.returncode,log_sha256=sha(log),last=text.strip().splitlines()[-1]))
    result=dict(baseline=a.baseline,mutation=a.mutation,geometry96=a.geometry96,inputs=sources,cases=cases,physical=False,installable=False,files={f.relative_to(o).as_posix():sha(f) for f in o.rglob('*') if f.is_file()})
    write('result.json',json.dumps(result,indent=2)+'\n');print('PASS098 cases='+str(len(cases)))
if __name__=='__main__':main()
