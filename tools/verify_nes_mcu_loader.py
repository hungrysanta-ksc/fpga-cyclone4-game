# SPDX-License-Identifier: MIT
"""Audit archived056 host, GPIO replay and full ARM link; does not run hardware."""
from pathlib import Path
import argparse
import hashlib
import json
import re
from nes_mcu_loader import ROOT, source


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def audit(evidence):
    host, wave, arm = [evidence / name for name in ['host', 'wave', 'arm']]
    h = json.loads((host / 'result.json').read_text())
    w = json.loads((wave / 'result.json').read_text())
    a = json.loads((arm / 'result.json').read_text())
    assert h['host_model_pass'] and w['rtl_replay'] and a['full_link']
    assert w['host_result_sha256'] == sha(host / 'result.json')
    for folder, result in [(host, h), (wave, w), (arm, a)]:
        assert result['candidate'] == 'NES-MCU-LOADER-056'
        for name, digest in result['files'].items():
            assert sha(folder / name) == digest, (folder, name)
    assert (host / 'nes_h1_stm32.c').read_text() == source()
    assert (arm / 'nes_h1_stm32.c').read_bytes() == (host / 'nes_h1_stm32.c').read_bytes()
    for name in ['nes_rom_spi.c', 'nes_rom_spi.h', 'nes_mcu_loader.h']:
        assert sha(host / name) == sha(ROOT / 'src/nes/firmware' / name)
        assert sha(arm / name) == sha(host / name)
    for folder, result in [(host, h), (wave, w)]:
        assert sha(folder / 'waveform.txt') == result['waveform_sha256']
        assert sha(folder / 'executed-driver.py') == result['driver_sha256']
    assert h['waveform_sha256'] == w['waveform_sha256']
    log = (host / 'host.log').read_text()
    assert h['marker'] in log and log.count('PASS lifecycle ') == 27
    assert 'lifecycle=26 header_rejections=18 no_start=1 no_sd_writes=1' in log
    log = (wave / 'vsim.log').read_text()
    assert w['marker'] in log
    assert 'samples=33184 checked=29024 pin_bytes=256' in w['marker']
    for name in ['vlog.log', 'vsim.log']:
        assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)', (wave / name).read_text())
    assert re.search(r'\bT nes_mcu_load_probe$', (arm / 'symbols.txt').read_text(), re.M)
    assert 'PASS: compile-only NES056 firmware' in (arm / 'build.log').read_text()
    assert 'Legacy queryf0 got00 expecteda5' in (evidence / 'wave-idle-failed/vsim.log').read_text()
    protected = {}
    for name in ['source-manifest.json', 'cores/nes/publication-sources.json']:
        entries = json.loads((ROOT / name).read_text())['files']
        for e in entries:
            assert sha(ROOT / e['path']) == e['sha256'], e['path']
        protected[name] = len(entries)
    return dict(candidate='NES-MCU-LOADER-056', passed=True, lifecycle_cases=26,
                header_rejections=18, waveform_samples=33184, response_bits=29024,
                pin_bytes=256, full_arm_link=True, protected=protected,
                no_start=True, hardware_image=False, actual_stm32_execution=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(audit(args.evidence), indent=2))
