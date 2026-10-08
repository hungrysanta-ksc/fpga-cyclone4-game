# SPDX-License-Identifier: MIT
"""Verify immutable082 host evidence and its unchanged081 ARM inputs."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--evidence081',type=Path,required=True)
    a=p.parse_args();e=a.evidence;old=a.evidence081
    meta=json.loads((ROOT/'analysis/report-session082-verification.json').read_bytes())
    assert sha(e/'manifest.json')==meta['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files'];assert len(pins)==meta['files']
    for n,h in pins.items():assert sha(e/n)==h,n
    for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
    assert sha(old/'manifest.json')==meta['input081_manifest_sha256']
    oldpins=json.loads((old/'manifest.json').read_bytes())['files']
    modes=['normal','no-readback-compare','no-reset-rehold']
    for mode in modes:
        d=e/'work'/(mode+'-04');r=json.loads((d/'result.json').read_bytes())
        assert r['mode']==mode and r['exit']==(0 if mode=='normal' else 3)
        assert not r['physical'] and not r['production_changed']
        for n,h in r['files'].items():assert sha(d/n)==h,(mode,n)
        for n,h in r['inputs'].items():
            if n.startswith('public/'):assert sha(ROOT/n[7:])==h,n
            else:assert h==oldpins[n] and sha(old/n)==h,n
        assert sha(d/'executed-driver.py')==sha(ROOT/'tools/test_nes_report_session082.py')
    d=e/'work/normal-04';r=json.loads((d/'result.json').read_bytes())
    # Runtime bodies, writer, strong disk bridge and checkpoint are the exact
    # final081 ARM source bytes. Only unrelated menu-copy code is omitted.
    for n in ['ff.c','nes_diag_runtime.c','nes_sd_inventory_log.c','nes_report_disk081.c',
              'nes_report_checkpoint079.c','nes_report_boot080.c','nes_report_decode080.c',
              'nes_report_platform081.c']:
        assert sha(d/n)==oldpins['work/arm-02/source/src/'+n],n
    assert sha(d/'nes_report_init081.inc')==oldpins['work/arm-02/source/src/stm32f4xx/nes_report_init081.inc']
    assert 'PASS082 checks=667 physical=0 production_changed=0' in (d/'run.log').read_text()
    arm=old/'work/arm-02/source/src/obj-report079/firmware.stm'
    assert sha(arm)==meta['firmware_sha256'] and arm.stat().st_size==132320
    assert meta['checks']==667 and meta['causal_controls']==2 and not meta['installable']
    print('PASS082 667 combined init/native/FatFS/mini/writer/terminal +2 causal; unchanged081 ARM; physical=0 installable=0')
if __name__=='__main__':main()
