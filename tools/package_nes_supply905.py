"""Validate final-link evidence and generate the install-only SD root."""
import json
import struct
import sys
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile,ZipInfo
from package_nes_frame862 import board
from package_nes_trial704 import digest,sha,read,save
from prepare_nes_supply905 import ROOT,PROBES,WORK
from read_nes_supply905 import decode
from check_nes_supply905_pages import check as wire_pages

def pack(temp):
    parent=read(ROOT/'analysis/tile903-package.json')
    original=PROBES/'nes-tile903'/parent['ZIP']
    assert sha(original)==parent['ZIP_SHA256']
    bi,checks=board(temp,905,PROBES/'nes-trial890/client02',temp/'nes-supply905-image')
    wire=temp/'nes-supply905-wire/wire.log'
    assert 'PASS905 first E9' in wire.read_text() and 'Errors: 0,' in wire.read_text()
    wire_pages(temp)
    project=temp/'nes-trial816-board905'
    for name in ('nes_screen_status151','nes_supply905','nes_native_arbiter165','nes_plan_spi200','nes_bulk_aperture188'):
        assert sha(project/(name+'.sv'))==sha(wire.parent/(name+'.sv'))
    assert sha(project/'nes_supply905.sv')==sha(ROOT/'tests/nes-functional/nes_supply905.sv')
    fw=(WORK/'link/src/obj-nes-100/firmware.stm').read_bytes();proof=WORK/'proof'
    size,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and size+512==len(fw)<=212992 and crc==zlib.crc32(fw[512:]) and crc^inv==0xffffffff
    for name in ('budget','frame','progress','game-last'):
        ext='bin' if name=='frame' else 'txt'
        assert f'/sd2snes/nes-{name}-mmc905.{ext}\0'.encode() in fw
    assert read(proof/'timer.json')['passed'] and read(proof/'menu.json')['rows']['normal']['released']
    for k,field in [('timer.json','firmware'),('menu.json','firmware'),('loader.json','firmware'),('windows.json','firmware_SHA256'),('base/result.json','firmware_sha256')]:
        assert read(proof/k)[field]==digest(fw)
    assert read(proof/'base/result.json')['safe_return']
    cases=read(proof/'sram.json')['cases']
    assert len(cases['normal']['d0_sites'])==4 and not cases['bad-crc']['checked_retire']
    runs={}
    for clip in ('early','late'):
        for phase in (1,2):
            p=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-905-supply'
            r=read(p/'verified905.json');j=read(p/'joint.json')
            assert j['passed'] and j['firmware_SHA256']==digest(fw)
            assert j['client_SHA256']==sha(PROBES/'nes-trial890/client02/sink165.sfc') and j['last_status']==1
            d=decode(p/'records.bin')
            assert r['RGB']==8 and len(d['rows'])==(6 if clip=='late' else 0)
            assert r['intervals'][0]==r['intervals'][1] and (clip!='late' or d['selected'])
            runs[f'{clip}-{phase}']=r
    files={'README-KO.txt':(ROOT/'docs/nes-mmc905-trial.ko.md').read_bytes()}
    with ZipFile(original) as z:
        for name,expected in parent['members'].items():
            blob=z.read(name);assert digest(blob)==expected
            if name=='README-KO.txt':continue
            new=name.replace('903','905')
            if new.endswith('/firmware.stm'):blob=fw
            elif new.endswith('fpga_mmc905.bi3'):blob=bi
            elif new.endswith('ROM-NOT-INCLUDED.txt'):blob=blob.replace(b'903',b'905')
            files[new]=blob
    assert not any('RESTORE' in k.upper() or k.lower().endswith('.nes') for k in files)
    members={k:digest(v) for k,v in files.items()}
    files['manifest.json']=json.dumps(members,indent=2).encode()
    path=WORK/'MMC905-ADVENTURE-SUPPLY-60SEC-SD-ROOT.zip'
    with ZipFile(path,'w') as z:
        for name,blob in files.items():z.writestr(ZipInfo(name),blob,compress_type=ZIP_DEFLATED)
    with ZipFile(path) as z:
        assert len(z.namelist())==len(files) and z.testzip() is None and all(z.read(k)==v for k,v in files.items())
    save(ROOT/'analysis/supply905-package.json',dict(parent=903,ARM=digest(fw),flash_B=len(fw),free_B=212992-len(fw),
        board=checks,wire=sha(wire),replays=runs,proof={k:sha(proof/k) for k in ('sram.json','loader.json','menu.json','timer.json','base/result.json','windows.json','rtl-pages.bin')},
        ZIP=path.name,ZIP_SHA256=sha(path),members=members))
    print(path.name,sha(path))
if __name__=='__main__':pack(Path(sys.argv[1]))
