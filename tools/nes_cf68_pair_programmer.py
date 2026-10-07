# SPDX-License-Identifier: MIT
"""Snapshot exact069 runtime and included C programmer for host all-byte tests.
Requires an explicitly supplied frozen069 archive and compiler; no ARM rebuild.
"""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_cf68_pair_preflight import digest
ROOT=Path(__file__).resolve().parents[1]
MCU_MANIFEST='b5d50d8a5f7590a43f33b8ebe4d5166ff2f2ae0ba9bbebf953984959d6d026ae'
def snapshot(archive,out):
    raw=(archive/'manifest.json').read_bytes();assert digest(raw)==MCU_MANIFEST
    m=json.loads(raw)['files']
    names=['arm/src/fpga.c','arm/src/nes_diag_runtime.c','arm/src/nes_diag_runtime.h']
    for n in names:assert digest((archive/n).read_bytes())==m[n],n
    inc=(ROOT/'src/nes/firmware/nes_diag_fpga.inc').read_bytes().replace(b'\r\n',b'\n')
    assert inc in (archive/names[0]).read_bytes(),'Programmer body not in pinned069 ARM input'
    out.mkdir(exist_ok=False)
    for n in names:shutil.copy2(archive/n,out/Path(n).name)
    (out/'nes_diag_fpga.inc').write_bytes(inc)
    shutil.copy2(ROOT/'tests/nes-functional/cf68_pair_programmer_host.c',out/'host.c')
    return {p.name:digest(p.read_bytes()) for p in out.iterdir()}
def main():
    p=argparse.ArgumentParser();p.add_argument('--mcu-evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--gcc',type=Path,required=True);p.add_argument('--packed',type=Path,required=True);p.add_argument('--raw',type=Path,required=True)
    a=p.parse_args();sources=snapshot(a.mcu_evidence,a.out)
    phases=[('compile',[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),str(a.out/'host.c'),str(a.out/'nes_diag_runtime.c'),'-o',str(a.out/'host.exe')]),('programmer',[str((a.out/'host.exe').resolve()),str(a.packed.resolve()),str(a.raw.resolve())])]
    for phase,cmd in phases:
        with (a.out/(phase+'.log')).open('wb') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=60)
        text=(a.out/(phase+'.log')).read_text(errors='replace')
        if r.returncode or (phase=='programmer' and ('all_bytes=1' not in text or 'negative_controls=13' not in text)):
            raise ValueError('Inspect raw '+str(a.out/(phase+'.log')))
    (a.out/'result.json').write_text(json.dumps(dict(mcu_manifest_sha256=MCU_MANIFEST,sources=sources,packed_sha256=digest(a.packed.read_bytes()),raw_sha256=digest(a.raw.read_bytes()),raw_bytes=a.raw.stat().st_size,negative_controls=13,hardware_execution=False),indent=2)+'\n')
    print('PASS071 exact069 C programmer raw='+str(a.raw.stat().st_size)+' negatives=13')
if __name__=='__main__':main()
