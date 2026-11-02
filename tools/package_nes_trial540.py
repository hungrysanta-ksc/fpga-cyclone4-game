# SPDX-License-Identifier: MIT
"""Package the verified MMC540 image with pinned menu/base files and distinct log names."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from package_nes_window516 import ROOT, read, sha, encode, decode


def package(a, trial=540):
    previous={540:533,551:540}[trial]
    evidence=ROOT/f'analysis/trial{trial}-verification.json'
    verified=read(evidence)
    assert verified['candidate']==f'MMC{trial}' and verified['timing_criterion']=='matched-mmc529'
    prior=read(ROOT/f'analysis/trial{previous}-package.json')
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
    prefix=f'01-MMC{trial}-SD-ROOT/'
    marker=f'NES MMC3 {trial}.nh1'
    board=f'sd2snes/fpga_mmc{trial}.bi3'
    rom=f'sd2snes/nes/mmc{trial}.nes'
    logs=[f'sd2snes/nes-{name}-mmc{trial}.txt' for name in ('progress','budget','game-last')]
    firmware=image.read_bytes()
    for name in (marker,board,rom,*logs):
        assert (name if name==marker else '/'+name).encode()+b'\0' in firmware
    files={prefix+'sd2snes/firmware.stm':firmware,prefix+marker:b'',prefix+board:bitstream,
           prefix+'sd2snes/nes/ROM-NOT-INCLUDED.txt':f'Copy your own mmc{previous}.nes unchanged as mmc{trial}.nes. CRC32 5a04eed7.\n'.encode('ascii'),
           '읽어주세요.txt':(ROOT/f'docs/nes-mmc{trial}-trial.ko.md').read_bytes()}
    with zipfile.ZipFile(a.prior) as z:
        for name in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin'):
            old=f'01-MMC{previous}-SD-ROOT/'+name
            data=z.read(old)
            assert hashlib.sha256(data).hexdigest()==prior['files'][old]
            files[prefix+name]=data
    result=dict(candidate=f'MMC{trial}',physical_verified=False,timing_criterion=verified['timing_criterion'],
                raw_worst_ns=verified['raw_worst_ns'],firmware_SHA256=sha(image),SOF_SHA256=sha(sof),RBF_SHA256=sha(rbf),
                evidence_SHA256=sha(evidence),compatible_ROM=prior['compatible_ROM'],logs=logs,
                files={name:hashlib.sha256(data).hexdigest() for name,data in files.items()})
    files['manifest.json']=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    archive=a.out/f'MMC{trial}-TRIAL.zip'
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
    p.add_argument('--trial',type=int,choices=(540,551),default=540)
    a=p.parse_args()
    package(a,a.trial)
