# SPDX-License-Identifier: MIT
"""Compare measurement-only reset paths and ignored loader budget."""
import collections,csv,json
from nes_delta231 import BASE,ROOT,sha
d=BASE/'probes/nes-nrom419/fit01';old=BASE/'probes/nes-counter224/io02/boundary165-paths.tsv'
def rows(p):
 with p.open() as f:return list(csv.DictReader(f,delimiter='\t'))
def negative(p):
 return {(r['corner'],r['group'],r['from'],r['to']) for r in rows(p) if r['group'] in ('recovery','removal') and float(r['slack'])<0}
a=negative(d/'boundary165-paths.tsv');b=negative(old);assert len(a)==len(b)==39 and a==b
r=rows(d/'nrom421-loader-paths.tsv');corners={}
for c in sorted({v['corner'] for v in r}):
 q=[v for v in r if v['corner']==c];assert len(q)==171
 corners[c]={'count':len(q),'max_delay':max(float(v['delay']) for v in q),'min_slack':min(float(v['slack']) for v in q)}
assert len(corners)==3
report=(d/'implementation-unconstrained204.rpt').read_text(errors='replace')
assert 'Unconstrained Input Ports       ; 54' in report and 'Unconstrained Output Ports      ; 56' in report
out={'reset_negative_paths':len(a),'same_path_keys_as_224':True,'path_comparison_does_not_prove_full_reset_safety':True,
 'loader_phase_to_count':corners,'ignored_max_delay_budget_ns':5.3,'maximum_delay_ns':max(v['max_delay'] for v in corners.values()),
 'worst_normal_setup_slack_ns':min(v['min_slack'] for v in corners.values()),'unconstrained_inputs':54,'unconstrained_outputs':56,
 'electrical_signoff':False,'constraint_modified':False,'inputs':{p.relative_to(BASE).as_posix():sha(p) for p in [old,d/'boundary165-paths.tsv',d/'nrom421-loader-paths.tsv',d/'implementation-unconstrained204.rpt']}}
(ROOT/'analysis/nrom421-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
