# SPDX-License-Identifier: MIT
"""Pinned077 + report074 + pre-operation079, compile-only separate candidate."""
from pathlib import Path
import argparse, hashlib, json, shutil
ROOT=Path(__file__).resolve().parents[1]
PINS={'074':'2be1006b6365414d2246e1dc38655126e3f2b00405871422f1f7a9626d37165b',
      '077':'8b4b5a9385dd7ced9a46b725d9e3a71f6877734b07febe3f0ec560f30842720c'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def writer079(s):
    assert s.count('sdinv_fault_stage(')==7 and s.count('/HW005')==1
    return s.replace('#include "nes_sd_fault074.h"','#include "nes_report_checkpoint079.h"').replace('sdinv_fault_stage(', 'sdinv_checkpoint079(').replace('/HW005','/HW079')
def main():
    p=argparse.ArgumentParser()
    for n in ['evidence074','evidence077','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();assert not out.exists()
    sources={}
    for v in PINS:
        e=getattr(a,'evidence'+v).resolve()
        assert not out.is_relative_to(e) and sha(e/'manifest.json')==PINS[v]
        sources[v]=(e,json.loads((e/'manifest.json').read_bytes())['files'])
    used={}
    def copy(v,key,dest):
        e,m=sources[v];assert sha(e/key)==m[key],key
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/key,dest);used[v+'/'+key]=m[key]
    # Copy ONLY manifest-listed source/build inputs; exclude all old outputs.
    for key in sources['077'][1]:
        if not key.startswith('arm/source/'):continue
        n=Path(key.removeprefix('arm/source/'))
        if any(x.startswith(('obj-','.dep-')) or x in ['db','incremental_db','output_files','__pycache__'] for x in n.parts):continue
        if n.suffix.lower() in ['.exe','.elf','.stm','.sof','.rbf','.pyc','.o','.d','.map','.lst']:continue
        copy('077',key,out/n)
    src=out/'src'
    for n in ['nes_sd_inventory.h','nes_sd_inventory_log.c','nes_sd_inventory_log073.h','nes_sd_fault074.h','nes_diag_platform.c']:
        copy('074','arm/source/src/'+n,src/n)
    for n in ['nes_report_checkpoint079.c','nes_report_checkpoint079.h','nes_report_platform079.c']:
        shutil.copy2(ROOT/'src/nes/firmware'/n,src/n)
    f=src/'nes_sd_inventory_log.c';f.write_text(writer079(f.read_text()),encoding='utf-8',newline='\n')
    f=src/'main.c';s=f.read_text();needle='  fpga_init();\n  firstboot = 1;';assert s.count(needle)==1
    s=s.replace(needle,'  fpga_init();\n  sdreport_run079();\n  firstboot = 1;')
    s='void sdreport_run079(void) __attribute__((noreturn));\n'+s
    f.write_text(s,encoding='utf-8',newline='\n')
    f=src/'Makefile';s=f.read_text();needle='SRC  = main.c ff.c ccsbcs.c';assert s.count(needle)==1
    f.write_text(s.replace(needle,needle+'\nSRC += nes_sd_inventory_log.c nes_report_checkpoint079.c nes_report_platform079.c'),encoding='utf-8',newline='\n')
    (src/'VERSION').write_bytes(b'RELEASE_VERSION = "SDREPORT079"\r\n')
    unchanged=['ff.c','stm32f4xx/sdnative.c','stm32f4xx/timer.c','fpga_spi.c','memory.c','nes_menu_return.c','nes_diag_runtime.c','snes.c']
    for n in unchanged:assert sha(src/n)==sources['077'][1]['arm/source/src/'+n]
    record=dict(inputs=used,unchanged_native=unchanged,installable=False,files={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()})
    (out.parent/'preparation079.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print('Prepared compile-only079 inputs='+str(len(used)))
if __name__=='__main__':main()
