"""Package the complete interactive menu only after checking its final route and firmware."""
import argparse
import hashlib
import json
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path

from package_nes_kirby1027 import programmer, timing
from nes_cf68_pair_preflight import encode, decode

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / 'probes/nes-ff3-1043'
PRIOR = WORK.parent / 'nes-kirby1035/MMC1035-KIRBY-60SEC-SD-ROOT.zip'
FINAL = WORK / 'FF3-1044-NES-PLAY-SD-ROOT.zip'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def report(name):
    return json.loads((WORK / name).read_text())


def package(route):
    board = timing(route)
    simulated = WORK/'board-stop'
    fitted = WORK/'board-timing'
    # Timing closure changes only placement constraints. Check the complete
    # generated source tree against the one exercised by the RTL benches.
    def source_files(folder):
        return {p.relative_to(folder): digest(p.read_bytes()) for p in folder.rglob('*')
                if p.is_file() and p.name != 'board.sdc'}
    assert source_files(simulated) == source_files(fitted)
    assert (fitted/'sink-program.hex').read_bytes() == (WORK/'rom-timing/sink-program.hex').read_bytes()
    sram = (route / 'sram.tsv').read_text().splitlines()[1:]
    assert {row.split('\t')[1] for row in sram} == {'input', 'output'}
    corners = {row.split('\t')[0] for row in sram}
    assert len(corners) == 3
    obj = WORK / 'arm-cold/src/obj-nes-100'
    fw = (obj / 'firmware.stm').read_bytes()
    n, crc, inverse = struct.unpack_from('<III', fw, 8)
    assert fw[:4] == b'STM3' and n + 512 == len(fw) <= 212992
    assert crc == zlib.crc32(fw[512:]) == inverse ^ 0xffffffff
    for name in ['nes-progress-ff31044.txt', 'nes-game-last-ff31044.txt', 'nes-frame-ff31044.bin',
                 'nes-chrram.bi3', 'nes-chrrom.bi3']:
        assert name.encode() + b'\0' in fw, name
    identity = digest(fw)
    base = report('base1044-final/result.json')
    io = report('io-cold.json')
    browse = report('browser-cold.json')
    assert identity == base['firmware_sha256'] == io['firmware_sha256'] == browse['firmware_stm_sha256']
    assert base['safe_return'] and base['base_restored']
    assert base['config_paths'] == ['/sd2snes/nes-chrram.bi3', '/sd2snes/fpga_base.bi3']
    assert io['state_bytes'] == 21264 and io['battery_bytes'] == 8192
    assert report('dispatch-slots.json')['distinct_slots_reloaded'] == 4
    assert '524288 independent PSRAM reads' in (WORK / 'restart-final.txt').read_text()
    device_menu = (WORK / 'menu-cpu-final.log').read_text(errors='replace')
    assert all(msg in device_menu for msg in ('exact VRAM/CGRAM', 'PASS SLOT 2 LOAD STATE', 'PASS EXIT TO MENU'))
    for name in ['ff3_load_count_tb', 'ff3_menu_link_tb', 'ff3_spi_tb']:
        assert 'PASS' in (WORK / (name + '.log')).read_text()
    sim = (WORK.parent / 'nes-ff3-checkpoint/vsim-checkpoint.log').read_text(errors='replace')
    assert 'PASS FF3 checkpoint words=2658' in sim and '** Fatal' not in sim
    assert 'restored=1 visible pixels=122880' in sim and 'Errors: 0' in sim
    assert 'FF3 FAT16 menu checkpoint via two ARM boots' in sim
    pgm = json.loads((route/'programmer.json').read_text())
    raw = (route/'board.rbf').read_bytes()
    bitstream = encode(raw)
    assert decode(bitstream) == raw and pgm['passed']
    assert pgm['rbf_sha256'] == digest(raw) and pgm['image_sha256'] == digest(bitstream)
    files = {'firmware.stm': fw, 'nes-chrram.bi3': bitstream}
    reference = json.loads((ROOT/'analysis/trial1035-package.json').read_text())
    assert digest(PRIOR.read_bytes()) == reference['ZIP_SHA256']
    with zipfile.ZipFile(PRIOR) as old:
        for dest in ['fpga_base.bi3', 'm3nu.bin', 'fpga_egbc.bi3', 'gbc_snes.bin', 'nes-chrrom.bi3']:
            name = 'fpga_mmc1035.bi3' if dest == 'nes-chrrom.bi3' else dest
            files[dest] = old.read(f'MMC1035-KIRBY-60SEC-SD-ROOT/sd2snes/{name}')
    manifest = dict(edition=1044, hardware_tested=False, board=board, flash_bytes=len(fw),
                    files={k: digest(v) for k, v in files.items()}, sof=digest((route/'board.sof').read_bytes()),
                    rbf=pgm['rbf_sha256'])
    with tempfile.TemporaryDirectory(dir=WORK) as tmp:
        dst = Path(tmp) / FINAL.name
        with zipfile.ZipFile(dst, 'w', compression=zipfile.ZIP_DEFLATED) as out:
            for k, v in files.items():
                out.writestr('sd2snes/' + k, v)
            out.writestr('README-KO.txt', (ROOT/'docs/nes-ff3-play1044.ko.md').read_bytes())
            out.writestr('manifest.json', json.dumps(manifest, indent=2))
        with zipfile.ZipFile(dst) as out:
            assert out.testzip() is None
            for k, v in files.items():
                assert out.read('sd2snes/' + k) == v
        dst.replace(FINAL)
    manifest['ZIP_SHA256'] = digest(FINAL.read_bytes())
    manifest['archive'] = FINAL.name
    manifest['checkpoint'] = dict(words=2658, pixels_compared=122880, cpu_fetches_compared=64,
                                  partial_restore_stop_cases=7, battery_bytes=io['battery_bytes'],
                                  sectors_written=io['sectors_written'], stack_gap_observed_B=report('dispatch-cold.json')['free_stack_observed_B'])
    manifest['base_return'] = base['scope']
    manifest['external_SRAM'] = 'Routed input/output pin delays in lite-timing/sram.tsv. Actual board and SRAM delays require the physical test.'
    (ROOT/'analysis/ff3-play1044.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(FINAL, manifest['ZIP_SHA256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('route', type=Path)
    parser.add_argument('--check-programmer', action='store_true')
    args = parser.parse_args()
    if args.check_programmer:
        _, proof = programmer(args.route, WORK, 1044)
        (args.route/'programmer.json').write_text(json.dumps(proof, indent=2))
    else:
        package(args.route)
