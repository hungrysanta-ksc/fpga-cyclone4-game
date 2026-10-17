# SPDX-License-Identifier: MIT
"""Same board gates for selected224 source02; source01 failure stays preserved."""
import re
import nes_counter224_evidence as prior
from nes_counter224 import ROOT,sha,replace
s=prior.s
for x,y in [('source01','source02'),('mapfit01','mapfit02'),('timing01','timing02'),('io01','io02'),('paths01','paths02'),('test02','test04')]:
 s=re.sub(r"\bd/'"+x+r"(?=/|')", "d/'"+y, s)
 # Whole-source audit list and the QSF version exception use folder strings.
 s=s.replace("'"+x+"'","'"+y+"'")
s=replace(s,"'tools/nes_counter224.py','tools/test_nes_counter224.py','tools/nes_counter224_evidence.py',", "'tools/nes_counter224_sample.py','tools/test_nes_counter224_sample.py','tools/nes_counter224_sample_evidence.py','tools/nes_counter224.py','tools/test_nes_counter224.py','tools/nes_counter224_evidence.py',")
s=s.replace("d/'analysis.json'","d/'analysis02.json'").replace('analysis/counter224-verification.json','analysis/counter224-sample-verification.json')
ns=dict(prior.ns);ns['__file__']=__file__;exec(compile(s,'counter224-sample-evidence','exec'),ns)
if __name__=='__main__':ns['main']()
