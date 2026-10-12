# SPDX-License-Identifier: MIT
"""Expose bounded secondary OAM addresses; retain a rejected read-port experiment.

No register, memory write, clock enable, or external interface is changed.
The default secondary-range transform changes four address expressions only.
"""
from pathlib import Path
import argparse, difflib, json, shutil
from nes_game147 import ROOT, sha
from nes_oam_select165 import prepare as prepare_area


def transform(text, variant='secondary-range'):
    start = text.index('module OAMEval(')
    end = text.index('endmodule', start)
    old = text[start:end]
    s = old
    if variant in ['secondary-range', 'secondary-range-bank-data-enable']:
        # Each write is already guarded by oam_secondary_row_ex < 8.
        # Express the resulting upper-half address without an overflowing add.
        # This lets synthesis isolate extra-sprite writes from base OAM bytes.
        assert s.count('if (oam_secondary_row_ex < 8) begin') == 1
        for lane in range(4):
            needle = "{oam_secondary_row_ex, 2'b" + f'{lane:02b}' + "} + 6'd32"
            assert s.count(needle) == 1
            s = s.replace(needle, "{1'b1, oam_secondary_row_ex[2:0], 2'b" + f'{lane:02b}' + '}')
        if variant == 'secondary-range-bank-data-enable':
            for lane in range(8):
                needle = f'reg [7:0] oam_bank{lane}[0:31];'
                assert s.count(needle) == 1
                s = s.replace(needle, '(* altera_attribute = "-name AUTO_CLOCK_ENABLE_RECOGNITION OFF" *) ' + needle)
        return text[:start] + s + text[end:]
    assert variant == 'shared-read'
    # The main byte is consumed on even evaluation cycles or outside rendering.
    # The repeat detector consumes aligned Y/tile/attr on odd evaluation cycles.
    # Rendering fetch/refresh use secondary OAM, so they need neither port.
    declarations = '''// Share primary byte/repeat reads; extra-sprite and row-copy reads stay independent.
wire [4:0] oam_shared_row = rendering && secondary_write ? oam_addr[7:3] : oam_read_addr[7:3];
wire [63:0] oam_shared_word = {''' + ', '.join(
        f'oam_bank{i}[oam_shared_row]' for i in reversed(range(8))) + '''};
wire [7:0] oam_shared_byte = oam_shared_word[oam_read_addr[2:0]*8 +: 8];
wire [31:0] oam_shared_sprite = oam_addr[2] ? oam_shared_word[63:32] : oam_shared_word[31:0];
'''
    needle = 'assign native_oam_data='
    assert s.count(needle) == 1
    s = s.replace(needle, declarations + '\n' + needle)
    assert s.count('oam_read(oam_read_addr)') == 2
    s = s.replace('oam_read(oam_read_addr)', 'oam_shared_byte')
    for lane, bits in [(0, '7:0'), (1, '15:8'), (2, '23:16')]:
        needle = "oam_read({oam_addr[7:2], 2'b" + f'{lane:02b}' + '})'
        assert s.count(needle) == 2, needle
        s = s.replace(needle, f'oam_shared_sprite[{bits}]')
    return text[:start] + s + text[end:]


def prepare(baseline, out, variant='secondary-range'):
    prepare_area(baseline, out, 'area')
    p = out / 'rtl/ppu.sv'
    before = p.read_text()
    after = transform(before, variant)
    p.write_text(after, encoding='utf8')
    (out / 'oam-port.diff').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile='board03/rtl/ppu.sv',
        tofile='port165/rtl/ppu.sv')), encoding='utf8')
    m = json.loads((out / 'preparation.json').read_bytes())
    m['variant'] = variant + '-area'
    m['sources']['rtl/ppu.sv'] = sha(p)
    m['changed'] = ['board.qsf', 'rtl/ppu.sv']
    m['public_sources']['tools/nes_oam_port165.py'] = sha(Path(__file__))
    assert sorted(n for n in m['sources'] if m['sources'][n] != m['baseline'][n]) == m['changed']
    (out / 'preparation.json').write_text(json.dumps(m, indent=2) + '\n')


def prepare_fit(source, out, mode='physical-area'):
    """Reuse a successful mapped database for area-oriented physical synthesis."""
    assert not out.exists() and str(out).isascii()
    m = json.loads((source / 'preparation.json').read_bytes())
    assert m['variant'] == 'secondary-range-area'
    assert 'Analysis & Synthesis was successful' in (source / 'map.log').read_text()
    out.mkdir(parents=True)
    for n, h in m['sources'].items():
        assert sha(source / n) == h, n
        (out / n).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / n, out / n)
    # Keep every mapped database byte; do not import the failed fitting outputs.
    for n in ['db', 'incremental_db']:
        shutil.copytree(source / n, out / n)
    (out / 'output_files').mkdir()
    for p in (source / 'output_files').glob('board.map.*'):
        shutil.copy2(p, out / 'output_files' / p.name)
    shutil.copy2(source / 'map.log', out / 'map.log')
    p = out / 'board.qsf'
    setting = {'physical-area':'PHYSICAL_SYNTHESIS_COMBO_LOGIC_FOR_AREA ON',
               'packed-area':'QII_AUTO_PACKED_REGISTERS "MINIMIZE AREA"'}[mode]
    p.write_text(p.read_text() + '\nset_global_assignment -name ' + setting + '\n')
    m['sources']['board.qsf'] = sha(p)
    m['variant'] = 'secondary-range-' + mode
    m['reused_map_sha256'] = sha(source / 'output_files/board.map.rpt')
    m['public_sources']['tools/nes_oam_port165.py'] = sha(Path(__file__))
    (out / 'preparation.json').write_text(json.dumps(m, indent=2) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--fit-area-from', type=Path)
    p.add_argument('--fit-mode', choices=['physical-area','packed-area'], default='physical-area')
    p.add_argument('--variant', choices=['secondary-range', 'secondary-range-bank-data-enable', 'shared-read'], default='secondary-range')
    a = p.parse_args()
    if a.fit_area_from:
        prepare_fit(a.fit_area_from, a.out, a.fit_mode)
    else:
        assert a.baseline
        prepare(a.baseline, a.out, a.variant)
