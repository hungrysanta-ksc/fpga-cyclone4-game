# SPDX-License-Identifier: MIT
"""Package exactly the tested 529 ELF image, paired 526 board, and verified MMC524 menu/base."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zipfile
import zlib

from nes_cf68_pair_preflight import encode, decode
from nes_schedule492 import sha

ROOT=Path(__file__).resolve().parents[1]


def package(a):
    evidence=ROOT/'analysis/flash529-verification.json'
    result=json.loads(evidence.read_text())
    fw=(a.arm/'obj-nes-100/firmware.stm').read_bytes()
    sof=a.board/'output_files/board.sof'
    assert sha(sof)==result['SOF']
    assert hashlib.sha256(fw).hexdigest()==result['firmware_SHA256']
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==result['Flash_B']==size+512<=0x34000
    assert crc==zlib.crc32(fw[512:]) and inverse^crc==0xffffffff
    assert result['saved_B']>=500 and result['base_return']==dict(none=1,program=0,done=0,busy=0,token=0)
    assert [p['start'] for p in result['phases']]==[3000000,3178684]
    for p in result['phases']:
        assert p['replay']['frames']==53 and p['ACK_vs527_ms']<0 and p['ACK_vs524_ms']<0
        assert [p['targets'][g]['VBlanks'] for g in ('952','954')]==[8,7]

    prior=json.loads((ROOT/'analysis/idle524-package.json').read_text())
    assert sha(a.prior)==prior['ZIP_SHA256']
    a.out.mkdir(parents=True,exist_ok=False)
    rbf=a.out/'board.rbf'
    with (a.out/'cpf.log').open('wb') as f:
        subprocess.run([str(a.quartus/'quartus_cpf.exe'),'-c',str(sof.resolve()),str(rbf.resolve())],
                       stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
    image=encode(rbf.read_bytes())
    assert decode(image)==rbf.read_bytes()
    prefix='01-MMC529-SD-ROOT/'
    marker='NES MMC3 529.nh1'
    board_name='sd2snes/fpga_mmc529.bi3'
    rom='sd2snes/nes/mmc529.nes'
    logs=[f'sd2snes/nes-{key}-mmc529.txt' for key in ('progress','budget','game-last')]
    for name in [marker,board_name,rom,*logs]:
        assert (name if name==marker else '/'+name).encode()+b'\0' in fw
    files={prefix+'sd2snes/firmware.stm':fw,prefix+board_name:image,prefix+marker:b'',
           prefix+'sd2snes/nes/ROM-NOT-INCLUDED.txt':b'Copy your own mmc524.nes unchanged as mmc529.nes. CRC32 5a04eed7.\n',
           '읽어주세요.txt':(ROOT/'docs/nes-mmc529-trial.ko.md').read_bytes()}
    with zipfile.ZipFile(a.prior) as z:
        for name in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin'):
            key='01-MMC524-SD-ROOT/'+name
            data=z.read(key)
            assert hashlib.sha256(data).hexdigest()==prior['files'][key]
            files[prefix+name]=data
    report=dict(candidate='MMC529',physical_verified=False,firmware_SHA256=result['firmware_SHA256'],
                SOF_SHA256=sha(sof),RBF_SHA256=sha(rbf),BI3_SHA256=hashlib.sha256(image).hexdigest(),
                evidence_SHA256=sha(evidence),logs=logs,compatible_ROM=prior['compatible_ROM'],base_return=result['base_return'],
                files={n:hashlib.sha256(v).hexdigest() for n,v in files.items()})
    files['manifest.json']=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf8')
    archive=a.out/'MMC529-TRIAL.zip'
    with zipfile.ZipFile(archive,'x') as z:
        for n,d in files.items():
            z.writestr(zipfile.ZipInfo(n),d,compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(files) and all(z.read(n)==d for n,d in files.items())
    report.update(ZIP_SHA256=sha(archive),ZIP_bytes=archive.stat().st_size)
    (a.out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','board','prior','quartus','out'):
        p.add_argument('--'+n,type=Path,required=True)
    package(p.parse_args())
