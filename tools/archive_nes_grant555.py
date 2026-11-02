# SPDX-License-Identifier: MIT
"""Preserve the selected local timing traces and verify the archive after writing."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def archive(probe, traces, out, report):
    evidence = json.loads(report.read_bytes())
    files = [(report, 'public/' + report.name)]
    # Only inputs/outputs selected by the analysis. Do not sweep the portable
    # emulator, OS temp tree, or another run's license/config files.
    for phase, variants in enumerate(evidence['phases'], 1):
        for row in variants.values():
            for key in ('trace_folder', 'audit_folder'):
                folder = traces / row[key]
                files.extend((f, folder.name+'/'+f.relative_to(folder).as_posix())
                             for f in sorted(folder.rglob('*')) if f.is_file())
        fixed = traces / f'nes-grant555-fixed{phase}'
        files.extend((f,fixed.name+'/'+f.relative_to(fixed).as_posix())
                     for f in sorted(fixed.rglob('*')) if f.is_file())
    for folder in (traces/'nes-grant555-edge02', traces/'nes-grant555-stop01', traces/'nes-grant555-priority01',
                   probe/'client01', probe/'patch01'):
        files.extend((f,folder.name+'/'+f.relative_to(folder).as_posix()) for f in sorted(folder.rglob('*')) if f.is_file())
    for name in ('guards.json','credit.json','menu.json','window.json','ARM02/build.log','ARM02/size.log',
                 'ARM02/src/obj-nes-100/sd2snes.elf','ARM02/src/obj-nes-100/firmware.stm'):
        files.append((probe/name,'build/'+name))
    out.mkdir(parents=True,exist_ok=False)
    dst = out/'evidence.zip'
    with zipfile.ZipFile(dst,'x',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for f,name in files:
            z.write(f,name)
    with zipfile.ZipFile(dst) as z:
        assert len(z.namelist())==len(set(z.namelist()))==len(files)
        for f,name in files:
            assert z.read(name)==f.read_bytes(),name
    result = dict(files=len(files),sha256=hashlib.sha256(dst.read_bytes()).hexdigest())
    (out/'verified.json').write_text(json.dumps(result)+'\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for key in ('probe','traces','out','report'):
        p.add_argument('--'+key,required=True,type=Path)
    a=p.parse_args()
    print(archive(a.probe,a.traces,a.out,a.report))
