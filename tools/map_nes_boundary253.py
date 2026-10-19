# SPDX-License-Identifier: MIT
"""MAP the unchanged functional240 source boundary including query and SPI.

Comparison against253 includes the new receipt/H2 functionality on253 only.
Neither MAP can establish a placed whole-board logic or timing margin.
"""
from pathlib import Path
import argparse,json,re,shutil,subprocess
from nes_delta231 import BASE,sha

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
    prior=BASE/'probes/nes-source240/board01';pins={}
    names=['nes_source240','nes_source_encoder240','nes_source_query235','nes_source_spi235','nes_native_mailbox206']
    for n in names:
        f=prior/(n+'.sv');pins[f.relative_to(BASE).as_posix()]=sha(f);shutil.copyfile(f,d/f.name)
    shutil.copyfile(__file__,d/'runner.py')
    (d/'reference.qpf').write_text('PROJECT_REVISION = "reference"\n')
    (d/'reference.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_source240','set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',*[f'set_global_assignment -name SYSTEMVERILOG_FILE {n}.sv' for n in names]])+'\n')
    with (d/'map.log').open('wb') as log:
        q=subprocess.run(['C:/altera_standard/25.1std/quartus/bin64/quartus_map.exe','reference'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    assert q.returncode==0,(d/'map.log').read_text()[-5000:]
    summary=(d/'output_files/reference.map.summary').read_text();report=(d/'output_files/reference.map.rpt').read_text()
    result=dict(passed=True,scope=__doc__,summary=summary,input_hashes=pins,fit=False,sta=False,
                ram_rows=[l.strip() for l in report.splitlines() if 'M9K' in l and ('base_' in l or 'scratch' in l or 'memory' in l)])
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(summary)

if __name__=='__main__':main()
