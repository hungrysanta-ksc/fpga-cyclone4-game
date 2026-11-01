# SPDX-License-Identifier: MIT
"""Package the verified MMC540 image with pinned menu/base files and distinct log names."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from package_nes_window516 import ROOT, read, sha, encode, decode


def package(a):
    evidence=ROOT/'analysis/trial540-verification.json'
    verified=read(evidence)
    assert verified['timing_criterion']=='matched-mmc529'
    prior=read(ROOT/'analysis/trial533-package.json')
    assert sha(a.prior)==prior['ZIP_SHA256']
    image=a.arm/'obj-nes-100/firmware.stm'
    sof=a.board/'output_files/board.sof'
    assert sha(image)==verified['firmware_SHA256'] and sha(sof)==verified['SOF_SHA256']
    a.out.mkdir(parents=True,exist_ok=False)
    rbf=a.out/'board.rbf'
    with (a.out/'cpf.log').open('wb') as log:
        subprocess.run([str(a.quartus/'quartus_cpf.exe'),'-c',str(sof.resolve()),str(rbf.resolve())],
                       stdout=log,stderr=subprocess.STDOUT,timeout=300,check=True)
    raw=rbf.read_bytes()
    bitstream=encode(raw)
    assert raw and decode(bitstream)==raw
    prefix='01-MMC540-SD-ROOT/'
    marker='NES MMC3 540.nh1'
    board='sd2snes/fpga_mmc540.bi3'
    rom='sd2snes/nes/mmc540.nes'
    logs=[f'sd2snes/nes-{name}-mmc540.txt' for name in ('progress','budget','game-last')]
    firmware=image.read_bytes()
    for name in (marker,board,rom,*logs):
        assert (name if name==marker else '/'+name).encode()+b'\0' in firmware
    files={prefix+'sd2snes/firmware.stm':firmware,prefix+marker:b'',prefix+board:bitstream,
           prefix+'sd2snes/nes/ROM-NOT-INCLUDED.txt':b'Copy your own mmc533.nes unchanged as mmc540.nes. CRC32 5a04eed7.\n',
           '읽어주세요.txt':(ROOT/'docs/nes-mmc540-trial.ko.md').read_bytes()}
    with zipfile.ZipFile(a.prior) as z:
        for name in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin'):
            old='01-MMC533-SD-ROOT/'+name
            data=z.read(old)
            assert hashlib.sha256(data).hexdigest()==prior['files'][old]
            files[prefix+name]=data
    result=dict(candidate='MMC540',physical_verified=False,timing_criterion=verified['timing_criterion'],
                raw_worst_ns=verified['raw_worst_ns'],firmware_SHA256=sha(image),SOF_SHA256=sha(sof),RBF_SHA256=sha(rbf),
                evidence_SHA256=sha(evidence),compatible_ROM=prior['compatible_ROM'],logs=logs,
                files={name:hashlib.sha256(data).hexdigest() for name,data in files.items()})
    files['manifest.json']=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    archive=a.out/'MMC540-TRIAL.zip'
    with zipfile.ZipFile(archive,'x') as z:
        for name,data in files.items():
            z.writestr(zipfile.ZipInfo(name),data,compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(files)
        assert all(z.read(name)==data for name,data in files.items())
    result.update(ZIP_SHA256=sha(archive),ZIP_bytes=archive.stat().st_size)
    (a.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','board','prior','quartus','out'):
        p.add_argument('--'+name,type=Path,required=True)
    package(p.parse_args())
