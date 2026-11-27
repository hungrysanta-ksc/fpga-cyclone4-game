"""Package the CHR RAM trial against the physically checked 1050 installation."""
import csv
import json
from pathlib import Path
import struct
import zipfile
import zlib

from package_ff3_battle1047 import digest, read
from package_nes_kirby1027 import programmer, timing


def package(work, route):
    root=Path(__file__).resolve().parents[1]
    previous=read(root/'analysis/ff3-1050.json')
    old=work.parent/'nes-ff3-1050/FF3-1050-NES-PLAY-SD-ROOT.zip'
    assert digest(old.read_bytes())==previous['ZIP_SHA256']
    with zipfile.ZipFile(old) as archive:
        files={name:archive.read('sd2snes/'+name) for name in previous['files']}
    assert {name:digest(data) for name,data in files.items()}==previous['files']
    board=timing(route)
    with (route/'sram.tsv').open() as file:
        rows=list(csv.DictReader(file,delimiter='\t'))
    corners={r['corner'] for r in rows}
    assert len(corners)==3
    for corner in corners:
        assert {(r['group'],r['check']) for r in rows if r['corner']==corner}=={
            (port,check) for port in ('input','output') for check in ('setup','hold')}
    fw=(work/'link/src/obj-nes-100/firmware.stm').read_bytes()
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==size+512<=212992 and zlib.crc32(fw[512:])==crc==inverse^0xffffffff
    for name,ext in [('game-last','txt'),('progress','txt'),('frame','bin')]:
        assert f'nes-{name}-ff31051.{ext}\0'.encode() in fw
    io,ret=read(work/'io.json'),read(work/'return/result.json')
    assert io['firmware_sha256']==ret['firmware_sha256']==digest(fw)
    assert ret['passed'] and ret['safe_return'] and ret['base_restored']
    assert io['state_bytes']==21264 and read(work/'slots.json')['distinct_slots_reloaded']==4
    assert 'PASS1051 64 narrow headers' in (work/'chr.log').read_text(errors='replace')
    assert 'PASS FF3 loader 524288' in (work/'loader.log').read_text(errors='replace')
    evidence=read(root/'analysis/ff3-airship1051.json')
    assert evidence['firmware_sha256']==digest(fw)
    assert evidence['sof_sha256']==digest((route/'board.sof').read_bytes())
    for trial in evidence['warm_replay'].values():
        assert trial['tile_bytes'][1]<trial['tile_bytes'][0]
    assert (work/'client/sink-program.hex').read_bytes()==(work.parent/'nes-ff3-1050/client/sink-program.hex').read_bytes()
    packed,pgm=programmer(route,work,1051)
    files.update({'nes-chrram.bi3':packed,'firmware.stm':fw})
    report=dict(edition=1051,hardware_tested=False,flash_bytes=len(fw),route=board,rbf=pgm['rbf_sha256'],
                files={k:digest(v) for k,v in files.items()})
    name='FF3-1051-NES-PLAY-SD-ROOT.zip'
    out=work/name
    tmp=out.with_suffix('.tmp')
    with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for k,v in files.items():archive.writestr('sd2snes/'+k,v)
        archive.writestr('README-KO.txt',(root/'docs/nes-ff3-airship1051.ko.md').read_bytes())
        archive.writestr('manifest.json',json.dumps(report,indent=2))
    with zipfile.ZipFile(tmp) as archive:
        assert archive.testzip() is None and all(archive.read('sd2snes/'+k)==v for k,v in files.items())
    tmp.replace(out)
    report['ZIP_SHA256']=digest(out.read_bytes())
    (work/'package.json').write_text(json.dumps(report,indent=2)+'\n')
    print(out,report['ZIP_SHA256'])


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('work','route'):ap.add_argument(name,type=Path)
    args=ap.parse_args()
    package(args.work,args.route)
