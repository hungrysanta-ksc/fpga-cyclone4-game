# SPDX-License-Identifier: MIT
"""Package MMC533 with the verified base/menu and an explicit timing acceptance criterion."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from nes_cf68_pair_preflight import encode,decode
from package_nes_window516 import ROOT,read,sha

def package(a):
    ev=ROOT/'analysis/trial533-verification.json'
    r=read(ev)
    assert r['relevant_paths_pass'] and r['base_return']==dict(none=1,program=0,done=0,busy=0,token=0)
    if a.timing=='matched-mmc529':
        assert r['all_raw_summary_rows_equal'] and r['unconstrained_equal'] and all(r['path_inventory_equal'].values())
    else:assert r['all_STA_slacks_nonnegative']
    fw=a.arm/'obj-nes-100/firmware.stm'
    sof=a.board/'output_files/board.sof'
    assert sha(fw)==r['firmware_SHA256'] and sha(sof)==r['SOF_SHA256']
    prev=read(ROOT/'analysis/flash529-package.json')
    assert sha(a.prior)==prev['ZIP_SHA256']
    a.out.mkdir(parents=True,exist_ok=False)
    rbf=a.out/'board.rbf'
    with (a.out/'cpf.log').open('wb') as f:
        subprocess.run([str(a.quartus/'quartus_cpf.exe'),'-c',str(sof.resolve()),str(rbf.resolve())],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
    raw=rbf.read_bytes()
    bitstream=encode(raw)
    assert raw and decode(bitstream)==raw
    prefix='01-MMC533-SD-ROOT/'
    marker='NES MMC3 533.nh1'
    board_name='sd2snes/fpga_mmc533.bi3'
    rom='sd2snes/nes/mmc533.nes'
    logs=[f'sd2snes/nes-{key}-mmc533.txt' for key in ('progress','budget','game-last')]
    image=fw.read_bytes()
    for name in [marker,board_name,rom,*logs]:
        assert (name if name==marker else '/'+name).encode()+b'\0' in image
    files={prefix+'sd2snes/firmware.stm':image,prefix+board_name:bitstream,prefix+marker:b'',
           prefix+'sd2snes/nes/ROM-NOT-INCLUDED.txt':b'Copy your own mmc529.nes unchanged as mmc533.nes. CRC32 5a04eed7.\n',
           '읽어주세요.txt':(ROOT/'docs/nes-mmc533-trial.ko.md').read_bytes()}
    with zipfile.ZipFile(a.prior) as z:
        for n in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin'):
            old='01-MMC529-SD-ROOT/'+n
            data=z.read(old)
            assert hashlib.sha256(data).hexdigest()==prev['files'][old]
            files[prefix+n]=data
    report=dict(candidate='MMC533',physical_verified=False,timing_criterion=a.timing,raw_worst_ns=r['raw_worst_ns'],
                SOF_SHA256=sha(sof),RBF_SHA256=sha(rbf),evidence_SHA256=sha(ev),logs=logs,
                compatible_ROM=prev['compatible_ROM'],files={n:hashlib.sha256(v).hexdigest() for n,v in files.items()})
    files['manifest.json']=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
    archive=a.out/'MMC533-TRIAL.zip'
    with zipfile.ZipFile(archive,'x') as z:
        for n,d in files.items():z.writestr(zipfile.ZipInfo(n),d,compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(files) and all(z.read(n)==d for n,d in files.items())
    report.update(ZIP_SHA256=sha(archive),ZIP_bytes=archive.stat().st_size)
    (a.out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('arm','board','prior','quartus','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--timing',choices=('full','matched-mmc529'),default='full')
    package(p.parse_args())
