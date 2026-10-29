# SPDX-License-Identifier: MIT
"""Run 415 prefix at five clock phases using the authorized FLOAT wrapper.

This probes only initial observer selection and 256 DATA writes. It does not
exercise screen during RUN or claim electrical timing/CDC signoff.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from nes_delta231 import ROOT,sha

p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--fixture',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
out=a.out.resolve();assert out.as_posix().isascii() and not out.exists()
assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
out.mkdir(parents=True)
rows=[]
for phase in (0,11,23,35,46):
 d=out/('phase%02d'%phase)
 cmd=[sys.executable,str(ROOT/'tools/test_nes_nrom415_wiring.py'),'--build',str(a.build),'--fixture',str(a.fixture),'--out',str(d),'--run','--phase-ns',str(phase)]
 with (out/('phase%02d.log'%phase)).open('wb') as f:
  r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode!=0:raise RuntimeError((out/('phase%02d.log'%phase)).read_text(errors='replace')[-5000:])
 result=json.loads((d/'result.json').read_text());assert result['passed'] and result['prefix_bytes']==256
 rows.append({'phase_ns':phase,'result_sha256':sha(d/'result.json'),'bench_sha256':sha(d/'prefix_tb.sv')})
result={'passed':True,'phases':rows,'SPI_hz':2625000,'scope':'observer identify and 256 DATA prefix using 415 fixture; screen RUN, STOP/base, actual ARM, physical CDC and timing not tested'}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
