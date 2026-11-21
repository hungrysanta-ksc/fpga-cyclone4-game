"""Package the linked probes and the byte-identical, hardware-tested MMC894 board."""
import json
import struct
import zlib
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from package_nes_trial872 import ROOT, digest, read, save, sha
from prepare_nes_input895 import BASE, MODES, WORK


def package(work=WORK,edition=895,modes=MODES,*,source=None,parent_report='block894-results',
            folder='MMC895-FIRST-INPUT-SD-ROOT',root_markers=('OFFER',),log_suffixes=('',),
            result_name='input895-results'):
    fw = (work/'link/src/obj-nes-100/firmware.stm').read_bytes()
    size,crc,inverse = struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and size+512==len(fw)<=212992
    assert crc==zlib.crc32(fw[512:]) and inverse^crc==0xffffffff
    checks,loader,full,base = [read(work/f'{k}.json') for k in
                               ('checks','loader','full-loader/result','recovery/result')]
    parent = read(ROOT/f'analysis/{parent_report}.json')
    assert digest(fw)==checks['firmware']==loader['firmware']==full['firmware']==base['firmware_sha256']
    assert checks['markers']==modes and checks['menu']['rows']['normal']['released']
    assert full['passed'] and full['compared']==393216 and full['entry_sp']==checks['entry_sp']
    assert loader['cases']==parent['loader']['cases'] and base['safe_return'] and base['base_restored']
    logs = [f'nes-{k}-mmc{edition}{suffix}.txt' for k in ('progress','game-last','budget') for suffix in log_suffixes]
    for name in (f'fpga_mmc{edition}.bi3',f'mmc{edition}.nes',*logs):
        assert name.encode()+b'\0' in fw
    if source is None:
        source = BASE.parent/'MMC894-FIRST-BLOCK-SD-ROOT.zip'
    assert sha(source)==parent['ZIP_SHA256']
    files = {}
    with ZipFile(source) as archive:
        for key,checksum in parent['files'].items():
            data = archive.read(key)
            assert digest(data)==checksum
            name = key.replace(source.stem,folder).replace(str(edition-1),str(edition))
            if name.endswith('.nh1'):
                continue
            if name=='README-KO.txt':
                data = (ROOT/f'docs/nes-mmc{edition}-trial.ko.md').read_bytes()
            elif name.endswith('/firmware.stm'):
                data = fw
            elif name.endswith('/ROM-NOT-INCLUDED.txt'):
                data = data.replace(f'mmc{edition-1}.nes'.encode(),f'mmc{edition}.nes'.encode())
            files[name] = data
    for mode in modes:
        subdir = '' if mode in root_markers else 'NES-DIAG/'
        files[f'{folder}/{subdir}NES {mode} {edition}.nh1'] = b''
    board = parent['board'] if 'board' in parent else parent['reused_board']['BI3']
    assert digest(files[f'{folder}/sd2snes/fpga_mmc{edition}.bi3'])==board
    assert not any(n.endswith('.nes') or 'restore' in n.lower() for n in files)
    report = dict(firmware=digest(fw),flash_bytes=len(fw),physical=False,parent_zip=sha(source),
                  board=board,client=parent['client'],files={n:digest(b) for n,b in files.items()},
                  tests=checks,loader=loader,full_loader=full,base=base)
    files['manifest.json'] = (json.dumps(report,indent=2)+'\n').encode()
    path = work/(folder+'.zip')
    partial = path.with_suffix('.partial')
    with ZipFile(partial,'w') as archive:
        for name,data in files.items():
            archive.writestr(ZipInfo(name),data,compress_type=ZIP_DEFLATED)
    with ZipFile(partial) as archive:
        assert archive.namelist()==list(files) and archive.testzip() is None
        assert all(archive.read(n)==b for n,b in files.items())
    partial.replace(path)
    report['ZIP_SHA256'] = sha(path)
    save(ROOT/f'analysis/{result_name}.json',report)
    print(report['ZIP_SHA256'])


if __name__=='__main__':
    package()
