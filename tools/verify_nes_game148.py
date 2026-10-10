# SPDX-License-Identifier: MIT
"""Verify the preserved actual-ROM result and unchanged147 service/reader."""
from pathlib import Path
import argparse, json
from nes_game147 import ROOT, sha

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path, required=True)
    a = p.parse_args()
    m = json.loads((ROOT/'analysis/game148-verification.json').read_bytes())
    e = a.baseline/'nes-game148/evidence'
    assert sha(e/'manifest.json') == m['manifest_sha256']
    files = json.loads((e/'manifest.json').read_bytes())['files']
    assert len(files) == m['file_count']
    for n, h in files.items():
        assert sha(e/n) == h, n
    for n, h in m['public_sources'].items():
        assert sha(ROOT/n) == h, n
    result = json.loads((e/'core03/result.json').read_bytes())
    log = (e/'core03/simulation.log').read_text()
    assert result['sources'] == m['executed_sources']
    assert result['passed'] == m['core_passed']
    if result['passed']:
        assert result['frames'] == 30 and 'PASS GAME147 frames=30 ' in log
        assert '** Fatal:' not in log
    else:
        assert '** Fatal:' in log and 'PASS GAME147 frames=30 ' not in log
    old = json.loads((a.baseline/'nes-game147/evidence/core03/result.json').read_bytes())
    for n in ['nes_rom_service.sv', 'nes_rom_physical.sv', 'nes_rom_loader.sv',
              'nes_rom_boot.sv', 'nes_rom_spi.sv', 'nes_spi_boot.sv']:
        assert result['sources'][n] == old['sources'][n], n
    assert not m['physical_test'] and not m['sd_package']
    print('PASS148 evidence integrity; actual-ROM outcome preserved; no hardware/package claim')

if __name__ == '__main__':
    main()
