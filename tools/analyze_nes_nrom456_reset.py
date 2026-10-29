# SPDX-License-Identifier: MIT
"""Inventory 455 sampled cross-domain reset endpoints, not a CDC signoff."""
import collections,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=BASE/'probes/nes-nrom455/fit01';rows=list(csv.DictReader((p/'inventory206.tsv').open(),delimiter='\t'))
neg=[x for x in rows if x['kind']=='recovery' and float(x['slack'])<0 and ((x['from_clock']=='nes')!=(x['to_clock']=='nes'))]
endpoints=sorted({x['to'] for x in neg});src=sorted({x['from'] for x in neg});assert len(neg)==576 and len(endpoints)==62
def group(n):
 if ':clock_guard|' in n:return 'clock_guard_state'
 if n.startswith('nes_sink_bridge165:sink|') and re.search(r'\|(host_ready|idle_ss\[|idle_write\[)',n):return 'sink_admission'
 if n.startswith('sink_rom_fault['):return 'sink_fault_synchronizer'
 if re.search(r'\|(release_reset|memory_reset|source_reset|sr|dr|dac_release)\[',n):return 'local_reset_release'
 return 'other'
classes={k:sorted(x for x in endpoints if group(x)==k) for k in sorted({group(x) for x in endpoints})};assert sum(map(len,classes.values()))==62
r={'sampled_negative_recovery_rows':len(neg),'distinct_endpoints':len(endpoints),'distinct_sources':len(src),'classes':classes,'sources_by_sampled_rows':dict(collections.Counter(x['from'] for x in neg)),'unconstrained_ports':{'inputs':54,'outputs':56},'input_sha256':{'inventory':sha(p/'inventory206.tsv'),'unconstrained':sha(p/'implementation-unconstrained204.rpt')},'scope':'top-N reported paths across clock pairs and corners, not a complete endpoint inventory; classification by name only, no CDC/MTBF/IO signoff'};(ROOT/'analysis/nrom456-reset.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:len(v) for k,v in classes.items()}))
