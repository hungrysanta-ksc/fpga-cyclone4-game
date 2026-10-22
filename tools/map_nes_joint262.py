# SPDX-License-Identifier: MIT
"""One tested integrated replacement boundary, Quartus Lite MAP only."""
import argparse,json,shutil
from pathlib import Path
from nes_joint262 import sources
from nes_delta231 import BASE,ROOT,sha
from probe_nes_joint262 import run


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--test',type=Path,required=True);p.add_argument('--separate-prelude',action='store_true');a=p.parse_args();d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
 test=json.loads((a.test/'result.json').read_text());assert test['passed'];src=sources(not a.separate_prelude)
 for n,s in src.items():(d/n).write_text(s,encoding='utf-8',newline='\n')
 for n in ['nes_native_mailbox206.sv','nes_domain_reset124.sv','nes_capture_lease201.sv','nes_bulk_aperture188.sv']:
  shutil.copyfile(a.test/n,d/n);src[n]=''
 hashes={n:sha(d/n) for n in src};assert all(test['rtl_hashes'][n]==h for n,h in hashes.items())
 (d/'joint.qpf').write_text('PROJECT_REVISION = "joint"\n',encoding='utf-8')
 (d/'joint.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_joint262','set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',*[f'set_global_assignment -name SYSTEMVERILOG_FILE {n}' for n in src]])+'\n',encoding='utf-8')
 run('C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe',['joint'],d,'map',600)
 summary=(d/'output_files/joint.map.summary').read_text();r=dict(passed=True,summary=summary,rtl_hashes=hashes,test_sha256=sha(a.test/'result.json'),whole_board=False,FIT=False,STA=False,Quartus='Lite25.1std')
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(summary)

if __name__=='__main__':main()
