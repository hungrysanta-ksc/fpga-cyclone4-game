# SPDX-License-Identifier: MIT
"""Audit058 saved evidence. Requires private raw folders; does not run tests."""
from pathlib import Path
import argparse,json,re,tempfile
from nes_rom_readback import ROOT,materialize
from nes_spi_boot import sha,put


def verify(evidence):
    result=dict(candidate='NES-READBACK-PORT-058',date_kst='2026-10-07',passed=False,
                hardware_image=False,full_core_execution=False,spi_mcu_connected=False,integrity_gate=False)
    records={}
    for mode in ['unit','diff','mutation','fit']:
        folder=evidence/mode
        r=json.loads((folder/'result.json').read_text())
        assert r['candidate']==result['candidate'] and r['passed'] and r['mode']==mode
        for name,digest in r['sources'].items():assert sha(folder/name)==digest,name
        assert sha(folder/'nes_rom_readback.py')==r['generator_sha256']
        assert sha(folder/'nes_rom_readback_checks.py')==r['driver_sha256']
        if mode in ['unit','diff']:
            for name in ['vlib','vlog','vsim']:
                log=(folder/(name+'.log')).read_text(errors='replace')
                assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
            assert r['marker'] in log and 'Errors: 0, Warnings: 0' in log
        elif mode=='mutation':
            assert len(r['negative_controls'])==3
            for c in r['negative_controls']:
                sub=folder/c['mutation']
                for name,digest in c['sources'].items():assert sha(sub/name)==digest
                log=(sub/'vsim.log').read_text(errors='replace')
                assert log.count('** Fatal:')==1 and c['expected_failure'] in log
                assert 'returned accepted address tag' in c['expected_failure']
                assert not c['incorrect_design_passed'] and 'PASS READBACK PORT' not in log
        else:
            log=(folder/'output_files/live.fit.rpt').read_text(errors='replace')
            assert 'Fitter Status : Successful' in r['fit_summary']
            for pattern in [r'Total LABs:.*?;\s*949 / 963',r'M9Ks\s*;\s*26 / 56']:
                assert re.search(pattern,log),pattern
            assert '13,946 / 15,408' in r['fit_summary'] and 'Total registers : 5160' in r['fit_summary']
        records[mode]=r
    with tempfile.TemporaryDirectory(prefix='nes058-audit-') as tmp:
        out=Path(tmp);materialize(out)
        for name in ['nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv']:
            assert sha(out/name)==records['unit']['sources'][name]==records['fit']['sources'][name]
        assert sha(out/'nes_spi_boot.sv')==records['fit']['sources']['nes_spi_boot.sv']
        assert sha(out/'nes_rom_physical.sv')==records['diff']['sources']['nes_rom_physical.sv']
    expected='checks=1919161 pin_written_bytes=835585 checked_reads=180238 run_reads=1024 cancellations=10 rejected=10 corruptions_detected=4'
    assert expected in records['unit']['marker']
    assert 'comparisons=161207 requests=4096 replies=4053 cancellations=43' in records['diff']['marker']
    for manifest in ['source-manifest.json','cores/nes/publication-sources.json']:
        for entry in json.loads((ROOT/manifest).read_text())['files']:
            assert sha(ROOT/entry['path'])==entry['sha256'],entry['path']
    result.update(passed=True,unit=records['unit']['marker'],differential=records['diff']['marker'],
                  joint_fit=dict(LE=13946,LAB=949,total_LAB=963,remaining_LAB=14,registers=5160,M9K=26,virtual_pins=335,physical_unlocated_pins=22,PLL=0),
                  protected_files=dict(GBC=152,original_NES=334),runs=records)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=verify(a.evidence);put(a.out,json.dumps(r,indent=2)+'\n')
    print('PASS058 saved evidence: unit, RUN differential, 3 expected failures, joint949LAB; GBC152/NES334 preserved')


if __name__=='__main__':main()
