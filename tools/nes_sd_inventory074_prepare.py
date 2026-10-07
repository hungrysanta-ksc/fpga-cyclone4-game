# SPDX-License-Identifier: MIT
"""Observe the 073 blank-screen fault; no speculative SD-driver fix."""
from pathlib import Path
import argparse,json,shutil
from nes_sd_inventory073_prepare import prepare073,digest,ROOT

def replace(s,old,new):
    assert s.count(old)==1,old
    return s.replace(old,new,1)

def prepare074(source,evidence,out):
    old=prepare073(source,evidence,out)
    src=out/'src'
    p=src/'nes_sd_inventory.c'
    s=p.read_text();assert '073' in s;p.write_text(s.replace('073','074'),encoding='utf-8',newline='\n')
    p=src/'nes_sd_inventory_log.c';s=p.read_text()
    s=replace(s,'#include "nes_menu_return.h"','#include "nes_menu_return.h"\n#include "nes_sd_fault074.h"')
    s=replace(s,'/HW004%03u.TXT','/HW005%03u.TXT')
    for oldtext,newtext in [
        (' for(slot=0;',' sdinv_fault_stage(2);\n for(slot=0;'),
        (' for(unsigned pos=0;pos<len;){',' sdinv_fault_stage(3);\n for(unsigned pos=0;pos<len;){'),
        (' if(!result){if(!allowed())',' if(!result){sdinv_fault_stage(4);if(!allowed())'),
        (' if(!allowed())return 8;\n FRESULT r=f_close',' sdinv_fault_stage(5);\n if(!allowed())return 8;\n FRESULT r=f_close'),
        (' if(result)return result;',' if(result)return result;\n sdinv_fault_stage(6);'),
        (' uint8_t data[256];',' sdinv_fault_stage(7);\n uint8_t data[256];'),
        (' if(!allowed())return 8;\n r=f_close',' sdinv_fault_stage(8);\n if(!allowed())return 8;\n r=f_close')]:s=replace(s,oldtext,newtext)
    p.write_text(s,encoding='utf-8',newline='\n')
    p=src/'nes_sd_inventory_platform.c';s=p.read_text().replace('SDINFO073','SDINFO074')
    s=replace(s,'#include "nes_sd_inventory_log073.h"','#include "nes_sd_inventory_log073.h"\n#include "nes_sd_fault074.h"')
    s=replace(s,' nes_diag_begin();nes_return_io_begin();',' sdinv_fault_stage(1);nes_diag_begin();nes_return_io_begin();')
    s=replace(s,' snes_bootprint_center(8,result?',' sdinv_fault_stage(9);\n snes_bootprint_center(8,result?')
    p.write_text(s,encoding='utf-8',newline='\n')
    shutil.copy2(ROOT/'src/nes/firmware/nes_sd_fault074.c',src/'nes_diag_platform.c')
    shutil.copy2(ROOT/'src/nes/firmware/nes_sd_fault074.h',src/'nes_sd_fault074.h')
    (src/'VERSION').write_bytes(b'RELEASE_VERSION = "SDINFO074-BASE069"\r\n')
    pins=json.loads((ROOT/'analysis/sd-write-recovery-inputs.json').read_bytes())
    for n,h in pins.items():assert digest(src/n)==h,n
    record=dict(candidate='SDINFO074',unchanged_platform_inputs=pins,physical_SD=False,
                root_cause_fixed=False,source_files={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()})
    (out.parent/'preparation-074.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return record
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mcu-root',type=Path,required=True);p.add_argument('--mcu-evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    prepare074(a.mcu_root,a.mcu_evidence,a.out);print('PASS074 prepared; native SD/FatFS guards unchanged; LED observation only')
