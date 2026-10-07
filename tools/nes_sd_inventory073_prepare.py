# SPDX-License-Identifier: MIT
"""Separate073 inventory retry: old072 inputs and frozen archives untouched."""
from pathlib import Path
import argparse,json,shutil
from nes_sd_inventory_prepare import prepare,digest,ROOT
def prepare073(source,evidence,out):
    old=prepare(source,evidence,out)
    mapping={'nes_sd_inventory073.c':'nes_sd_inventory.c','nes_sd_inventory_log073.c':'nes_sd_inventory_log.c','nes_sd_inventory_platform073.c':'nes_sd_inventory_platform.c','nes_sd_inventory_log073.h':'nes_sd_inventory_log073.h'}
    for public,actual in mapping.items():shutil.copy2(ROOT/'src/nes/firmware'/public,out/'src'/actual)
    (out/'src/VERSION').write_bytes(b'RELEASE_VERSION = "SDINFO073-BASE069"\r\n')
    pins=json.loads((ROOT/'analysis/sd-write-recovery-inputs.json').read_bytes())
    for n,h in pins.items():assert digest(out/'src'/n)==h,n
    record=dict(candidate='SDINFO073',baseline_manifest_sha256=old['baseline_manifest_sha256'],pinned069=old['pinned069'],new_mapping=mapping,
                unchanged_platform_inputs=pins,physical_SD=False,
                fresh073_copy={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()})
    (out.parent/'preparation-073.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');return record
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mcu-root',type=Path,required=True);p.add_argument('--mcu-evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=prepare073(a.mcu_root,a.mcu_evidence,a.out);print('PASS073 prepared baseline069275 + actual072 platform11; separate source only')
