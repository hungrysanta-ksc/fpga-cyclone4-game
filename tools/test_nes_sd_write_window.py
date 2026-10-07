# SPDX-License-Identifier: MIT
"""Whole pinned072 FatFS + actual native permission/runtime integration."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,re
from nes_diag_recovery_checks import function
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,out,name):
    with (out/(name+'.log')).open('wb') as f:r=subprocess.run([str(x) for x in cmd],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=60)
    if r.returncode:raise RuntimeError('Inspect raw '+str(out/(name+'.log')))
def main():
    p=argparse.ArgumentParser();p.add_argument('--platform',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);p.add_argument('--mutation',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);source=a.platform.resolve();out=a.out.resolve();fw=ROOT/'src/nes/firmware'
    pins=json.loads((ROOT/'analysis/sd-write-recovery-inputs.json').read_bytes())
    for n,h in pins.items():assert sha(source/n)==h,n
    for n in ['ff.c','ff.h','ffconf.h','integer.h','diskio.h','nes_menu_return.c','nes_menu_return.h','nes_diag_runtime.c','nes_diag_runtime.h']:shutil.copy2(source/n,out/n)
    (out/'unicode').mkdir();shutil.copy2(source/'ccsbcs.c',out/'unicode/ccsbcs.c')
    sd=(source/'stm32f4xx/sdnative.c').read_text();start=sd.index('static void nes_diag_sd_error(enum nes_diag_error error){')
    definitions=function(sd[start:],'nes_diag_sd_error')+''.join(function(sd,n) for n in ['nes_diag_sd_response','nes_return_sd_write'])
    (out/'sd-permission-functions.inc').write_text(definitions,encoding='utf-8',newline='\n')
    rejection='if(nes_diag_active()&&nes_return_failed())return RES_NOTRDY;';assert rejection in function(sd,'sdn_read')
    (out/'sd-read-rejection.inc').write_text(rejection+'\n',encoding='utf-8')
    (out/'config.h').write_text('/* host RAM/card model */\n#include <stdio.h>\n')
    (out/'uart.h').write_text('/* no actual UART */\n')
    (out/'fileops.h').write_text('#include "ff.h"\n')
    (out/'memory.h').write_text('#include <stdint.h>\nuint16_t sram_writeblock(void *,uint32_t,uint16_t);\nuint16_t sram_readblock(void *,uint32_t,uint16_t);\n')
    for n in ['nes_sd_inventory.h','nes_sd_inventory_log073.h','nes_sd_inventory_log073.c','nes_sd_inventory_log.c']:shutil.copy2(fw/n,out/n)
    shutil.copy2(ROOT/'tests/nes-functional/sd_inventory_window_host.c',out/'host.c');shutil.copy2(__file__,out/'executed-driver.py')
    if a.mutation:
        f=out/'nes_sd_inventory_log073.c';s=f.read_text();assert s.count(' nes_return_log_allow(true);')==1;f.write_text(s.replace(' nes_return_log_allow(true);',' /* mutation: write window omitted */'),encoding='utf-8',newline='\n')
    flags=['-std=c11','-O2','-Wall','-Wextra','-ffunction-sections','-fdata-sections','-D__USE_MINGW_ANSI_STDIO=1','-I.']
    run([a.gcc,*flags,'-Dsdinv_write_report=sdinv_write_report072','-c','nes_sd_inventory_log.c','-o','legacy.o'],out,'legacy-compile')
    run([a.gcc,*flags,'ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_sd_inventory_log073.c','host.c','legacy.o','-Wl,--gc-sections','-o','host.exe'],out,'integration-compile')
    with (out/'integration.log').open('wb') as f:r=subprocess.run([str(out/'host.exe')],stdout=f,stderr=subprocess.STDOUT,timeout=60)
    log=(out/'integration.log').read_text(errors='replace')
    if a.mutation:assert r.returncode!=0 and 'sdinv_write_report(data,sizeof(data),path,sizeof(path))==0' in log
    else:assert r.returncode==0 and 'REPRO072 FAT16 result=4' in log and 'REPRO072 FAT32 result=4' in log and 'PASS073 integration' in log
    result=dict(candidate='SDINFO073',mutation=a.mutation,exit=r.returncode,physical_SD=False,checks=None if a.mutation else int(re.search(r'integration checks=(\d+)',log)[1]),
                inputs=pins,executed_files={x.relative_to(out).as_posix():sha(x) for x in out.rglob('*') if x.is_file()})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print('PASS073 integration mutation='+str(a.mutation)+' checks='+str(result['checks']))
if __name__=='__main__':main()
