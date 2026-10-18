# SPDX-License-Identifier: MIT
"""Narrow235 response/lease/partialSS/partial-record guards; no normal rerun."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,re
from nes_delta231 import ROOT,BASE,sha
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert str(d).isascii() and not d.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir()
    files=[ROOT/'src/nes/rtl'/('nes_source_'+n+'235.sv') for n in ('spi','query')]+[ROOT/'tests/nes-functional'/n for n in ('source_spi235_tb.sv','source_query235_guards_tb.sv')]+[BASE/'probes/nes-counter224/mapfit02/nes_native_mailbox206.sv']
    for f in files:shutil.copyfile(f,d/f.name)
    def run(exe,args,name):
        with (d/(name+'.log')).open('wb') as log:q=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        t=(d/(name+'.log')).read_text(errors='replace');assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:];return t
    run('vlib',['work'],'vlib');run('vlog',['-sv',*[f.name for f in files]],'vlog')
    spi=run('vsim',['-c','work.source_spi235_tb','-gGUARDS_ONLY=1','-do','onerror {quit -code 1}; run -all; quit -f'],'spi')
    query=run('vsim',['-c','work.source_query235_guards_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'query')
    assert 'PASS SPI235 checks=19' in spi and 'PASS QUERY235 GUARDS checks=21' in query
    r=dict(passed=True,scope=__doc__,spi=spi,query=query,pins={str(f.relative_to(BASE)):sha(f) for f in files})
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS SOURCE235 narrow guards')
if __name__=='__main__':main()
