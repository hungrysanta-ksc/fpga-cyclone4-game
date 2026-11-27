"""Use each 1054 board set with its matching final, verified ARM firmware."""
import hashlib
import json
import struct
import zipfile
import zlib
from prepare_ff3_pair1055 import OUT, ROOT


def sha(data):
    return hashlib.sha256(data).hexdigest()


def package():
    tests=json.loads((OUT/'verification.json').read_text())
    assert tests['menu_copy']==65536 and tests['ff3_stop_base']['menu_released'] and tests['actual_raw_dma_pixels']==8192
    for case in (0,1):
        assert '# PASS FF3' in (OUT/'spi'/f'boot{case}.log').read_text()
    for first in (55,95,134,218):
        assert 'PASS GEOMETRY230 frames=4' in (OUT/f'g{first}'/f'{first}.log').read_text()
    original=json.loads((ROOT/'analysis/kirby-pair1054.json').read_text())
    original['release']=json.loads((ROOT/'analysis/nes-retail1054r2.json').read_text())
    result={}
    for profile in ('debug','release'):
        assert tests['profiles'][profile]['distinct_slots_reloaded']==4
        prior=original[profile]
        name=prior.get('zip') or 'NES-1054r2-RELEASE-SD-ROOT.zip'
        source=OUT.parent/'nes-pair1054r2'/name
        assert sha(source.read_bytes())==prior['sha256']
        firmware=(OUT/profile/'link/src/obj-nes-100/firmware.stm').read_bytes()
        assert sha(firmware)==tests['profiles'][profile]['firmware_sha256']
        size,crc,inv=struct.unpack_from('<III',firmware,8)
        assert firmware[:4]==b'STM3' and size+512==len(firmware)<=212992
        assert zlib.crc32(firmware[512:])==crc==(inv^0xffffffff)
        for log in (b'nes-progress-',b'nes-game-last-',b'nes-frame-'):
            assert (log+b'debug1055' in firmware)==(profile=='debug')
            if profile=='release':assert log not in firmware
        files={}
        target=OUT/f'NES-1055-{profile.upper()}-SD-ROOT.zip'
        tmp=target.with_suffix('.tmp')
        with zipfile.ZipFile(source) as old,zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as new:
            for item,h in prior['files'].items():
                path='sd2snes/'+item
                data=old.read(path)
                assert sha(data)==h
                if item=='firmware.stm':data=firmware
                files[item]=sha(data)
                new.writestr(path,data)
            manifest=dict(edition=1055,profile=profile,firmware_bytes=len(firmware),files=files)
            new.writestr('manifest.json',json.dumps(manifest,indent=2))
            new.writestr('README-KO.txt',(ROOT/'docs/nes-pair1055.ko.md').read_bytes())
        with zipfile.ZipFile(tmp) as z:
            assert not z.testzip() and len(z.namelist())==9
            assert all(sha(z.read('sd2snes/'+n))==h for n,h in files.items())
        tmp.replace(target)
        result[profile]=dict(manifest,zip=target.name,sha256=sha(target.read_bytes()))
    (ROOT/'analysis/nes-pair1055.json').write_text(json.dumps(dict(archives=result,tests=tests),indent=2)+'\n')


if __name__=='__main__':
    package()
