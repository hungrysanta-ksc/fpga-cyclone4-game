# SPDX-License-Identifier: MIT
"""Single083 pre-SD observation plus actual081 native/FatFS report session.

Only hardware pins, card storage, CRC assembly primitives and elapsed time are
modeled. Inputs are copied from the immutable final081 ARM source inventory.
No firmware installation or physical timing claim follows from this test.
"""
from pathlib import Path
import argparse, hashlib, json, re, shutil, subprocess
from nes_diag_recovery_checks import function
ROOT = Path(__file__).resolve().parents[1]
PIN = '4e74c45d85315546c7d61c7f613ed4386283eb24c05c5724b506358e3381b757'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def replace(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new)

def main():
    p = argparse.ArgumentParser()
    for n in ['evidence081', 'gcc', 'out']: p.add_argument('--'+n, type=Path, required=True)
    p.add_argument('--mode', choices=['normal','no-readback-compare','no-reset-rehold','no-early-marker','no-marker-rehold'], default='normal')
    a=p.parse_args(); o=a.out.resolve(); o.mkdir(parents=True,exist_ok=False)
    e=a.evidence081.resolve(); assert sha(e/'manifest.json')==PIN
    pins=json.loads((e/'manifest.json').read_bytes())['files']; inputs={}
    def copy(n, target=None):
        k='work/arm-02/source/src/'+n; assert sha(e/k)==pins[k], k
        inputs[k]=pins[k]; d=o/(target or n); d.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(e/k,d); return d
    names=['ff.c','ff.h','ffconf.h','integer.h','diskio.h','nes_diag_runtime.c',
           'nes_diag_runtime.h','nes_menu_return.c','nes_menu_return.h','nes_menu076.h','smc.h',
           'nes_sd_inventory.h','nes_sd_inventory_log.c','nes_sd_inventory_log073.h','nes_sd_fault074.h',
           'nes_report_checkpoint079.c','nes_report_checkpoint079.h','nes_report_boot080.c',
           'nes_report_boot080.h','nes_report_decode080.c','nes_report_platform081.c',
           'nes_report_disk081.c','rle.c','rle.h','snesboot.h']
    for n in names: copy(n)
    copy('ccsbcs.c','unicode/ccsbcs.c'); copy('obj-report079/cfgware.h','cfgware.h')
    copy('stm32f4xx/nes_report_init081.inc','nes_report_init081.inc')
    raw=copy('stm32f4xx/sdnative.c','input-sdnative.c').read_text()
    functions=['nes_diag_sd_error','nes_diag_sd_reset','nes_diag_sd_failed','getbits','sdn_status',
               'wiggle_fast_pos','wiggle_fast_neg','wiggle_fast_neg1','wiggle_fast_pos1',
               'get_and_check_datacrc','wait_busy','send_command_fast','make_crc7','cmd_fast',
               'send_datablock','nes_diag_sd_response','nes_diag_sd_read','sdn_read',
               'nes_return_sd_write','sdn_write','sdn_ioctl']
    bodies=[]
    for n in functions:
        m=re.search(r'^(?:static inline void|static void|static bool|static uint32_t|static DRESULT|int|void|bool|DRESULT|DSTATUS) '+n+r'\([^;{}]*\)\s*\{',raw,re.M)
        assert m,n; bodies.append(function(raw[m.start():],n))
    (o/'native.inc').write_text(''.join(bodies),encoding='utf-8')
    raw=copy('fileops.c','input-fileops.c').read_text()
    (o/'file-init.inc').write_text(function(raw[raw.index('void file_init() {'):],'file_init'),encoding='utf-8')
    f=o/'nes_menu_return.c'; s=f.read_text(); f.write_text(s[:s.index('uint32_t nes_return_copy_menu(')],encoding='utf-8')
    inputs['public/src/nes/firmware/nes_report_platform083.c']=sha(ROOT/'src/nes/firmware/nes_report_platform083.c')
    shutil.copy2(ROOT/'src/nes/firmware/nes_report_platform083.c',o/'nes_report_platform083.c')
    f=o/'nes_sd_inventory_log.c'; f.write_text(replace(f.read_text(),'/HW081','/HW083'),encoding='utf-8',newline='\n')
    if a.mode=='no-readback-compare':
        f=o/'nes_sd_inventory_log.c'; s=f.read_text()
        s=replace(s,'memcmp(data,report+pos,n)','0 /* causal mutation */'); f.write_text(s,encoding='utf-8')
    if a.mode=='no-reset-rehold':
        f=o/'nes_report_checkpoint079.c'; s=f.read_text()
        s=replace(s,' snes_reset(1);\n if(!get_snes_reset()',' /* causal mutation */\n if(!get_snes_reset()'); f.write_text(s,encoding='utf-8')
    if a.mode=='no-early-marker':
        f=o/'nes_report_platform083.c'; s=f.read_text(); s=replace(s,'!marker083("STEP 1A INIT SD")','false'); f.write_text(s,encoding='utf-8')
    if a.mode=='no-marker-rehold':
        f=o/'nes_report_platform083.c'; s=f.read_text(); s=replace(s,' snes_reset(1);\n if(!get_snes_reset()', ' /* causal mutation */\n if(!get_snes_reset()'); f.write_text(s,encoding='utf-8')
    # Retain the already-reviewed model algorithms, recording their exact input
    # hashes and each generated translation unit. No old archive is edited.
    def public(n):
        q=ROOT/n; inputs['public/'+n]=sha(q); return q.read_text()
    host=public('tests/nes-functional/report_session078_host.c')
    host=host[:host.index('static void reset_case(unsigned fat32){')]
    host=host.replace('static FATFS fs;','FATFS fatfs;\nint file_res,newcard;\nuint8_t file_path[256];')
    for n in ['sdn_status','sram_writeblock','sram_readblock','nes_menu_crc076']:
        host=re.sub(r'^.*? '+n+r'\([^\n]*\n','',host,flags=re.M)
    host=host.replace('static int during_blocktrans;','int during_blocktrans;')
    host=replace(host,'uint32_t nes_diag_ticks(void){return tick_origin+(tick_div?rises/tick_div:0);}',
                 '#include "platform-model.h"\nuint32_t nes_diag_ticks(void){return tick_origin+display_ticks+(tick_div?rises/tick_div:0);}')
    host=host.replace('n>=2&&n<=8','n>=1&&n<=9')
    host=replace(host,' assert(cmd_bits==48);',' assert(held&&!nvic.ISER[2]&&init_commands==17&&stage>=1);\n assert(cmd_bits==48);')
    host=replace(host,'assert(ccs||!(address&511));cmd_sector=ccs?address:address/512;',
                 'assert(ccs==high_capacity);assert(high_capacity||!(address&511));cmd_sector=high_capacity?address:address/512;')
    host=replace(host,'#define SD_CLKREG 0','#include "init-model.h"\n#define SD_CLKREG 0')
    host=host.replace('#define SET_BIT(r,p) set_pin(p,1)','#define SET_BIT(r,p) dispatch_set(p,1)')
    host=host.replace('#define CLEAR_BIT(r,p) set_pin(p,0)','#define CLEAR_BIT(r,p) dispatch_set(p,0)')
    host=host.replace('#define BITBAND(r,p) input(p)','#undef BITBAND\n#define BITBAND(r,p) dispatch_input(p)')
    host=host.replace('#define GPIO_MODE_IN(r,p) mode_in(p)','#define GPIO_MODE_IN(r,p) dispatch_mode(p,0)')
    host=host.replace('#define GPIO_MODE_OUT(r,p) mode_out(p)','#define GPIO_MODE_OUT(r,p) dispatch_mode(p,1)')
    host=host.replace('#define OUT_BIT(r,p,n) set_pin(p,n)','#define OUT_BIT(r,p,n) dispatch_set(p,n)')
    host=replace(host,'#include "native.inc"','#include "native.inc"\n#include "nes_report_init081.inc"\n#include "file-init.inc"')
    host=replace(host,'DSTATUS disk_initialize(BYTE d){assert(!d);return 0;}','/* Actual strong081 disk_initialize is linked separately. */')
    host=replace(host,'DSTATUS disk_status(BYTE d){assert(!d);return 0;}','DSTATUS disk_status(BYTE d){return sdn_status(d);}')
    (o/'host.c').write_text(host+'\n#include "session-tests.h"\n',encoding='utf-8')
    # Slow command card model from081, now followed by actual native CMD17/24.
    slow=public('tests/nes-functional/report_init081_host.c')
    slow=slow[slow.index('static void set_bits('):slow.index('/* Actual legacy initializer')]
    renames=['response','response_pos','response_len','wire','cmd_bits','command','commands',
             'busy_clocks','clk','set_pin','mode_pin','read_pin']
    for n in renames: slow=re.sub(r'\b'+n+r'\b','init_'+n,slow)
    slow=replace(slow,'case 16:assert(arg==512);init_response[3]=9;break;',
                 'case 16:assert(arg==512);init_response[3]=9;init_complete=1;break;')
    # Capacity is modeled as 4M sectors for SDHC and 2M for SDSC; only a sparse
    # prepared FAT partition (8192/70000 sectors) is accessed in these cases.
    (o/'slow-model.inc').write_text(slow,encoding='utf-8')
    for n in ['platform-model.h','init-model.h','session-tests.h']:
        s=public('tests/nes-functional/report_session083_'+n); (o/n).write_text(s,encoding='utf-8')
    # Same hardware seams as080, while file_init and all disk calls are real.
    old=public('tools/test_nes_report_boot080.py')
    h=old[old.index(' headers={')+1:old.index('\n for n,s in headers.items()')]
    ns={}; exec(h,{},ns); headers=ns['headers']
    headers['fileops.h']='#pragma once\n#include "ff.h"\nextern int file_res,file_status;\nvoid file_init(void);\nuint8_t file_getc(void);\n'
    headers['uart.h']='#include <stdio.h>\n'
    for n,s in headers.items(): (o/n).write_text(s,encoding='utf-8')
    shutil.copy2(__file__,o/'executed-driver.py')
    cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-format','-I.','host.c','ff.c',
         'unicode/ccsbcs.c','rle.c','nes_diag_runtime.c','nes_menu_return.c',
         'nes_sd_inventory_log.c','nes_report_checkpoint079.c','nes_report_disk081.c',
         'nes_report_boot080.c','nes_report_decode080.c','nes_report_platform083.c','-o','host.exe']
    with (o/'compile.log').open('wb') as f: subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT,check=True)
    with (o/'run.log').open('wb') as f: r=subprocess.run([str(o/'host.exe')],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
    log=(o/'run.log').read_text(errors='replace')
    if a.mode=='normal': assert r.returncode==0 and 'PASS083' in log,log[-2000:]
    else:
        needle={'no-readback-compare':'TXT SAVE FAILED','no-reset-rehold':'report_session083()','no-early-marker':'marker_mask==(init_complete?3u:1u)','no-marker-rehold':'report_session083()'}[a.mode]
        assert r.returncode!=0 and 'Assertion' in log and needle in log,log[-2000:]
    if a.mode=='normal':
        timer=copy('stm32f4xx/timer.c','input-timer.c').read_text()
        at=timer.index('bool nes_return_delay(unsigned time,bool milliseconds) {')
        (o/'timer.inc').write_text(function(timer[at:],'nes_return_delay'),encoding='utf-8')
        (o/'timer-host.c').write_text(public('tests/nes-functional/report_timer083_host.c'),encoding='utf-8')
        cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I.','timer-host.c','nes_diag_runtime.c','nes_menu_return.c','-o','timer.exe']
        with (o/'timer-compile.log').open('wb') as f:subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT,check=True)
        with (o/'timer.log').open('wb') as f:subprocess.run([str(o/'timer.exe')],cwd=o,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=30)
        assert 'PASS083 TIMER checks=5' in (o/'timer.log').read_text()
    result=dict(mode=a.mode,exit=r.returncode,inputs=inputs,physical=False,production_changed=True,
                files={f.relative_to(o).as_posix():sha(f) for f in o.rglob('*') if f.is_file()})
    (o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(log[-2000:])

if __name__=='__main__':main()
