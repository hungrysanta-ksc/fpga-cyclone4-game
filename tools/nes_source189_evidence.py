# SPDX-License-Identifier: MIT
"""Read-only cross-check of selected189 results and immutable prior archives."""
from pathlib import Path
import argparse, hashlib, json
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    selected = BASE/'probes/nes-source189/test02'
    result = json.loads((selected/'result.json').read_bytes())
    assert result['passed']
    for name, expected in result['source_pins'].items():
        path = BASE/name if name.startswith('probes/') else ROOT/name
        assert sha(path) == expected, name
    comparisons = []
    for name in ('patch0', 'maxgroups'):
        old = BASE/'probes/nes-packed181/evidence/test02'/name/'transactions.txt'
        payload = bytearray()
        for line in old.read_text().splitlines():
            count, tx, rx = line.split()
            if tx.startswith('d1'):
                raw = bytes.fromhex(rx)
                assert len(raw) == int(count)
                payload.extend(raw[1:-2])  # SPI dummy, then payload, then CRC16.
        actual = bytes(int(x, 16) for x in (selected/name/'read.hex').read_text().split())
        assert actual == payload, name
        comparisons.append(dict(name=name, bytes=len(actual),
            old_spi_transactions_sha256=sha(old), payload_sha256=hashlib.sha256(actual).hexdigest()))
    prior = []
    for name in ('nes-paired186', 'nes-game186-hardware01', 'nes-video-arch187', 'nes-bulk188'):
        folder = BASE/'probes'/name
        manifest = folder/'manifest01.json'
        entries = json.loads(manifest.read_bytes())
        for relative, expected in entries.items():
            assert sha(folder/relative) == expected, (name, relative)
        prior.append(dict(name=name, files=len(entries), manifest_sha256=sha(manifest)))
    regression = BASE/'probes/nes-source189/regression01/result.json'
    old = json.loads(regression.read_bytes())
    assert old['passed']
    assert old['source_pins']['src/nes/rtl/nes_bulk_aperture188.sv'] == sha(ROOT/'src/nes/rtl/nes_bulk_aperture188.sv')
    report = dict(passed=True, selected='test02', tests=result['cases'],
        source_pins=result['source_pins'], source_result_sha256=sha(selected/'result.json'),
        spi_payload_comparisons=comparisons, regression=old['cases'],
        regression_result_sha256=sha(regression), prior_archives=prior,
        physical_game=False, actual_snes_cpu_dma=False, snes_section_conversion=False,
        physical_cdc_timing=False, new_fit=False, new_firmware=False, new_package=False,
        scope='Deployed exporter/fill/mailbox joined to candidate aperture with synthetic sealed query and memory replies; raw bus consumer. 1813 records, not SNES-ready graphics. No FPS claim.')
    (a.out/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8', newline='\n')
    print(json.dumps(dict(passed=True, cases=len(result['cases']), prior_archives=prior,
                         spi_payload_comparisons=comparisons), indent=2))
if __name__ == '__main__':
    main()
