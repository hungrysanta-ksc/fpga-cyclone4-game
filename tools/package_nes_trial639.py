# SPDX-License-Identifier: MIT
"""Archive only the checked MMC639 install tree and verify it after reopening."""
import argparse
import hashlib
import json
import struct
import zipfile
import zlib
from pathlib import Path
from check_nes_wire600 import ROOT,read,sha
from nes_cf68_pair_preflight import encode,decode
from nes_schedule492 import funcs
from prepare_nes_trial639 import gate

PREFIX='01-MMC639-SD-ROOT/'
MARKER='NES MMC3 639.nh1'
LOGS=[f'sd2snes/nes-{kind}-mmc639.txt' for kind in ('progress','budget','game-last')]
IMAGE='sd2snes/fpga_mmc639.bi3'
ROM='sd2snes/nes/mmc639.nes'


def package(a):
    edge=gate(a.edge)
    selected=read(ROOT/'analysis/front638-verification.json')
    assert selected['passed']['both']
    old=a.base/'obj-nes-100'
    new=a.arm/'obj-nes-100'
    assert all(sha(old/'firmware.stm')==c['modes']['both']['schedule']['image'] for c in selected['cases'])
    original=(old/'firmware.stm').read_bytes()
    fw=(new/'firmware.stm').read_bytes()
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and size+512==len(fw)<=212992
    assert zlib.crc32(fw[512:])==crc and crc^inverse==0xffffffff
    assert original[32:].replace(b'577',b'639')==fw[32:]
    functions=funcs(old/'sd2snes.elf')
    assert functions and funcs(new/'sd2snes.elf')==functions
    for n in (MARKER,*('/'+f for f in [IMAGE,ROM,*LOGS])):
        assert n.encode()+b'\0' in fw and n.replace('639','577').encode()+b'\0' not in fw
    menu=read(a.checks/'menu.json')
    windows=read(a.checks/'windows.json')
    digest=sha(new/'firmware.stm')
    assert menu['firmware']==windows['firmware_SHA256']==digest and menu['marker_cases']==4
    assert [(x['start_s'],x['end_s']) for x in windows['accepted']]==[(5,40),(40,55)]
    recovery={k:read(a.checks/f'base-{k}/result.json') for k in ('none','program','done','busy','token')}
    for k,r in recovery.items():
        assert r['firmware_sha256']==digest and r['passed']
        assert r['safe_return']==r['base_restored']==int(k=='none')
        assert r['config_paths']==['/'+IMAGE,'/sd2snes/fpga_base.bi3']
    board=read(ROOT/'analysis/dma637-verification.json')['board']['nes-dma637-board01']
    for n,h in board['SHA'].items():
        assert sha(a.board/'output_files'/n)==h
    romcheck=read(a.romcheck/'result.json')
    assert romcheck['program']==sha(a.board/'sink-program.hex')==sha(a.client/'sink-program.hex')
    assert romcheck['bytes']==5120 and romcheck['client']==edge['client']==sha(a.client/'sink165.sfc')
    assert romcheck['bus']==sha(a.board/'nes_sink_bus165.sv') and romcheck['log']==sha(a.romcheck/'vsim.log')
    cpf=(a.image/'cpf.log').read_text(errors='replace')
    assert 'quartus_cpf -c' in cpf and 'was successful' in cpf
    raw=(a.image/'board.rbf').read_bytes()
    bi3=(a.image/'fpga_mmc639.bi3').read_bytes()
    assert encode(raw)==bi3 and decode(bi3)==raw
    programmer=read(a.programmer/'result.json')
    assert programmer['passed'] and programmer['image_sha256']==sha(a.image/'fpga_mmc639.bi3')
    assert programmer['rbf_sha256']==sha(a.image/'board.rbf')
    old_release=read(ROOT/'analysis/trial613-package.json')
    assert sha(a.prior)==old_release['ZIP_SHA256']
    files={PREFIX+'sd2snes/firmware.stm':fw,PREFIX+IMAGE:bi3,PREFIX+MARKER:b'',
           PREFIX+'sd2snes/nes/ROM-NOT-INCLUDED.txt':b'Copy your existing mmc613.nes to mmc639.nes. CRC32 5a04eed7.\n',
           'README-KO.txt':(ROOT/'docs/nes-mmc639-trial.ko.md').read_bytes()}
    with zipfile.ZipFile(a.prior) as z:
        for n in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin'):
            key='01-MMC613-SD-ROOT/'+n
            data=z.read(key)
            assert hashlib.sha256(data).hexdigest()==old_release['files'][key]
            files[PREFIX+n]=data
    assert not any('RESTORE' in n.upper() or n.lower().endswith(('.nes','.sav','.srm','.rtc')) for n in files)
    result=dict(candidate='MMC639',gate='limited physical trial',physical_verified=False,
                firmware_SHA256=digest,ELF=sha(new/'sd2snes.elf'),identical_functions=len(functions),
                Flash_B=len(fw),Flash_free_B=212992-len(fw),board=board,ROM_read=romcheck,
                beam=edge,menu=menu,windows=windows,recovery=recovery,programmer=programmer,
                required_ROM={**old_release['required_ROM'],'path':ROM},logs=LOGS,
                ROM_included=False,RESTORE_included=False,
                files={n:hashlib.sha256(data).hexdigest() for n,data in files.items()})
    files['manifest.json']=(json.dumps(result,indent=2)+'\n').encode()
    a.out.mkdir(parents=True,exist_ok=False)
    archive=a.out/'MMC639-TRIAL.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for n,data in files.items():z.writestr(n,data)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and sorted(z.namelist())==sorted(files)
        assert all(z.read(n)==data for n,data in files.items())
    result.update(ZIP_SHA256=sha(archive),ZIP_bytes=archive.stat().st_size)
    a.report.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(archive,result['ZIP_SHA256'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ('arm','base','edge','board','client','romcheck','checks','image','programmer','prior','out','report'):
        parser.add_argument('--'+k,required=True,type=Path)
    package(parser.parse_args())
