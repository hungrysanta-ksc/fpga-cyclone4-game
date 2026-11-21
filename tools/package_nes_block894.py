"""Build the first-block SD bundle from the verified MMC893 board and final ARM."""
import json
import struct
import zlib
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from package_nes_trial872 import ROOT, digest, read, save, sha
from prepare_nes_block894 import BASE, WORK


def package():
    parent = read(ROOT/'analysis/trial893-package.json')
    source = BASE.parent/'MMC893-ADVENTURE-60SEC-SD-ROOT.zip'
    assert sha(source)==parent['ZIP_SHA256']
    firmware = (WORK/'linkB/src/obj-nes-100/firmware.stm').read_bytes()
    size, crc, inverse = struct.unpack_from('<III',firmware,8)
    assert firmware[:4]==b'STM3' and size+512==len(firmware)<=212992
    assert crc==zlib.crc32(firmware[512:]) and inverse^crc==0xffffffff
    for literal in ('NES BLOCK 894.nh1','mmc894.nes','fpga_mmc894.bi3',
                    'nes-budget-mmc894.txt','nes-progress-mmc894.txt','nes-game-last-mmc894.txt'):
        assert literal.encode()+b'\0' in firmware
    checks = read(WORK/'checks.json')
    loader = read(WORK/'loader.json')
    base = read(WORK/'recovery/result.json')
    full = read(WORK/'full-loader/result.json')
    assert checks['firmware']==loader['firmware']==base['firmware_sha256']==full['firmware']==digest(firmware)
    assert full['passed'] and full['compared']==393216 and full['entry_sp']==checks['entry_sp']
    assert loader['cases']==parent['checks']['loader']['cases'] and base['safe_return'] and base['base_restored']
    files = {}
    with ZipFile(source) as archive:
        for name, expected in parent['files'].items():
            data = archive.read(name)
            assert digest(data)==expected
            if '/NES-DIAG/' in name:
                continue
            if name=='README-KO.txt':
                data = (ROOT/'docs/nes-mmc894-trial.ko.md').read_bytes()
            elif name.endswith('/firmware.stm'):
                data = firmware
            elif name.endswith('/ROM-NOT-INCLUDED.txt'):
                data = data.replace(b'mmc893.nes',b'mmc894.nes')
            name = name.replace('MMC893-ADVENTURE-60SEC','MMC894-FIRST-BLOCK').replace('NES MMC3','NES BLOCK').replace('893','894')
            files[name] = data
    assert sum(n.endswith('.nh1') for n in files)==1
    assert all('restore' not in n.lower() and not n.lower().endswith('.nes') for n in files)
    report = dict(edition=894,hardware_verified=False,ARM=checks['firmware'],flash_B=len(firmware),
                  reused_board=parent['board']['image'],reference_ZIP=sha(source),client=parent['client'],
                  checks=checks,loader=loader,full_loader=full,base=base,files={n:digest(b) for n,b in files.items()})
    files['manifest.json'] = (json.dumps(report,indent=2)+'\n').encode()
    path = WORK/'MMC894-FIRST-BLOCK-SD-ROOT.zip'
    partial = path.with_suffix('.partial')
    with ZipFile(partial,'w') as archive:
        for name, data in files.items():
            archive.writestr(ZipInfo(name),data,compress_type=ZIP_DEFLATED)
    with ZipFile(partial) as archive:
        assert archive.testzip() is None and archive.namelist()==list(files)
        assert all(archive.read(n)==b for n,b in files.items())
    partial.replace(path)
    report['ZIP_SHA256'] = sha(path)
    save(ROOT/'analysis/block894-results.json',report)
    print(path,report['ZIP_SHA256'])


if __name__=='__main__':
    package()
