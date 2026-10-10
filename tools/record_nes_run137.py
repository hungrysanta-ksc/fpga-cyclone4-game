# SPDX-License-Identifier: MIT
"""Import the user's136 physical result into a new immutable observation folder."""
from pathlib import Path
import argparse, hashlib, json, shutil

def record(final, progress, out):
    assert not out.exists()
    raw = progress.read_bytes()
    assert len(raw) % 512 == 0
    records = []
    for start in range(0, len(raw), 512):
        line = raw[start:start+512].decode('ascii').strip()
        assert line.startswith('NES136 ')
        fields = dict(token.split('=', 1) for token in line.split()[1:])
        records.append(fields)
    result = dict(line.split('=', 1) for line in final.read_text().splitlines() if '=' in line)
    expected = dict(candidate='NES-RUN-136', board_expected_hex='59', board_observed_hex='59', board_seen='1',
                    loaded_bytes='81920', compared_bytes='81920', verified='1', end_accepted='1', stop_ok='1',
                    base_restored='1', safe_to_reload='1', start_sent='1', run_passed='1', observer_id_hex='d4',
                    run_flags='1', run_error='0', run_rom_error='0', load_result='0', file_result='0', verify_error='0',
                    menu_state='PREPARED_RESET_HELD')
    assert all(result.get(k) == v for k, v in expected.items()), result
    assert 0 < int(result['run_first']) < int(result['run_last']) <= int(result['run_stopped'])
    assert len(records) == 47
    assert [int(r['seq']) for r in records] == list(range(47))
    assert all(r['entry_transfer']=='1' for r in records)
    assert records[0]['stage']=='ENTRY_SD_READY' and records[-1]['stage']=='MENU_PREPARED'
    elapsed=[int(r['elapsed_ms']) for r in records];assert elapsed==sorted(elapsed)
    assert elapsed[-1]==491600
    assert [r['stage'] for r in records if r['stage'].startswith('RUN_')]==['RUN_NEXT','RUN_STOPPED']
    out.mkdir(parents=True)
    for source in (final, progress):
        shutil.copy2(source, out/source.name)
    data = dict(candidate='NES-SCREEN-137', physical_run136_passed=True, final=result, progress=records,
                raw_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (final, progress)},
                user_confirmed=dict(menu_return=True, restoration=True, gbc_play_this_run=None),
                limits=['CPU ROM sample activity is not instruction, video or game correctness.',
                        'MENU_PREPARED alone is not menu visibility; return confirmed separately by user.',
                        'Firmware elapsed time is not measured wall-clock time.'])
    (out/'result.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, records=len(records), final=result)))

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for key in ('final','progress','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();record(a.final,a.progress,a.out)
