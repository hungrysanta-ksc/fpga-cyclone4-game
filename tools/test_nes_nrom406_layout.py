# SPDX-License-Identifier: MIT
"""Build and run narrow mapper0 header/layout C unit, without production IO."""
import argparse
import json
import subprocess
from pathlib import Path
from nes_delta231 import BASE, ROOT, sha


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    a=p.parse_args()
    d=a.out.resolve()
    assert d.as_posix().isascii() and not d.exists()
    d.mkdir(parents=True)
    source=ROOT/'src/nes/firmware/nes_nrom406.c'
    header=ROOT/'src/nes/firmware/nes_nrom406.h'
    test=ROOT/'tests/nes-nrom406/layout_test.c'
    args=['C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',
          '-std=c99','-O2','-Wall','-Wextra','-Werror','-I',str(header.parent),str(source),str(test),'-o',str(d/'layout.exe')]
    with (d/'compile.log').open('wb') as f:
        c=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    assert c.returncode==0, (d/'compile.log').read_text(errors='replace')
    with (d/'test.log').open('wb') as f:
        t=subprocess.run([str(d/'layout.exe')],stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    assert t.returncode==0 and 'NROM406 HEADER/LAYOUT PASS' in (d/'test.log').read_text()
    target=BASE/'probes/nes-repeat227/arm01/src'
    verify=target/'nes_rom_verify.c'
    spi=target/'nes_rom_spi.c'
    verify_test=ROOT/'tests/nes-nrom406/verify_test.c'
    args=['C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',
          '-std=c99','-O2','-Wall','-Wextra','-Werror','-I',str(target),'-I',str(header.parent),
          str(verify),str(spi),str(source),str(verify_test),'-o',str(d/'verify.exe')]
    with (d/'verify_compile.log').open('wb') as f:
        c=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    assert c.returncode==0, (d/'verify_compile.log').read_text(errors='replace')
    with (d/'verify_test.log').open('wb') as f:
        t=subprocess.run([str(d/'verify.exe')],stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    assert t.returncode==0 and 'NROM406 VERIFY PASS' in (d/'verify_test.log').read_text()
    report={'passed':True,'scope':'header/layout plus actual 227 C readback with synthetic peer; not production file IO, CRC, full loader, STOP recovery or hardware',
            'source':sha(source),'header':sha(header),'test':sha(test),'executable':sha(d/'layout.exe'),
            'production_verify':sha(verify),'production_spi':sha(spi),
            'verify_test':sha(verify_test),'verify_executable':sha(d/'verify.exe')}
    (d/'result.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
