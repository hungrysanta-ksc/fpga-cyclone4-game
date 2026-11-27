"""Issue both experimental policies only against the same validated FPGA image."""
import argparse
import csv
import json
from pathlib import Path
import struct
import zipfile
import zlib
from package_ff3_battle1047 import digest,read
from package_nes_kirby1027 import programmer,timing

ROOT=Path(__file__).resolve().parents[1]

def package(work,route):
    original=work.parent/'nes-ff3-1051B/FF3-1051-NES-PLAY-SD-ROOT.zip'
    previous=read(work.parent/'nes-ff3-1051B/package.json')
    assert digest(original.read_bytes())==previous['ZIP_SHA256']
    with zipfile.ZipFile(original) as f:
        files={n:f.read('sd2snes/'+n) for n in previous['files']}
    assert {n:digest(d) for n,d in files.items()}==previous['files']
    board=timing(route)
    with (route/'sram.tsv').open() as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    assert len({r['corner'] for r in rows})==3
    for c in {r['corner'] for r in rows}:
        assert {(r['group'],r['check']) for r in rows if r['corner']==c}=={
            (g,k) for g in ('input','output') for k in ('setup','hold')}
    assert 'PASS1052' in (work/'trace.log').read_text(errors='replace')
    assert 'PASS1051' in (work/'chr.log').read_text(errors='replace')
    assert 'PASS FF3 loader 524288' in (work/'loader.log').read_text(errors='replace')
    r=read(work/'route.json')['1']
    assert [sum(row['tile_bytes'] for row in r[k][2:]) for k in ('page','group')]==[4864,832]
    packed,program=programmer(route,work,1052)
    files['nes-chrram.bi3']=packed
    result=dict(board=board,rbf_sha256=program['rbf_sha256'],replay_warm_bytes=[4864,832],editions={})
    for ed in (1052,1053):
        d=work/str(ed)
        fw=(d/'link/src/obj-nes-100/firmware.stm').read_bytes()
        size,crc,inv=struct.unpack_from('<III',fw,8)
        assert fw[:4]==b'STM3' and len(fw)==size+512<=212992 and zlib.crc32(fw[512:])==crc==inv^0xffffffff
        assert all(f'nes-{n}-ff3{ed}.{ext}\0'.encode() in fw for n,ext in [('frame','bin'),('game-last','txt'),('progress','txt')])
        io,ret=read(d/'io.json'),read(d/'return/result.json')
        assert io['firmware_sha256']==ret['firmware_sha256']==digest(fw)
        assert ret['passed'] and ret['safe_return'] and ret['base_restored']
        assert read(d/'slots.json')['distinct_slots_reloaded']==4 and read(d/'movement.json')['groups']==64
        files['firmware.stm']=fw
        manifest=dict(edition=ed,bytes=len(fw),policy='1KiB' if ed==1052 else '128B',
                      files={n:digest(v) for n,v in files.items()})
        out=work/f'FF3-{ed}-MOVEMENT-SD-ROOT.zip'
        tmp=out.with_suffix('.tmp')
        with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():z.writestr('sd2snes/'+name,data)
            z.writestr('README-KO.txt',(ROOT/'docs/nes-ff3-movement1052.ko.md').read_bytes())
            z.writestr('manifest.json',json.dumps(manifest,indent=2))
        with zipfile.ZipFile(tmp) as z:
            assert z.testzip() is None and all(z.read('sd2snes/'+k)==v for k,v in files.items())
        tmp.replace(out)
        result['editions'][ed]=dict(manifest,zip_sha256=digest(out.read_bytes()))
        print(out,result['editions'][ed]['zip_sha256'])
    (work/'package.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work',type=Path);parser.add_argument('route',type=Path)
    args=parser.parse_args();package(args.work,args.route)
