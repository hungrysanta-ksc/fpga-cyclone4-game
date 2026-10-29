# SPDX-License-Identifier: MIT
"""Compare the reset candidate with the pinned original routed build."""
import csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
before=BASE/'probes/nes-nrom419/fit01';after=BASE/'probes/nes-nrom451/fit01'
def negatives(d):
 return {r['to'] for r in csv.DictReader((d/'boundary165-paths.tsv').open(),delimiter='\t') if r['group'] in ('recovery','removal') and float(r['slack'])<0}
a,b=negatives(before),negatives(after);removed=sorted(a-b);assert len(a)==13 and len(b)==8 and len(removed)==5 and not b-a
assert all(x.startswith('nes_sink_bridge165:sink|') for x in removed)
def fit(d):
 s=(d/'board.fit.summary').read_text();return {k:int(re.search(pattern,s).group(1).replace(',','')) for k,pattern in {'le':r'Total logic elements\s*:\s*([\d,]+)','comb':r'Total combinational functions\s*:\s*([\d,]+)','registers':r'Dedicated logic registers\s*:\s*([\d,]+)','ram_bits':r'Total memory bits\s*:\s*([\d,]+)'}.items()}
def worst(d,kind):
 s=(d/'board.sta.summary').read_text();return min(float(x) for x in re.findall(r'Type\s*:\s*[^\n]*\b'+kind+r"\b[^\n]*\nSlack\s*:\s*(-?[\d.]+)",s))
r={'baseline':fit(before),'candidate':fit(after),'raw_setup_ns':[worst(before,'Setup'),worst(after,'Setup')],'raw_recovery_ns':[worst(before,'Recovery'),worst(after,'Recovery')],'sample_negative_endpoint_before':len(a),'sample_negative_endpoint_after':len(b),'removed_sample_endpoints':removed,'scope':'same board RTL/SDC except sink reset and Quartus last-version metadata; sampled paths only; FIT success is not STA signoff', 'input_sha256':{'before':sha(before/'boundary165-paths.tsv'),'after':sha(after/'boundary165-paths.tsv')}}
(ROOT/'analysis/nrom451-reset.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
