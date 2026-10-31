# SPDX-License-Identifier: MIT
"""Build a local 516 trial from the measured board, an identical-code labeled ARM, and pinned MMC509 base/menu."""
import argparse
import hashlib
import json
import struct
import subprocess
import zipfile
import zlib
from pathlib import Path
from nes_cf68_pair_preflight import encode, decode
from nes_schedule492 import funcs, sha

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
LABELS=('nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION')
def prepare(a):
    known=read(ROOT/'analysis/service509-package.json')
    assert sha(a.base/'obj-nes-100/firmware.stm')==known['firmware_SHA256']
    a.out.mkdir(parents=True,exist_ok=False)
    for name in LABELS:
        p=a.base/name
        s=p.read_text();assert '509' in s
        (a.out/name).write_text(s.replace('509','516'),encoding='utf8',newline='\n')

def pack(a):
    old=read(ROOT/'analysis/service509-package.json');r=read(ROOT/'analysis/window516-verification.json')
    assert sha(a.prior)==old['ZIP_SHA256']
    old_fw=a.base/'obj-nes-100/firmware.stm';fw=a.arm/'obj-nes-100/firmware.stm'
    assert sha(old_fw)==old['firmware_SHA256']
    before,after=old_fw.read_bytes(),fw.read_bytes()
    functions=funcs(a.arm/'obj-nes-100/sd2snes.elf')
    assert len(functions)>700 and functions==funcs(a.base/'obj-nes-100/sd2snes.elf')
    assert len(before)==len(after)==212956 and before[:4]==after[:4]==b'STM3'
    assert before[32:].replace(b'509',b'516')==after[32:]
    n,crc,inverse=struct.unpack_from('<III',after,8)
    assert n==len(after)-512 and zlib.crc32(after[512:])==crc and crc^inverse==0xffffffff
    for path in ('/sd2snes/fpga_mmc516.bi3','/sd2snes/nes/mmc516.nes','nes-progress-mmc516.txt','nes-budget-mmc516.txt','nes-game-last-mmc516.txt'):
        assert path.encode() in after,path
    arm_guard=read(a.guards/'result.json')
    assert arm_guard['passed'] and arm_guard['baseline_SHA256']==sha(old_fw) and arm_guard['candidate_SHA256']==sha(fw) and len(arm_guard['rows'])==40
    recover={}
    for fault in ('none','program','done','busy','token'):
        check=read(a.guards.parent/f'labelrecovery-{fault}/result.json')
        assert check['passed'] and check['firmware_sha256']==sha(fw)
        assert [check['safe_return'],check['base_restored']]==r['ARM_base_recovery'][fault]
        recover[fault]=check['safe_return']
    board=r['boards'][a.kind]
    for k,v in board['report_SHA256'].items():assert sha(a.board/k)==v
    for view in ('implementation','nominal'):
        assert all(board[f'{view}_{c}_ns']>=0 for c in ('setup','hold'))
    assert all(r['runs'][a.kind+i]['later_mean_ms']<r['runs']['base'+i]['later_mean_ms'] for i in ('01','02'))
    assert r['ARM_base_recovery']['none']==[1,1] and r['fill_guards']['stop64']['DMA_B']==64
    a.out.mkdir(parents=True,exist_ok=False)
    sof=a.board/'output_files/board.sof';assert sha(sof)==board['SOF_SHA256'];rbf=a.out/'board.rbf'
    with (a.out/'cpf.log').open('wb') as log:
        subprocess.run([str(a.quartus/'quartus_cpf.exe'),'-c',str(sof),str(rbf)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    raw=rbf.read_bytes();image=encode(raw);assert decode(image)==raw
    active='01-MMC516-SD-ROOT/'
    files={}
    with zipfile.ZipFile(a.prior) as z:
        assert z.testzip() is None
        for name in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin'):
            path='01-MMC509-SD-ROOT/'+name
            b=z.read(path);assert hashlib.sha256(b).hexdigest()==old['files'][path]['SHA256']
            files[active+name]=b
    files[active+'sd2snes/firmware.stm']=after
    files[active+'sd2snes/fpga_mmc516.bi3']=image
    files[active+'NES MMC3 516.nh1']=b''
    files[active+'sd2snes/nes/ROM-NOT-INCLUDED.txt']=b'Copy your original mmc509.nes to mmc516.nes without changing its bytes. CRC32 5a04eed7.\n'
    files['읽어주세요.txt']=(ROOT/'docs/nes-mmc516-trial.ko.md').read_bytes()
    assert not any('RESTORE' in name or name.lower().endswith(('.nes','.sav','.srm','.rtc')) for name in files)
    logs=['sd2snes/nes-'+name+'-mmc516.txt' for name in ('progress','budget','game-last')]
    manifest=dict(candidate='MMC516',selected=a.kind,physical_verified=False,ROM_included=False,RESTORE_included=False,
                  required_ROM={**old['required_ROM'],'path':'sd2snes/nes/mmc516.nes'},logs=logs,
                  unchanged_ARM_functions=len(functions),ARM_response_checks=len(arm_guard['rows']),base_return=recover,firmware_SHA256=sha(fw),SOF_SHA256=sha(sof),RBF_SHA256=sha(rbf),
                  BI3_SHA256=hashlib.sha256(image).hexdigest(),evidence_SHA256=sha(ROOT/'analysis/window516-verification.json'),
                  files={k:hashlib.sha256(b).hexdigest() for k,b in files.items()})
    files['manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf8')
    archive=a.out/'MMC516-TRIAL.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for k,b in files.items():z.writestr(k,b)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(files) and all(z.read(k)==b for k,b in files.items())
    save(a.out/'result.json',dict(**manifest,ZIP_SHA256=sha(archive),ZIP_bytes=archive.stat().st_size))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('labels','package'));p.add_argument('--kind',choices=('fill','both'))
    for k in ('base','arm','board','prior','out','quartus','guards'):p.add_argument('--'+k,type=Path)
    a=p.parse_args();(prepare if a.mode=='labels' else pack)(a)
