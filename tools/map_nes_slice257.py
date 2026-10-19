# SPDX-License-Identifier: MIT
"""One MAP of the tested range boundary, including retained queue and aperture.

This inclusive envelope is not new incremental cost, whole-board fit, or STA.
The source core, capture lease, tile arbitration and ordinary packet path are
outside this synthesis top. Do not subtract this from unrelated parent rows.
"""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_delta231 import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--test',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--quartus-bin',type=Path,default=Path('C:/altera_lite/25.1std/quartus/bin64'))
    a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists()
    test=json.loads((a.test/'result.json').read_text());assert test['passed']
    names=['nes_range257.sv','nes_queue257.sv','nes_bulk_aperture188.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv']
    d.mkdir(parents=True);pins={}
    for name in names:
        f=a.test/name;pins[name]=sha(f);assert pins[name]==test['rtl_hashes'][name]
        shutil.copyfile(f,d/name)
    shutil.copyfile(__file__,d/'runner.py')
    (d/'range.qpf').write_text('PROJECT_REVISION = "range"\n',newline='\n')
    (d/'range.qsf').write_text('\n'.join([
        'set_global_assignment -name FAMILY "Cyclone IV E"',
        'set_global_assignment -name DEVICE EP4CE15F17C8',
        'set_global_assignment -name TOP_LEVEL_ENTITY nes_range257',
        'set_global_assignment -name NUM_PARALLEL_PROCESSORS 2',
        'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',
        *[f'set_global_assignment -name SYSTEMVERILOG_FILE {n}' for n in names]])+'\n',newline='\n')
    with (d/'map.log').open('wb') as f:
        q=subprocess.run([str(a.quartus_bin/'quartus_map.exe'),'range'],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
    assert q.returncode==0,(d/'map.log').read_text(errors='replace')[-5000:]
    summary=(d/'output_files/range.map.summary').read_text()
    report=(d/'output_files/range.map.rpt').read_text()
    r=dict(passed=True,scope=__doc__,summary=summary,rtl_hashes=pins,test_result_sha256=sha(a.test/'result.json'),quartus_bin=str(a.quartus_bin),
        memory_rows=[x.strip() for x in report.splitlines() if 'M9K' in x],fit=False,sta=False,incremental_cost=False)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(summary)


if __name__=='__main__':main()
