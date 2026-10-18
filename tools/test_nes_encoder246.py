# SPDX-License-Identifier: MIT
"""Full shared encoder against immutable240 synthetic frame wire fixtures."""
from pathlib import Path
import argparse,json,os,shutil
from nes_delta231 import ROOT,BASE,sha
from nes_operand246 import assemble,header
from test_nes_operand243 import run
from nes_stream234 import encode

PUBLIC=['src/nes/rtl/nes_operand246.sv','src/nes/rtl/nes_operand246_entries.vh',
        'src/nes/rtl/nes_source_encoder246.sv','src/nes/rtl/nes_source246.sv',
        'tests/nes-functional/source_encoder246_tb.sv','tools/nes_operand246.py',
        'tools/test_nes_encoder246.py','tools/run_nes_encoder246.ps1']

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert str(d).isascii() and not d.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
    for f in PUBLIC:shutil.copyfile(ROOT/f,d/Path(f).name)
    pins={f:sha(ROOT/f) for f in PUBLIC}
    assert (ROOT/PUBLIC[1]).read_text()==header()
    words,entries=assemble();(d/'operand246.mem').write_text('\n'.join(f'{v:018b}' for v in words+[0]*(512-len(words)))+'\n')
    # No re-generation by the new assembler/controller. These are the same
    # twenty-four complete geometry/raw/CRC record streams as baseline240.
    fixtures={}
    for f in (BASE/'probes/nes-source240/guards01').glob('case*'):
        shutil.copyfile(f,d/f.name);fixtures[f.name]=sha(f)
    assert len(list(d.glob('case*.geometry')))==24
    # One focused full-frame case: two matching one-byte raster changes must
    # produce two cheap records. Independently stall the first record's LAST
    # byte while record_ready remains available; a next header must not leak.
    old=bytes.fromhex((d/'case23.geometry').read_text());new=bytearray(old)
    for row in range(2):new[3872+row*8]^=1
    rr,_=encode(old,bytes(new),b'',257,23)
    (d/'case24.serial').write_text('00000101\n');(d/'case24.geometry').write_text(new.hex(' ')+'\n')
    (d/'case24.raw').write_text(bytes(1792).hex(' ')+'\n')
    (d/'case24.expected').write_text(str(len(rr))+'\n'+'\n'.join(str(len(b))+' '+b.hex(' ') for b in rr)+'\n')
    run(d,a.questa_bin,'vlib',['work'])
    run(d,a.questa_bin,'vlog',['-sv','nes_operand246.sv','nes_source_encoder246.sv','source_encoder246_tb.sv'])
    t=run(d,a.questa_bin,'vsim',['-c','work.source_encoder246_tb','-do','onerror {quit -code 1}; run -all; quit -f'])
    assert 'PASS ENCODER246 checks=42 normal=25' in t and 'LASTBYTE246 stall256=1' in t
    assert pins=={f:sha(ROOT/f) for f in PUBLIC},'Source changed during test'
    result=dict(passed=True,scope=__doc__,program_words=len(words),entries=entries,
        summaries=[s for s in t.splitlines() if 'ENCODER246 ' in s or 'VIEWS246 ' in s or 'LASTBYTE246 ' in s],
        pins=pins,fixture_pins=fixtures,program_sha256=sha(d/'operand246.mem'),
        full_encoder=True,actual_collector=False,actual_spi=False,physical=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('\n'.join(result['summaries']))
if __name__=='__main__':main()
