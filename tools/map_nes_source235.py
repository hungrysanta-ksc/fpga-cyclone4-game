# SPDX-License-Identifier: MIT
"""One MAP per235 endpoint; NOT additive whole-board resource/timing approval."""
from pathlib import Path
import argparse,json,subprocess,shutil,re
from nes_delta231 import ROOT,BASE,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
    result=dict(scope=__doc__,fit=False,sta=False,encoder_included=False,projects={})
    for name in ('spi','query'):
        d=out/name;d.mkdir();top='nes_source_'+name+'235'
        files=[ROOT/'src/nes/rtl'/(top+'.sv')]
        if name=='spi':files.append(BASE/'probes/nes-counter224/mapfit02/nes_native_mailbox206.sv')
        qsf=['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8',
             'set_global_assignment -name TOP_LEVEL_ENTITY '+top,'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',
             'set_global_assignment -name NUM_PARALLEL_PROCESSORS 2']
        for f in files:shutil.copyfile(f,d/f.name);qsf.append('set_global_assignment -name SYSTEMVERILOG_FILE '+f.name)
        (d/'source.qpf').write_text('PROJECT_REVISION = "source"\n');(d/'source.qsf').write_text('\n'.join(qsf)+'\n')
        with (d/'map.log').open('wb') as log:
            q=subprocess.run(['C:/altera_standard/25.1std/quartus/bin64/quartus_map.exe','source'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
        assert q.returncode==0,(d/'map.log').read_text(errors='replace')[-6000:]
        summary=(d/'output_files/source.map.summary').read_text()
        report=(d/'output_files/source.map.rpt').read_text()
        result['projects'][name]=dict(summary=summary,pins={str(f.relative_to(BASE)):sha(f) for f in files},
            ram_rows=[l.strip() for l in report.splitlines() if 'M9K' in l or ('memory' in l and ';' in l)],
            warnings=[l.strip() for l in (d/'map.log').read_text().splitlines() if 'Warning' in l])
        print(name+'\n'+summary)
    result['passed']=True;(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
