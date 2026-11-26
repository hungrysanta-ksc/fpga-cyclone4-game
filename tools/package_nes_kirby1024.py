"""Package the loader journal correction against the known Kirby baseline."""
import argparse
import struct
import zlib
from zipfile import ZipFile

from prepare_nes_kirby1024 import PREVIOUS, WORK
from package_nes_trial872 import ROOT, digest, read, write_verified_archive


def package(edition=1024):
    work = WORK.with_name(f'nes-kirby{edition}')
    parent = edition - 1
    reference = PREVIOUS.with_name(f'nes-kirby{parent}')
    source = reference / f'MMC{parent}-KIRBY-60SEC-SD-ROOT.zip'
    previous = read(ROOT / f'analysis/trial{parent}-package.json')
    board_name, = [name for name in previous['files'] if name.endswith(f'/fpga_mmc{parent}.bi3')]
    with ZipFile(source) as archive:
        board = archive.read(board_name)
    assert digest(board) == previous['board_BI3']
    fw = (work / 'link/src/obj-nes-100/firmware.stm').read_bytes()
    size, crc, inverse = struct.unpack_from('<III', fw, 8)
    assert fw[:4] == b'STM3' and size + 512 == len(fw) <= 212992
    assert zlib.crc32(fw[512:]) == crc == (inverse ^ 0xffffffff)
    for name in (f' {edition}.nh1', f'mmc{edition}.nes', f'fpga_mmc{edition}.bi3', f'nes-frame-mmc{edition}.bin',
                 *(f'nes-{kind}-mmc{edition}.txt' for kind in ('game-last', 'budget', 'progress'))):
        assert name.encode() + b'\0' in fw, name

    proof = work / 'proof'
    journal = read(proof / 'journal.json')
    menu = read(proof / 'menu.json')
    base = read(proof / 'base-result.json')
    timer = read(proof / 'timer.json')
    windows = read(proof / 'windows.json')
    normal = read(proof / 'sram.json')['cases']['normal']
    loader = read(proof / 'loader.json')
    fixed = journal['fixed'] if edition == 1024 else journal
    assert digest(fw) == fixed['firmware'] == windows['firmware_SHA256']
    assert digest(fw) == menu['firmware'] == base['firmware_sha256'] == timer['firmware']
    if edition == 1024:
        assert journal['old']['first_rejected_check_B'] == 414720
    assert fixed['after_128'][1] == 414720 and fixed['end'][0] == 'MENU_PREPARED'
    assert menu['rows']['normal']['released'] and base['safe_return'] and timer['passed']
    assert normal['checked_retire'] and normal['static_gap_bytes'] > 0
    assert loader['kirby']['program'] and loader['bad-last']['error'] == 4
    assert (reference / 'arm/plans.txt').read_bytes() == (work / 'arm/plans.txt').read_bytes()
    pixels = read(work / 'arm/pixels.json')
    assert sorted(row['frame'] for row in pixels) == [750, 1830, 3030, 3570]
    assert all(row['errors'] == 0 for row in pixels)
    report = dict(edition=edition, physical=False, firmware=digest(fw), flash_B=len(fw),
                  flash_free_B=212992-len(fw), board_BI3=digest(board),
                  journal=journal, pixel_errors=[row['errors'] for row in pixels],
                  policy=previous['policy'], remember=previous['remember'])
    if edition==1025:
        sampling = read(proof/'sampling.json')
        assert sampling['firmware']==digest(fw) and sampling['windows']==sampling['wire_reads']==75
        report['sampling'] = sampling
    write_verified_archive(work, previous, fw, board, report, source=source, game_label='KIRBY')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--edition', type=int, choices=(1024,1025), default=1024)
    package(parser.parse_args().edition)
