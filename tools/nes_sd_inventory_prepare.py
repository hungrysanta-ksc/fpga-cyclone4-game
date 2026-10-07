# SPDX-License-Identifier: MIT
"""Prepare a separate SDINFO072 source tree from supplied private069 inputs."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
BASE_MANIFEST='b5d50d8a5f7590a43f33b8ebe4d5166ff2f2ae0ba9bbebf953984959d6d026ae'
NAMES=['nes_sd_inventory.h','nes_sd_inventory.c','nes_sd_inventory_log.c','nes_sd_inventory_platform.c']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare(source,evidence,out):
    source=source.resolve();evidence=evidence.resolve();out=out.resolve()
    assert not out.exists() and not out.is_relative_to(source) and not out.is_relative_to(evidence)
    raw=evidence/'manifest.json';assert digest(raw)==BASE_MANIFEST
    pinned={n[4:]:h for n,h in json.loads(raw.read_bytes())['files'].items() if n.startswith('arm/src/')}
    assert len(pinned)==275
    for n,h in pinned.items():assert digest(source/n)==h,n
    shutil.copytree(source,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.exe','*.elf','*.stm','*.sof','*.rbf','*.wlf','db','incremental_db','output_files'))
    for n in NAMES:shutil.copy2(ROOT/'src/nes/firmware'/n,out/'src'/n)
    p=out/'src/main.c';s=p.read_text();needle='  fpga_init();\n  firstboot = 1;';assert s.count(needle)==1
    s=s.replace('#include "nes_menu_return.h"','#include "nes_menu_return.h"\n#include "nes_sd_inventory.h"',1)
    s=s.replace(needle,'  fpga_init();\n  sdinv_run(); /* Dedicated SDINFO072; no menu/cfg/autoboot/core path. */\n  firstboot = 1;',1)
    p.write_text(s,encoding='utf-8',newline='\n')
    p=out/'src/Makefile';s=p.read_text();needle='SRC  = main.c ff.c ccsbcs.c';assert s.count(needle)==1
    p.write_text(s.replace(needle,needle+'\nSRC += nes_sd_inventory.c nes_sd_inventory_log.c nes_sd_inventory_platform.c',1),encoding='utf-8',newline='\n')
    (out/'src/VERSION').write_bytes(b'RELEASE_VERSION = "SDINFO072-BASE069"\r\n')
    # Config/Make/VERSION and other unarchived069 inputs are freshly pinned here;
    # the historical069 manifest proves only the 275 entries checked above.
    inventory={p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    record=dict(candidate='NES-SD-INSPECTION-072',baseline_manifest_sha256=BASE_MANIFEST,pinned069=pinned,fresh072_copy=inventory,
                changed=['src/main.c','src/Makefile','src/VERSION'],added=['src/'+n for n in NAMES],physical_SD=False)
    (out.parent/'preparation-072.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return record
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mcu-root',type=Path,required=True);p.add_argument('--mcu-evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=prepare(a.mcu_root,a.mcu_evidence,a.out);print('PASS072 pinned069='+str(len(r['pinned069']))+' fresh_copy='+str(len(r['fresh072_copy'])))
