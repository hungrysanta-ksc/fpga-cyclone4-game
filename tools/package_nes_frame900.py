"""Package each measured link with its own fitted board and the parent's verified SD files."""
import json
import struct
import sys
import zlib
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

from package_nes_frame862 import board
from package_nes_trial704 import digest,sha,read
from prepare_nes_frame900 import ROOT,PROBES,WORK,PARENTS
from read_nes_frame900 import read_trace


def pack(temp,n):
    old,project,arm,client=PARENTS[n]
    parent=read(ROOT/f'analysis/trial{old}-package.json')
    assert sha(PROBES/arm/'src/obj-nes-100/firmware.stm')==parent['ARM']
    assert sha(temp/f'nes-trial816-board{project}/output_files/board.sof')==parent['board']['image']['SOF']
    bi,check=board(temp,n,PROBES/client,temp/f'nes-frame900-final{n}')
    assert 'PASS900 checked' in (temp/f'nes-frame900-wire{n}/wire.log').read_text()
    src=WORK/f'link{n}/src'
    fw=(src/'obj-nes-100/firmware.stm').read_bytes()
    length,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==length+512<=212992 and crc==zlib.crc32(fw[512:])==0xffffffff^inv
    proof=WORK/f'proof{n}'
    assert read(proof/'timer.json')['passed'] and read(proof/'timer.json')['firmware']==digest(fw)
    assert read(proof/'loader.json')['firmware']==digest(fw)
    assert read(proof/'menu.json')['rows']['normal']['released']
    assert read(proof/'base/result.json')['safe_return'] and read(proof/'base/result.json')['firmware_sha256']==digest(fw)
    assert read(proof/'windows.json')['firmware_SHA256']==digest(fw)
    assert 'PASS windows' in (proof/'final-arm.log').read_text()
    sram={}
    if n==901:
        guard=read(proof/'sram.json')
        assert 0x20000000 <= guard['ram'] <= 0x20010000-8 and guard['ram'] % 4 == 0
        assert len(guard['cases']['normal']['d0_sites'])==4
        assert not guard['cases']['bad-crc']['checked_retire']
        sram=dict(address=hex(guard['ram']),sites=guard['cases']['normal']['d0_sites'],
                  stack_gap_bytes=guard['cases']['normal']['static_gap_bytes'])
    replays={}
    for clip in ('early','late'):
        for phase in (1,2):
            key=f'{clip}-{phase}';pair={}
            for name,tag in [('on',''),('control','-control-boot')]:
                folder=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-frame{n}{tag}'
                gate=read(folder/'verified900.json');j=read(folder/'joint.json')
                assert gate['RGB']==6 and gate['count']==6 and j['firmware_SHA256']==digest(fw)
                assert j['client_SHA256']==parent['client']
                trace=read_trace(folder/'records.bin')
                assert trace['mode']==(3 if tag else 0) and not any(trace['dropped'])
                loads=read(folder/'loads898.json')[2:]
                assert [[r['BG'],r['OBJ'],r['map']] for r in trace['rows']]==loads
                pair[name]=dict(intervals=gate['intervals'],reference=gate['reference'],
                                last_ACK=j['frames'][-1]['ACK_masterclock'],probe_ms=[r['probe_ms'] for r in trace['rows']])
            replays[key]=pair
    parent_zip=PROBES/arm.split('/')[0]/f'MMC{old}-ADVENTURE-60SEC-SD-ROOT.zip'
    assert sha(parent_zip)==parent['ZIP_SHA256']
    files={'README-KO.txt':(ROOT/'docs/nes-mmc900-901-trial.ko.md').read_bytes()}
    with ZipFile(parent_zip) as z:
        for oldname in z.namelist():
            if '/' not in oldname or '/NES-DIAG/' in oldname:continue
            blob=z.read(oldname);assert digest(blob)==parent['files'][oldname]
            name=oldname.replace(str(old),str(n))
            if name.endswith('/firmware.stm'):blob=fw
            elif name.endswith(f'/fpga_mmc{n}.bi3'):blob=bi
            elif name.endswith('ROM-NOT-INCLUDED.txt'):blob=blob.replace(str(old).encode(),str(n).encode())
            files[name]=blob
            if name.endswith(f'/NES MMC3 {n}.nh1'):
                for marker in ('CONTROL','EARLY','LATE'):
                    files[name.replace('/NES MMC3 ',f'/NES-DIAG/NES {marker} ')]=blob
    assert not any(name.lower().endswith('.nes') or 'RESTORE' in name.upper() for name in files)
    for marker in ('MMC3','CONTROL','EARLY','LATE'):
        assert sum(name.endswith(f'/NES {marker} {n}.nh1') for name in files)==1
    hashes={k:digest(v) for k,v in files.items()}
    files['manifest.json']=json.dumps(hashes,indent=2).encode()
    path=WORK/f'MMC{n}-ADVENTURE-TRACE-60SEC-SD-ROOT.zip'
    with ZipFile(path,'w') as z:
        for name,blob in files.items():z.writestr(ZipInfo(name),blob,compress_type=ZIP_DEFLATED)
    with ZipFile(path) as z:
        assert len(z.namelist())==len(files) and z.testzip() is None and all(z.read(k)==v for k,v in files.items())
    return dict(parent=old,ARM=digest(fw),flash_B=len(fw),free_B=212992-len(fw),client=parent['client'],
                **check,proof={f:sha(proof/f) for f in ('mode0.bin','mode1.bin','mode2.bin','mode3.bin',
                'timer.json','loader.json','windows.json','menu.json','base/result.json')},D0=sram,
                replays=replays,ZIP=path.name,ZIP_SHA256=sha(path),members=hashes)


if __name__=='__main__':
    result={n:pack(Path(sys.argv[1]),n) for n in PARENTS}
    (ROOT/'analysis/frame900-901-package.json').write_text(json.dumps(result,indent=2)+'\n')
    for v in result.values():print(v['ZIP'],v['ZIP_SHA256'])
