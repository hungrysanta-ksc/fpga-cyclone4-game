# SPDX-License-Identifier: MIT
"""Verify private frozen079 evidence and public pins without rebuilding."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();e=a.evidence
    m=json.loads((ROOT/'analysis/report-checkpoint079-verification.json').read_bytes())
    assert sha(e/'manifest.json')==m['manifest_sha256']
    files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['files']
    for n,h in files.items():assert sha(e/n)==h,n
    for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
    for mode in ['normal','no-compare','no-reset','no-budget']:
        d=e/'work'/(mode+'-06');r=json.loads((d/'result.json').read_bytes())
        assert r['mode']==mode and not r['physical'] and not r['arm_executed']
        assert r['checks']==(185 if mode=='normal' else None)
        assert r['timer_checks']==(5 if mode=='normal' else None)
        assert r['exit']==(0 if mode=='normal' else 3)
        for n,h in r['executed_files'].items():assert sha(d/n)==h,(mode,n)
        assert sha(d/'executed-driver.py')==m['public_sources']['tools/test_nes_report_checkpoint079.py']
        if mode=='normal':assert sha(d/'nes_report_checkpoint079.c')==m['public_sources']['src/nes/firmware/nes_report_checkpoint079.c']
    arm=e/'work/arm-03';c=json.loads((arm/'arm-check079.json').read_bytes());s=arm/'source/src'
    assert c['edges']['write_report -> sdinv_checkpoint079']==7
    assert sha(s/'obj-report079/firmware.stm')==c['firmware_sha256']==m['firmware_sha256']
    assert sha(s/'obj-report079/sd2snes.elf')==c['elf_sha256']
    assert not c['installable'] and not c['arm_executed']
    for n in ['nes_report_checkpoint079.c','nes_report_checkpoint079.h','nes_report_platform079.c']:
        assert sha(s/n)==m['public_sources']['src/nes/firmware/'+n],n
    assert sha(arm/'source/verilog/sd2snes_mini/fpga_mini.bi3')==c['mini_sha256']
    prep=json.loads((arm/'preparation079.json').read_bytes())
    for n in prep['unchanged_native']:assert sha(s/n)==prep['inputs']['077/arm/source/src/'+n],n
    print('PASS079 frozen evidence; report185/timer5/causal3/ARM7 checkpoints; compile-only, no physical result')
if __name__=='__main__':main()
