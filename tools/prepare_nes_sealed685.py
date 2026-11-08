"""Reuse684 receive ownership after SEAL, without a redundant E0 on progress."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha

def prepare(base,out):
    expected='1950553af72260ad1dc554baf9aec7bc952803eeb76684502528ef1ebb3eacbf'
    assert sha(base/'src/obj-nes-100/firmware.stm')==expected
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_native_runtime165.c'
    s=once(p.read_text(),'(input_wait || (reason==2 && !progress))','(input_wait || reason==2)')
    s=once(s,'/* Only sealed output may defer its next E0 until this bounded input',
        '/* SEAL has no later output to issue: preceding retirement does not\n    * need another E0 before borrowing SPI. Full identity is still checked\n    * by the barrier before it returns. Only sealed output may defer its next E0 until this bounded input')
    p.write_text(s,newline='\n')
    (out/'recipe685.json').write_text(json.dumps(dict(base=expected,source=sha(p),
        change='SEAL wait borrows SPI even on retirement progress. Unsealed credit priority, seven checked blocks and full final identity retained.'),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
