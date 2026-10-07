# SPDX-License-Identifier: MIT
"""Validate frozen081 executed inputs/results without rerunning experiments."""
from pathlib import Path
import argparse,json
from nes_report081_prepare import sha,ROOT
def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
    meta=json.loads((ROOT/'analysis/report-init081-verification.json').read_bytes())
    assert sha(e/'manifest.json')==meta['manifest_sha256']
    files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==meta['files']
    for n,h in files.items():assert sha(e/n)==h,n
    for n,h in meta['public_sources'].items():assert sha(ROOT/n)==h,n
    for mode in ['normal','no-crc','post-fault-clock']:
        d=e/'work'/(mode+'-06');r=json.loads((d/'result.json').read_bytes())
        assert r['mode']==mode and not r['physical'] and r['exit']==(0 if mode=='normal' else 3)
        for n,h in r['files'].items():assert sha(d/n)==h,(mode,n)
        assert sha(d/'host.c')==sha(ROOT/'tests/nes-functional/report_init081_host.c')
        assert sha(d/'executed-driver.py')==sha(ROOT/'tools/test_nes_report_init081.py')
        if mode=='normal':assert r['checks']==8558 and sha(d/'nes_report_init081.inc')==sha(ROOT/'src/nes/firmware/nes_report_init081.inc')
    arm=e/'work/arm-02';s=arm/'source/src';c=json.loads((arm/'arm-check081.json').read_bytes())
    assert not c['installable'] and not c['arm_executed'] and c['native_original_prefix_preserved']
    assert sha(s/'obj-report079/firmware.stm')==c['firmware_sha256']==meta['firmware_sha256']
    assert sha(s/'obj-report079/sd2snes.elf')==c['elf_sha256']
    assert c['edges']['disk_initialize -> sdn_report_mounted081']==1
    assert sha(s/'stm32f4xx/nes_report_init081.inc')==sha(ROOT/'src/nes/firmware/nes_report_init081.inc')
    print('PASS081 frozen8558/causal2/ARM; GPIO init + actual FatFS mount with modeled VBR, not full native platform or physical')
if __name__=='__main__':main()
