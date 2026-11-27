"""Execute the shipped 65816 menu from reset, with a cartridge mailbox fixture."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from build_ff3_menu_client import CHARS, ROOT

def run_case(client, mesen, mode):
    labels=json.loads((client/'menu-labels.json').read_text())
    source=(ROOT/'tests/nes-functional/ff3_menu_cpu.lua').read_text()
    with tempfile.TemporaryDirectory(prefix='ff3-menu-') as tmp:
        work=Path(tmp)
        result=work/'result.txt'
        values={'MODE':json.dumps(mode),'LABELS':'{'+','.join(f'{k}={labels[k]}' for k in ('input','ordinary'))+'}',
                'TITLE':'{'+','.join(str(CHARS.index(c)) for c in 'NES CORE MENU')+'}',
                'REPORT':json.dumps(result.as_posix()),'FONT':str(16*len(CHARS))}
        for key,value in values.items():source=source.replace('@'+key+'@', value)
        lua=work/'test.lua'
        lua.write_text(source)
        proc=subprocess.run([str(mesen.resolve()),'--testRunner',str(lua),str((client/'sink165.sfc').resolve()),
            '--timeout=15','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=35,creationflags=subprocess.CREATE_NO_WINDOW,
            env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'))
        outcome=result.read_text() if result.exists() else 'no completion record'
        if proc.returncode or not outcome.startswith('PASS'):raise RuntimeError(outcome)
        return proc.stdout + (outcome + '\n').encode()

def check(client, mesen, report):
    with report.open('wb') as stream:
        for mode in ('resume','load','exit'):
            stream.write(run_case(client, mesen, mode))
    print('PASS FF3 65816 menu, slot load request and exit request')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('client','mesen','report'):parser.add_argument(arg,type=Path)
    a=parser.parse_args()
    check(a.client,a.mesen,a.report)
