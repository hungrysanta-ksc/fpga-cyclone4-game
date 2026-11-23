"""Package the final link alongside the byte-identical, hardware-tested MMC955 board."""
import struct
import sys
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import zlib
import check_nes_header950 as headers
from check_nes_dense956 import check
from package_nes_trial704 import digest, read, sha
from package_nes_trial872 import write_verified_archive
from prepare_nes_dense956 import PARENT, ROOT, SOURCE, WORK


def package(capture):
    reference=read(ROOT/'analysis/trial955-package.json')
    original=PARENT/'MMC955-ADVENTURE-60SEC-SD-ROOT.zip'
    assert sha(original)==reference['ZIP_SHA256']
    with ZipFile(original) as z:
        name,=[p for p in z.namelist() if p.endswith('/fpga_mmc955.bi3')]
        board=z.read(name)
    assert digest(board)==reference['image']['BI3']
    fw=(SOURCE/'obj-nes-100/firmware.stm').read_bytes()
    n,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==512+n<=212992 and crc==zlib.crc32(fw[512:]) and crc^inv==0xffffffff
    for filename in ('mmc956.nes','fpga_mmc956.bi3','nes-progress-mmc956.txt','nes-game-last-mmc956.txt',
                     'nes-budget-mmc956.txt','nes-frame-mmc956.bin',' 956.nh1'):
        assert filename.encode()+b'\0' in fw and filename.replace('956','955').encode()+b'\0' not in fw
    proof=WORK/'proof'
    windows=read(proof/'windows.json')
    assert windows['firmware_SHA256']==digest(fw) and windows['accepted']==reference['windows']['accepted']
    timer,loader,menu=(read(proof/f'{s}.json') for s in ('timer','loader','menu'))
    assert all(r['firmware']==digest(fw) for r in (timer,loader,menu))
    assert timer['passed'] and menu['rows']['normal']['released'] and loader['cases']==reference['loader']['cases']
    assert loader['rom']==reference['loader']['rom']
    base=read(proof/'base/result.json')
    assert base['firmware_sha256']==digest(fw) and base['safe_return'] and base['base_restored'] and base['passed']
    assert base['config_paths']==['/sd2snes/fpga_mmc956.bi3','/sd2snes/fpga_base.bi3']
    rx=read(proof/'sram.json')['cases']
    assert len(rx['normal']['d0_sites'])==4 and rx['normal']['checked_retire'] and not rx['bad-crc']['checked_retire']
    with patch.object(headers,'work',lambda _:WORK):
        headers.test('release')
    cases=check(capture)
    report=dict(edition=956,physical=False,firmware=digest(fw),Flash_B=len(fw),free_B=212992-len(fw),
                board_BI3=digest(board),client=reference['client'],mode0_bytes=(proof/'mode0.bin').stat().st_size,
                timer_pass=True,base_restore=True,bad_crc_rejected=True,SRAM_D0_sites=4,MMC955_input=sha(capture),
                recorder_replay=cases,identity=read(WORK/'identity950.json'))
    write_verified_archive(WORK,reference,fw,board,report)


if __name__=='__main__':
    package(Path(sys.argv[1]))
