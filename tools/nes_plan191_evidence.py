# SPDX-License-Identifier: MIT
"""Audit bounded planning/materialization evidence; no physical FPS claim."""
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
    folder = BASE / 'probes/nes-plan191'
    normal = json.loads((folder / 'test03/result.json').read_bytes())
    faults = json.loads((folder / 'faults01/result.json').read_bytes())
    assert normal['passed'] and faults['passed'] and faults['cases'] == 9
    production = BASE / 'probes/nes-paired186/arm01/src'
    aliases = {'reference_sha256': production / 'nes_native_video165.c',
               'candidate_sha256': folder / 'test03/candidate/nes_plan191.c',
               'generator': ROOT / 'tools/nes_plan191.py',
               'runner': ROOT / 'tools/test_nes_plan191.py'}
    for result in (normal, faults):
        for name, digest in result['pins'].items():
            path = aliases.get(name, production / name[11:] if name.startswith('production/') else ROOT / name)
            assert sha(path) == digest, name
    assert (folder / 'test03/nes_plan191.h').read_bytes() == (ROOT / 'src/nes/firmware/nes_plan191.h').read_bytes()
    prior = []
    for name in ('nes-paired186', 'nes-game186-hardware01', 'nes-video-arch187',
                 'nes-bulk188', 'nes-source189', 'nes-chr190'):
        archive = BASE / 'probes' / name
        manifest = archive / 'manifest01.json'
        entries = json.loads(manifest.read_bytes())
        for path, digest in entries.items():
            assert sha(archive / path) == digest, (name, path)
        prior.append(dict(name=name, files=len(entries), manifest_sha256=sha(manifest)))
    cases = normal['cases']
    assert len(cases) == 8 and sum(c['plans'] for c in cases) == 97
    totals = {k: sum(c[k] for c in cases) for k in ('plans', 'plan_bytes', 'output_bytes', 'reads')}
    report = dict(passed=True, selected=['test03', 'faults01'], cases=cases, totals=totals,
                  negative_cases=9, host_summary=normal['host_summary'],
                  source_pins=normal['pins'], fault_pins=faults['pins'],
                  result_pins={n: sha(folder / n / 'result.json') for n in ('test03', 'faults01')},
                  plan_bytes_are_estimate=True, wire_codec_implemented=False,
                  tile_buffer_bytes=32, streamed_host_plan_bytes=40,
                  host_metadata_bytes=15912, full_arm_approval=False,
                  fixed_plan_bytes=16, alternate_tag_bytes=2,
                  shared_spi_payload_bytes_per_60hz_frame=2625000 / 8 / 60,
                  baseline_resources=dict(LE=13466, LAB=939, M9K=42, spare_LAB=24, spare_M9K=14),
                  lease='Sealed fixture only; live CHR-RAM/PSRAM lifetime and arbiter are not integrated.',
                  decision='Keep geometry/slots on MCU; qualify immutable source lifetime and direct materializer output before board integration. Ordinary BG plan is not smaller than its output; preserve delta/cache and capture-overlap work.',
                  actual_game=False, actual_snes_dma=False, physical_fit=False,
                  physical_fps=False, new_package=False, prior_archives=prior)
    (a.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8', newline='\n')
    print(json.dumps(dict(passed=True, totals=totals, prior_files=[x['files'] for x in prior])))

if __name__ == '__main__':
    main()
