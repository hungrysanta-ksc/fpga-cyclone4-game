"""Update the FF3 program ROM in a copy of the proven 1048 routed project."""
import argparse
import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from package_nes_kirby1027 import timing

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def assemble(base, work, reference, quartus):
    assert sha(base/'output_files/board.sof')==sha(reference/'board.sof')
    out=work/'route'
    out.mkdir(exist_ok=True)
    rom=bytes.fromhex((work/'client/sink-program.hex').read_text())
    original=bytes.fromhex((base/'sink-program.hex').read_text())
    assert len(rom)==len(original)==7168 and rom[0x1bff]==255
    with tempfile.TemporaryDirectory(prefix='ff3-client-') as tmp:
        board=Path(tmp)/'board'
        shutil.copytree(base,board)
        mif,=(board/'db').glob('board.ram*_nes_sink_bus165_*.hdl.mif')
        pattern=re.compile(r'^(\s*)(\d+)(\s*:\s*)([01]{8})(;)',re.M)
        def contents(text):
            rows=sorted((int(m[2]),int(m[4],2)) for m in pattern.finditer(text))
            assert [i for i,_ in rows]==list(range(len(rom)))
            return bytes(v for _,v in rows)
        source=mif.read_text()
        assert contents(source)==original
        updated=pattern.sub(lambda m:f'{m[1]}{m[2]}{m[3]}{rom[int(m[2])]:08b};',source)
        assert contents(updated)==rom
        mif.write_text(updated)
        shutil.copyfile(work/'client/sink-program.hex',board/'sink-program.hex')
        for name,args in [('quartus_cdb',['board','--update_mif']),('quartus_asm',['board']),
                          ('quartus_cpf',['-c','output_files/board.sof','board.rbf'])]:
            with (out/(name+'.log')).open('wb') as log:
                subprocess.run([quartus/(name+'.exe'),*args],cwd=board,stdout=log,stderr=subprocess.STDOUT,check=True)
        assert mif.name in (out/'quartus_cdb.log').read_text(errors='replace')
        for name in ('board.fit.rpt','board.fit.summary','board.sta.rpt','board.sta.summary','board.pin'):
            assert sha(base/'output_files'/name)==sha(board/'output_files'/name)
        assert sha(board/'output_files/board.sof')!=sha(reference/'board.sof')
        assert sha(board/'board.rbf')!=sha(reference/'board.rbf')
        shutil.copy2(board/'board.rbf',out)
        shutil.copy2(board/'output_files/board.sof',out)
    print(timing(reference))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('base','work','reference','quartus'):p.add_argument(key,type=Path)
    assemble(**vars(p.parse_args()))
