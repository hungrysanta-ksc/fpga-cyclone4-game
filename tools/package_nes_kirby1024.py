"""Package the loader journal correction against the known Kirby baseline."""
import struct
import zlib
from zipfile import ZipFile

from prepare_nes_kirby1024 import PREVIOUS, WORK
from package_nes_trial872 import ROOT, digest, read, write_verified_archive


def package():
    source = PREVIOUS / 'MMC1023-KIRBY-60SEC-SD-ROOT.zip'
    previous = read(ROOT / 'analysis/trial1023-package.json')
    board_name, = [name for name in previous['files'] if name.endswith('/fpga_mmc1023.bi3')]
    with ZipFile(source) as archive:
        board = archive.read(board_name)
    assert digest(board) == previous['board_BI3']
    fw = (WORK / 'link/src/obj-nes-100/firmware.stm').read_bytes()
    size, crc, inverse = struct.unpack_from('<III', fw, 8)
    assert fw[:4] == b'STM3' and size + 512 == len(fw) <= 212992
    assert zlib.crc32(fw[512:]) == crc == (inverse ^ 0xffffffff)
    for name in (' 1024.nh1', 'mmc1024.nes', 'fpga_mmc1024.bi3', 'nes-frame-mmc1024.bin',
                 *(f'nes-{kind}-mmc1024.txt' for kind in ('game-last', 'budget', 'progress'))):
        assert name.encode() + b'\0' in fw, name

    proof = WORK / 'proof'
    journal = read(proof / 'journal.json')
    menu = read(proof / 'menu.json')
    base = read(proof / 'base-result.json')
    timer = read(proof / 'timer.json')
    windows = read(proof / 'windows.json')
    normal = read(proof / 'sram.json')['cases']['normal']
    loader = read(proof / 'loader.json')
    assert digest(fw) == journal['fixed']['firmware'] == windows['firmware_SHA256']
    assert digest(fw) == menu['firmware'] == base['firmware_sha256'] == timer['firmware']
    assert journal['old']['first_rejected_check_B'] == journal['fixed']['after_128'][1] == 414720
    assert journal['fixed']['end'][0] == 'MENU_PREPARED'
    assert menu['rows']['normal']['released'] and base['safe_return'] and timer['passed']
    assert normal['checked_retire'] and normal['static_gap_bytes'] > 0
    assert loader['kirby']['program'] and loader['bad-last']['error'] == 4
    assert (PREVIOUS / 'arm/plans.txt').read_bytes() == (WORK / 'arm/plans.txt').read_bytes()
    pixels = read(WORK / 'arm/pixels.json')
    assert sorted(row['frame'] for row in pixels) == [750, 1830, 3030, 3570]
    assert all(row['errors'] == 0 for row in pixels)
    report = dict(edition=1024, physical=False, firmware=digest(fw), flash_B=len(fw),
                  flash_free_B=212992-len(fw), board_BI3=digest(board),
                  journal=journal, pixel_errors=[row['errors'] for row in pixels],
                  policy=previous['policy'], remember=previous['remember'])
    write_verified_archive(WORK, previous, fw, board, report, source=source, game_label='KIRBY')


if __name__ == '__main__':
    package()
