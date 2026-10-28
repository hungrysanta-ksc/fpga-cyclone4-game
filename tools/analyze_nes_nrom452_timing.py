# SPDX-License-Identifier: MIT
"""Run the established 420 timing audit against a selected 452 report directory."""
import argparse,re
from pathlib import Path
from nes_delta231 import ROOT
p=argparse.ArgumentParser();p.add_argument('--reports',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.reports.resolve();assert not a.out.exists()
fit=(d/'board.fit.summary').read_text();sta=(d/'board.sta.summary').read_text()
assert re.search(r'Total logic elements\s*:\s*14,741\s*/',fit)
for kind,expected in [('Setup',-6.568),('Recovery',-11.467)]:
 values=[float(x) for x in re.findall(r'Type\s*:\s*[^\n]*\b'+kind+r'\b[^\n]*\nSlack\s*:\s*(-?[\d.]+)',sta)];assert values and min(values)==expected
s=(ROOT/'tools/analyze_nes_nrom420_timing.py').read_text();changes={"d=BASE/'probes/nes-nrom419/fit01'":'d=Path('+repr(str(d))+')',"'fit_le':14751":"'fit_le':14741","'raw_sta_setup_ns':-6.970":"'raw_sta_setup_ns':-6.568","'raw_sta_recovery_ns':-8.824":"'raw_sta_recovery_ns':-11.467","(ROOT/'analysis/nrom420-timing.json').write_text(text)":'Path('+repr(str(a.out.resolve()))+').write_text(text)'}
for old,new in changes.items():assert s.count(old)==1;s=s.replace(old,new)
exec(compile(s,str(ROOT/'tools/analyze_nes_nrom420_timing.py'),'exec'))
