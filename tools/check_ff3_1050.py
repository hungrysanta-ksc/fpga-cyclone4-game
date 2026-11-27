"""Exercise the installed raw DMA routine and pad service on the 65816."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from check_ff3_backdrop1046 import captured
from check_ff3_menu_cpu import run_case

def check(client, mesen, work):
    sources=[work.parent/'nes-ff3-1047/test/vsim-checkpoint.log',
             work.parent/'nes-ff3-1046/closed/vsim-checkpoint.log']
    cases=[]
    for source in sources:
        frames=[bytes(row[-1]) for _,row in captured(source) if len(row[-1]) in (256,512)]
        assert frames,source
        cases.extend(frames)
    compare={}
    for name,root in [('before',work.parent/'nes-ff3-1048/menu-io'),('after',client)]:
        rom=bytearray((root/'sink165.sfc').read_bytes())
        labels=json.loads((root/'labels.json').read_text())
        # The original loader verifies and expands the exact installed program
        # into WRAM. Divert only its final jump into this test driver.
        entry=bytes.fromhex('5c 00 20 7e')
        assert rom.count(entry)==1
        rom[rom.index(entry):rom.index(entry)+4]=bytes.fromhex('5c 00 a0 00')
        rom[0x2000:0x2004]=bytes.fromhex('5c 00 1a 7e')
        with tempfile.TemporaryDirectory(prefix='ff3-dma-') as tmp:
            d=Path(tmp)
            (d/'test.sfc').write_bytes(rom)
            (d/'cases').write_bytes(b''.join(bytes([len(p)//256])+p for p in cases))
            lua=(Path(__file__).resolve().parents[1]/'tests/nes-functional/ff3_raw1050.lua').read_text()
            for k,v in {'ROOT':json.dumps(d.as_posix()),'RAW':str(labels['raw_dma489']&65535),
                        'FILL':str(rom[0x17be] if name=='before' else 255)}.items():
                lua=lua.replace('@'+k+'@',v)
            (d/'test.lua').write_text(lua)
            proc=subprocess.run([str(mesen),'--testRunner',str(d/'test.lua'),str(d/'test.sfc'),'--timeout=45',
                    '--doNotSaveSettings','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,
                    capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60,
                    env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'))
            result=(d/'result').read_text() if (d/'result').exists() else 'no completion record'
            assert proc.returncode==0 and result.startswith('PASS'),(name,result,proc.returncode)
            compare[name]=list(map(int,result.split()[1:]))
    assert compare['before'][0]==compare['after'][0] and compare['after'][1]==0
    assert compare['before'][1]*8==compare['before'][0]*7
    for mode in ('turbo','resume','load','exit'):
        run_case(client,mesen,mode)
    report={'frames':len(cases),'banks':2,'pixels_and_wrong_indices':compare,
            'pad_test_fields':148,'menu_cases':['resume','load','exit']}
    (work/'client-tests.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('client','mesen','work'):p.add_argument(key,type=Path)
    check(**vars(p.parse_args()))
