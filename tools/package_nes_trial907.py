"""Bind the 906 bitstream, release ARM and four fixed-workload replays to the SD root."""
import json
import struct
import sys
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from package_nes_frame862 import board
from package_nes_trial704 import digest, read, save, sha
from prepare_nes_trial907 import PROBES, ROOT, WORK


def pack(temp):
    parent=read(ROOT/'analysis/supply905-package.json')
    original=PROBES/'nes-supply905'/parent['ZIP']
    assert sha(original)==parent['ZIP_SHA256']
    client=PROBES/'nes-trial890/client02'
    image,checks=board(temp,906,client,temp/'nes-trial907-image')
    project=temp/'nes-trial816-board906'
    rtl=temp/'nes-peer906/pair'
    logs={}
    for filename in ('nes_tile205.sv','nes_source_tile192.sv'):
        assert sha(project/filename)==sha(rtl/filename)
    for phase in (1,2):
        for name in [f'edge-{phase}']+[f'run-{phase}-{i}' for i in range(3)]:
            f=rtl/(name+'.log')
            expected='directed last slot' if name.startswith('edge') else 'data identity STOP drain cold'
            assert 'PASS906 '+expected in f.read_text(errors='replace') and 'Errors: 0,' in f.read_text(errors='replace')
            logs[name]=sha(f)
    fw=(WORK/'link/src/obj-nes-100/firmware.stm').read_bytes()
    fw_hash=digest(fw)
    size,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and size+512==len(fw)<=212992 and crc==zlib.crc32(fw[512:]) and crc^inv==0xffffffff
    for part,ext in [('budget','txt'),('frame','bin'),('progress','txt'),('game-last','txt')]:
        assert f'/sd2snes/nes-{part}-mmc907.{ext}\0'.encode() in fw
    proof=WORK/'proof'
    for file,key in [('timer.json','firmware'),('menu.json','firmware'),('loader.json','firmware'),
                     ('windows.json','firmware_SHA256'),('base/result.json','firmware_sha256'),('selector.json','firmware')]:
        assert read(proof/file)[key]==fw_hash
    assert read(proof/'timer.json')['passed'] and read(proof/'menu.json')['rows']['normal']['released']
    assert read(proof/'base/result.json')['safe_return']
    cases=read(proof/'sram.json')['cases']
    assert len(cases['normal']['d0_sites'])==4 and not cases['bad-crc']['checked_retire']
    runs={}
    for p in (1,2):
        for state,count in [('warm',15),('cold',20)]:
            folder=f'nes-tile821-obj-jointmirror-p{p}-'
            current=temp/(folder+f'907-{state}-pair')
            baseline=temp/(folder+f'906-{state}-pair')
            j=read(current/'joint.json')
            r=read(current/'verified905.json')
            assert j['passed'] and j['commits']==8 and j['last_status']==1 and j['vram_DMA_B']==22512
            assert j['firmware_SHA256']==fw_hash and j['client_SHA256']==sha(client/'sink165.sfc')
            assert r['RGB']==8 and r['intervals'][1]==count
            for g in range(905,913):
                assert sha(current/f'frame-{g}.rgb')==sha(baseline/f'frame-{g}.rgb')
            runs[f'{state}-p{p}']=dict(intervals=count,RGB=8,final_ACK=r['final_ACK'][1],
                previous_final_ACK=read(baseline/'verified905.json')['final_ACK'][1],vram_DMA_B=j['vram_DMA_B'])
    files={'README-KO.txt':(ROOT/'docs/nes-mmc907-trial.ko.md').read_bytes()}
    with ZipFile(original) as z:
        for name,expected in parent['members'].items():
            blob=z.read(name)
            assert digest(blob)==expected
            if name=='README-KO.txt':continue
            new=name.replace('905','907')
            if new.endswith('/firmware.stm'):blob=fw
            elif new.endswith('/fpga_mmc907.bi3'):blob=image
            elif new.endswith('ROM-NOT-INCLUDED.txt'):blob=blob.replace(b'905',b'907')
            files[new]=blob
    assert not any('RESTORE' in k.upper() or k.lower().endswith('.nes') or '905' in k for k in files)
    members={k:digest(v) for k,v in files.items()}
    files['manifest.json']=json.dumps(members,indent=2).encode()
    path=WORK/'MMC907-ADVENTURE-OBJ-60SEC-SD-ROOT.zip'
    with ZipFile(path,'w') as z:
        for name,blob in files.items():z.writestr(ZipInfo(name),blob,compress_type=ZIP_DEFLATED)
    with ZipFile(path) as z:
        assert set(z.namelist())==set(files) and z.testzip() is None and all(z.read(k)==v for k,v in files.items())
    save(ROOT/'analysis/trial907-package.json',dict(parent=905,fpga=906,ARM=fw_hash,flash_B=len(fw),
         free_B=212992-len(fw),board=checks,RTL_tests=logs,replays=runs,
         selector=read(proof/'selector.json'),proof={k:sha(proof/k) for k in ('sram.json','loader.json','menu.json',
         'timer.json','base/result.json','windows.json','selector.bin')},ZIP=path.name,ZIP_SHA256=sha(path),members=members))
    print(path.name,sha(path))


if __name__=='__main__':pack(Path(sys.argv[1]))
