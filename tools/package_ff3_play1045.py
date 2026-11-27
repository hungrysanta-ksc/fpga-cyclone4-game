"""Verify the interactive 1045 link, routed CHR-RAM board and release archive."""
import hashlib
import json
import re
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path

from nes_cf68_pair_preflight import encode, decode
from package_nes_kirby1027 import timing

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent / 'probes/nes-ff3-1045'
PRIOR = WORK.parent / 'nes-ff3-1043/FF3-1044-NES-PLAY-SD-ROOT.zip'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package():
    route = WORK/'lite-final'
    fit = timing(route)
    sram = [line.split('\t') for line in (route/'sram.tsv').read_text().splitlines()[1:]]
    assert len({row[0] for row in sram}) == 3
    for corner in {row[0] for row in sram}:
        assert {(r[1], r[2]) for r in sram if r[0] == corner} == {
            ('input','setup'),('input','hold'),('output','setup'),('output','hold')}
    raw = (route/'board.rbf').read_bytes()
    packed = encode(raw)
    pgm = json.loads((route/'programmer.json').read_text())
    assert pgm['passed'] and decode(packed) == raw
    assert pgm['rbf_sha256'] == digest(raw) and pgm['image_sha256'] == digest(packed)

    fw = (WORK/'link/src/obj-nes-100/firmware.stm').read_bytes()
    size, crc, inverse = struct.unpack_from('<III',fw,8)
    assert fw[:4] == b'STM3' and len(fw) == size+512 <= 212992
    assert crc == zlib.crc32(fw[512:]) == (inverse ^ 0xffffffff)
    for log in ('nes-progress-ff31045.txt','nes-game-last-ff31045.txt','nes-frame-ff31045.bin'):
        assert log.encode()+b'\0' in fw
    result = json.loads((WORK/'return2/result.json').read_text())
    assert result['safe_return'] and result['base_restored'] and result['firmware_sha256'] == digest(fw)
    menu=(WORK/'menu-cpu.log').read_text(errors='replace')
    assert all(text in menu for text in ('exact VRAM/CGRAM','PASS SLOT 2 LOAD STATE','PASS EXIT TO MENU'))
    assert (WORK/'menu-final/sink-program.hex').read_bytes() == (WORK/'board-final/sink-program.hex').read_bytes()
    io = json.loads((WORK/'io.json').read_text())
    assert io['state_bytes'] == 21264 and io['firmware_sha256'] == digest(fw)
    assert json.loads((WORK/'browser.json').read_text())['firmware_stm_sha256'] == digest(fw)
    assert json.loads((WORK/'slots.json').read_text())['distinct_slots_reloaded'] == 4
    assert '524288 independent PSRAM reads/ACK' in (WORK/'restart.txt').read_text()
    assert 'first_error 0' in (WORK/'early-fixed.log').read_text()
    assert 'first_error 5' in (WORK/'early-original.log').read_text()

    replay = (WORK/'final/vsim-checkpoint.log').read_text(errors='replace')
    assert 'PASS FF3 physical scene replay' in replay and 'Errors: 0' in replay
    opening = re.findall(r'^# COLLECT valid=1 .* raw_errors=00 raw_rows=0 mask=0a',replay,re.M)
    assert opening
    old_opening=(WORK/'opening/vsim-checkpoint.log').read_text(errors='replace')
    old_drops=len(re.findall(r'^# COLLECT valid=0 .*raw_errors=08 raw_rows=7 mask=0a',old_opening,re.M))
    assert old_drops and 'PASS FF3 physical scene replay' in old_opening
    old_saved=(WORK/'vsim-checkpoint.log').read_text(errors='replace')
    assert old_saved.count('eligible=0 conflict=0 CHR_write_clocks=8 visible_write_clocks=0') == 6
    assert 'PASS FF3 mask 256 cases' in (WORK/'final/mask.log').read_text(errors='replace')
    assert 'PASS FF3 8192B snapshot' in (WORK/'final/pages.log').read_text(errors='replace')
    reference=json.loads((WORK/'pixel-check/pixels.json').read_text())
    assert reference['matched'] and reference['pixels']==368640
    saved = (WORK/'saved/vsim-checkpoint.log').read_text(errors='replace')
    assert 'PASS FF3 physical scene replay' in saved and saved.count('eligible=1 conflict=0') == 6
    assert len(re.findall(r'^# COLLECT valid=1 .* raw_errors=00 raw_rows=0 mask=1e',saved,re.M)) >= 5
    # The saved-scene run used the page-only board. Prove that only raster
    # admission changed, and that the common gameplay mask keeps its meaning.
    first = WORK/'board'
    final = WORK/'board-final'
    sources = {p.relative_to(first) for p in first.rglob('*') if p.is_file()}
    assert sources == {p.relative_to(final) for p in final.rglob('*') if p.is_file()}
    def lf(p):
        return p.read_bytes().replace(b'\r\n',b'\n')
    changed = {str(p) for p in sources if lf(first/p) != lf(final/p)}
    assert changed == {'nes_native_raster181.sv'}

    expected = json.loads((ROOT/'analysis/ff3-play1044.json').read_text())
    assert digest(PRIOR.read_bytes()) == expected['ZIP_SHA256']
    with zipfile.ZipFile(PRIOR) as old:
        files = {k:old.read('sd2snes/'+k) for k in expected['files']}
    assert {k:digest(v) for k,v in files.items()} == expected['files']
    files.update({'firmware.stm':fw,'nes-chrram.bi3':packed})
    manifest = dict(edition=1045,hardware_tested=False,board=fit,flash_bytes=len(fw),
                    files={k:digest(v) for k,v in files.items()},rbf=digest(raw),
                    opening_captures=len(opening),prior_opening_raw_overflows=old_drops,
                    slot1_old_capture_windows=0,slot1_new_capture_windows=6,reference_pixels=reference['pixels'],
                    fps_measured_on_hardware=None)
    name = 'FF3-1045-NES-PLAY-SD-ROOT.zip'
    with tempfile.TemporaryDirectory(dir=WORK) as tmp:
        dst = Path(tmp)/name
        with zipfile.ZipFile(dst,'w',compression=zipfile.ZIP_DEFLATED) as out:
            for k,v in files.items():
                out.writestr('sd2snes/'+k,v)
            out.writestr('README-KO.txt',(ROOT/'docs/nes-ff3-play1045.ko.md').read_bytes())
            out.writestr('manifest.json',json.dumps(manifest,indent=2))
        with zipfile.ZipFile(dst) as out:
            assert out.testzip() is None
            assert all(out.read('sd2snes/'+k)==v for k,v in files.items())
        dst.replace(WORK/name)
    manifest['ZIP_SHA256'] = digest((WORK/name).read_bytes())
    (ROOT/'analysis/ff3-play1045.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(name, manifest['ZIP_SHA256'])


if __name__ == '__main__':
    package()
