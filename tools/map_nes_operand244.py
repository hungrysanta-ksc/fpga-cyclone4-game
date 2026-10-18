# SPDX-License-Identifier: MIT
"""Single unbound-kernel MAP: RAM inference/cost, NOT whole-encoder savings."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_delta231 import ROOT,sha
from nes_operand244 import assemble

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--test',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert str(d).isascii() and not d.exists()
    test=json.loads((a.test/'result.json').read_text());assert test['passed'];d.mkdir(parents=True)
    source=ROOT/'src/nes/rtl/nes_operand244.sv';assert sha(source)==test['pins'][str(source.relative_to(ROOT)).replace('\\','/')]
    shutil.copyfile(source,d/source.name);shutil.copyfile(a.test/'kernel/operand244.mem',d/'operand244.mem')
    words,entries=assemble();assert len(words)==test['program_words'] and sha(d/'operand244.mem')==test['program_sha256']
    for f in ('tools/map_nes_operand244.py','tools/nes_operand244.py'):shutil.copyfile(ROOT/f,d/Path(f).name)
    (d/'source.qpf').write_text('PROJECT_REVISION = "source"\n')
    (d/'source.qsf').write_text('\n'.join([
        'set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8',
        'set_global_assignment -name TOP_LEVEL_ENTITY nes_operand244','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',
        'set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name SYSTEMVERILOG_FILE nes_operand244.sv'])+'\n')
    with (d/'map.log').open('wb') as log:
        q=subprocess.run(['C:/altera_standard/25.1std/quartus/bin64/quartus_map.exe','source'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    assert q.returncode==0,(d/'map.log').read_text(errors='replace')[-6000:]
    summary=(d/'output_files/source.map.summary').read_text();report=(d/'output_files/source.map.rpt').read_text()
    ram_rows=[l.strip() for l in report.splitlines() if 'M9K' in l and ('scratch' in l or 'program_rom' in l)]
    inferred=any('scratch' in l for l in ram_rows) and any('program_rom' in l for l in ram_rows)
    result=dict(passed=inferred,map_completed=True,scratch_and_rom_inferred=inferred,scope=__doc__,fit=False,sta=False,full_encoder=False,program_words=len(words),
        test_sha256=sha(a.test/'result.json'),pins={str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in (source,Path(__file__),ROOT/'tools/nes_operand244.py')},
        program_sha256=sha(d/'operand244.mem'),summary=summary,
        ram_rows=[l.strip() for l in report.splitlines() if 'M9K' in l or ('memory' in l and ';' in l)],
        warnings=[l.strip() for l in (d/'map.log').read_text().splitlines() if 'Warning' in l])
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(summary)
    assert inferred,'Scratch/ROM inference gate failed; preserve report, no board approval.'
if __name__=='__main__':main()
