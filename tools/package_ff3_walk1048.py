"""Package the tested CHR-page board and the same ARM links used for replay."""
import json
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path

from nes_cf68_pair_preflight import decode, encode
from package_ff3_battle1047 import digest, read
from package_nes_kirby1027 import timing

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / 'probes/nes-ff3-1048'
NAME = 'FF3-1048-NES-PLAY-SD-ROOT.zip'


def package():
    previous = read(ROOT / 'analysis/ff3-battle1047.json')
    old = WORK.parent / 'nes-ff3-1047/FF3-1047-NES-PLAY-SD-ROOT.zip'
    assert digest(old.read_bytes()) == previous['ZIP_SHA256']
    with zipfile.ZipFile(old) as src:
        files = {k: src.read('sd2snes/' + k) for k in previous['files']}
    assert {k: digest(v) for k, v in files.items()} == previous['files']

    routed = WORK / 'lite-io'
    board = timing(routed)
    raw = (routed / 'board.rbf').read_bytes()
    image = encode(raw)
    programmer = read(routed / 'programmer.json')
    assert programmer['passed'] and programmer['rbf_sha256'] == digest(raw)
    assert programmer['image_sha256'] == digest(image) and decode(image) == raw
    checks = [row.split('\t') for row in (routed / 'sram.tsv').read_text().splitlines()[1:]]
    corners = {row[0] for row in checks}
    assert len(corners) == 3 and all({(r[1],r[2]) for r in checks if r[0] == corner} ==
        {(direction, check) for direction in ('input','output') for check in ('setup','hold')} for corner in corners)
    fw = (WORK / 'link-final/src/obj-nes-100/firmware.stm').read_bytes()
    size, crc, inv = struct.unpack_from('<III', fw, 8)
    assert fw[:4] == b'STM3' and len(fw) == size+512 <= 212992
    assert crc == zlib.crc32(fw[512:]) == inv ^ 0xffffffff
    for log in ('nes-progress-ff31048.txt', 'nes-game-last-ff31048.txt', 'nes-frame-ff31048.bin'):
        assert log.encode() + b'\0' in fw
    io = read(WORK / 'io.json')
    ret = read(WORK / 'return/result.json')
    assert ret['passed'] and ret['safe_return'] and ret['base_restored']
    assert io['state_bytes'] == 21264 and io['firmware_sha256'] == ret['firmware_sha256'] == digest(fw)
    for log, markers in {
        'test/pages.log': ['PASS FF3 8192B snapshot'],
        'test/stop.log': ['PASS cold validation, slot restart'],
        'test/vsim-checkpoint.log': ['PASS FF3 physical scene replay'],
        'guards-final/battle-test.log': ['PASS eight page masks', 'PASS FF3 64 reference flash frames'],
    }.items():
        data = (WORK / log).read_text(errors='replace')
        assert all(marker in data for marker in markers)

    report = {}
    for scene, file, frames in [('town','town.json',11),('field','field-comparison.json',4)]:
        rows = read(WORK / file)
        assert rows['binaries'] == {'1047': previous['files']['firmware.stm'], '1048': digest(fw)}
        baseline, candidate = rows['frames']['1047'], rows['frames']['1048']
        assert len(candidate) == frames
        assert all((a['f'],a['image']) == (b['f'],b['image']) for a,b in zip(baseline,candidate,strict=True))
        report[scene] = {'frames': [r['f'] for r in candidate]}
        for key in ('planner_instructions','tile_bytes','descriptor_bytes'):
            values = [sum(r[key] for r in sample) for sample in (baseline,candidate)]
            assert values[1] < values[0]
            report[scene][key] = values
    files.update({'firmware.stm': fw, 'nes-chrram.bi3': image})
    result = dict(edition=1048, hardware_tested=False, physical_fps=None,
                  flash_bytes=len(fw), rbf=digest(raw), board=board, replay=report,
                  files={k:digest(v) for k,v in files.items()})
    with tempfile.TemporaryDirectory(dir=WORK) as tmp:
        path = Path(tmp) / NAME
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as dst:
            for k,v in files.items():
                dst.writestr('sd2snes/'+k,v)
            dst.writestr('README-KO.txt',(ROOT/'docs/nes-ff3-walk1048.ko.md').read_bytes())
            dst.writestr('manifest.json',json.dumps(result,indent=2))
        with zipfile.ZipFile(path) as dst:
            assert dst.testzip() is None and all(dst.read('sd2snes/'+k)==v for k,v in files.items())
        path.replace(WORK/NAME)
    result['ZIP_SHA256'] = digest((WORK/NAME).read_bytes())
    (ROOT/'analysis/ff3-walk1048.json').write_text(json.dumps(result,indent=2)+'\n')
    print(NAME,result['ZIP_SHA256'])


if __name__ == '__main__':
    package()
