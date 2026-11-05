"""Compare the two complete exporter entities at the same Quartus Lite MAP boundary."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from check_nes_wire600 import sha
from prepare_nes_rows604 import sources


def mapped(a,name,candidate):
    d=a.out/name
    d.mkdir(parents=True)
    sources(a.board,a.probe,d,candidate)
    top='nes_native_export203'
    (d/'export.qpf').write_text('PROJECT_REVISION = "export"\n')
    (d/'export.qsf').write_text(f'''set_global_assignment -name FAMILY "Cyclone IV E"
set_global_assignment -name DEVICE EP4CE15F17C8
set_global_assignment -name TOP_LEVEL_ENTITY {top}
set_global_assignment -name SYSTEMVERILOG_FILE {top}.sv
''')
    with (d/'map.log').open('wb') as log:
        subprocess.run([a.quartus,'export'],cwd=d,stdout=log,stderr=subprocess.STDOUT,check=True)
    summary=(d/'export.map.summary').read_text()
    assert 'Successful' in summary and 'Lite Edition' in summary
    result={k:int(re.search(r'^\s*'+label+r'\s*:\s*([\d,]+)',summary,re.M)[1].replace(',',''))
            for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),
                            ('FF','Dedicated logic registers'),('bits','Total memory bits')]}
    return dict(result,RTL=sha(d/(top+'.sv')),report=sha(d/'export.map.rpt'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('board','probe','quartus','out','report'):
        p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args()
    results={k:mapped(a,k,k=='rows') for k in ('shared','rows')}
    a.report.write_bytes((json.dumps(results,indent=2)+'\n').encode())
