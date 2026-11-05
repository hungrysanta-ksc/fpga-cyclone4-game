"""Bind the 595 pin-level functional run to the same-boundary Lite MAP gate."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('simulation', type=Path)
    parser.add_argument('mapping', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = json.loads((args.simulation / 'result.json').read_bytes())
    summary_path = args.mapping / 'region.map.summary'
    summary = summary_path.read_text()
    assert 'Successful' in summary and 'Lite Edition' in summary
    labels = {'LE': 'Total logic elements', 'comb': 'Total combinational functions',
              'FF': 'Dedicated logic registers', 'RAM_bits': 'Total memory bits'}
    candidate = {}
    for key, label in labels.items():
        count = re.search(r'^\s*' + label + r'\s*:\s*([\d,]+)', summary, re.M)
        candidate[key] = int(count[1].replace(',', ''))
    reference = json.loads((ROOT / 'analysis/source589-verification.json').read_bytes())['costs']['reference']
    arm = json.loads((ROOT / 'analysis/report594-verification.json').read_bytes())
    assert result['ELF'] == arm['input_test']['pins']['sd2snes.elf']
    for name, expected in result['RTL'].items():
        assert digest(ROOT / 'rtl' / name) == expected
    frames = result['frames']
    assert 906 <= frames[-1]['generation'] <= 957
    assert [f['generation'] for f in frames] == list(range(905, frames[-1]['generation'] + 1))
    result.update(stage=595, reference=reference, candidate=candidate,
                  delta={k: candidate[k] - reference[k] for k in reference},
                  normal_frame_count=len(frames), full_53_complete=len(frames) == 53,
                  board_headroom_LE=148, local_screen_LE=reference['LE'] + 148,
                  local_screen_pass=candidate['LE'] <= reference['LE'] + 148,
                  whole_board_fit=None, whole_board_sta=None, two_phase_timing=None,
                  wire_B=sum(f['wire_B'] for f in frames), packets=sum(f['packets'] for f in frames),
                  transactions=sum(f['calls'] for f in frames), physical_baseline='MMC577',
                  map_summary_sha256=digest(summary_path), map_report_sha256=digest(args.mapping / 'region.map.rpt'),
                  test_sources={n: digest(ROOT / 'tools' / n) for n in
                                ('check_nes_region595.py', 'nes_region595_tb.sv', 'nes_region595_rpc.tcl')})
    args.output.write_bytes((json.dumps(result, indent=2) + '\n').encode())


if __name__ == '__main__':
    main()
