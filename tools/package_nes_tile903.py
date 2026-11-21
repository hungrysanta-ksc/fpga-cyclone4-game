"""Package and read back the exact fitted board and the qualified ARM link."""
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile,ZipInfo
from package_nes_frame862 import board
from package_nes_trial704 import digest,sha,read,save
from prepare_nes_tile903 import ROOT,PROBES,WORK
from read_nes_tile903 import decode


def pack(temp):
    parent=read(ROOT/'analysis/frame900-901-package.json')['901']
    original=PROBES/'nes-frame900'/parent['ZIP']
    assert sha(original)==parent['ZIP_SHA256']
    bi,checks=board(temp,903,PROBES/'nes-trial890/client02',temp/'nes-tile903-image')
    wire=temp/'nes-tile903-wire/wire.log'
    assert 'PASS903 hidden second bank' in wire.read_text() and 'Errors: 0,' in wire.read_text()
    fw=(WORK/'link/src/obj-nes-100/firmware.stm').read_bytes()
    proof=WORK/'proof'
    assert len(fw)<=212992
    assert read(proof/'timer.json')['passed'] and read(proof/'menu.json')['rows']['normal']['released']
    for key,field in [('menu.json','firmware'),('timer.json','firmware'),('loader.json','firmware'),
                      ('windows.json','firmware_SHA256'),('base/result.json','firmware_sha256')]:
        assert read(proof/key)[field]==digest(fw)
    assert read(proof/'base/result.json')['safe_return']
    cases=read(proof/'sram.json')['cases']
    assert len(cases['normal']['d0_sites'])==4 and not cases['bad-crc']['checked_retire']
    for name in ['frame','budget','progress','game-last']:
        suffix='bin' if name=='frame' else 'txt'
        assert f'/sd2snes/nes-{name}-mmc903.{suffix}\0'.encode() in fw
    runs={}
    for clip in ('early','late'):
        for phase in (1,2):
            folder=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-903-tile'
            r=read(folder/'verified903.json')
            joint=read(folder/'joint.json')
            assert joint['passed'] and joint['firmware_SHA256']==digest(fw) and joint['client_SHA256']==parent['client']
            assert r['RGB']==8 and r['intervals'][0]==r['intervals'][1]
            data=decode(folder/'records.bin')
            assert not any(data['dropped']) and len(data['rows'])==(6 if clip=='late' else 0)
            assert all('token' in row and 'invalid' not in row for row in data['rows'])
            if clip=='late':assert r['last_ACK_difference_clocks']==0
            runs[f'{clip}-{phase}']=dict(**r,last_ACK=joint['frames'][-1]['ACK_masterclock'],trace=sha(folder/'records.bin'))
    files={'README-KO.txt':(ROOT/'docs/nes-mmc903-trial.ko.md').read_bytes()}
    with ZipFile(original) as z:
        for name,expected in parent['members'].items():
            blob=z.read(name)
            assert digest(blob)==expected
            if name=='README-KO.txt':continue
            new=name.replace('901','903')
            if new.endswith('/firmware.stm'):blob=fw
            elif new.endswith('/fpga_mmc903.bi3'):blob=bi
            elif new.endswith('ROM-NOT-INCLUDED.txt'):blob=blob.replace(b'901',b'903')
            files[new]=blob
    assert not any('RESTORE' in k.upper() or k.lower().endswith('.nes') for k in files)
    for name in ('firmware.stm','fpga_mmc903.bi3','NES MMC3 903.nh1'):
        assert sum(k.endswith('/'+name) for k in files)==1
    members={k:digest(v) for k,v in files.items()}
    files['manifest.json']=json.dumps(members,indent=2).encode()
    path=WORK/'MMC903-ADVENTURE-TILE-60SEC-SD-ROOT.zip'
    with ZipFile(path,'w') as z:
        for name,blob in files.items():z.writestr(ZipInfo(name),blob,compress_type=ZIP_DEFLATED)
    with ZipFile(path) as z:
        assert len(z.namelist())==len(files) and z.testzip() is None and all(z.read(k)==v for k,v in files.items())
    save(ROOT/'analysis/tile903-package.json',dict(parent=901,ARM=digest(fw),flash_B=len(fw),free_B=212992-len(fw),
         board=checks,wire=sha(wire),replays=runs,proof={k:sha(proof/k) for k in ('base/result.json','loader.json',
         'windows.json','menu.json','sram.json','timer.json','mode0.bin','mode1.bin','mode2.bin','mode3.bin')},
         ZIP=path.name,ZIP_SHA256=sha(path),members=members))
    print(path.name,sha(path))


if __name__=='__main__':
    pack(Path(sys.argv[1]))
