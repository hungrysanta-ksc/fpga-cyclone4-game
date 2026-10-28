# SPDX-License-Identifier: MIT
"""Audit the sampled negative reset paths; does not change STA constraints."""
import csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT
p=BASE/'probes/nes-nrom419/fit01';q=BASE/'probes/nes-repeat227/asm02'
rows=list(csv.DictReader((p/'boundary165-paths.tsv').open(),delimiter='\t'))
neg=[x for x in rows if x['group'] in ('recovery','removal') and float(x['slack'])<0]
assert len(neg)==39 and len({x['corner'] for x in neg})==3
assert all(x['from'].endswith('core_release|release_reset[1]') for x in neg)
ends={x['to'] for x in neg};assert len(ends)==13
classes={
 'mailbox_local_release':sorted(x for x in ends if 'native_prepared|sr[' in x or 'native_records|dr[' in x),
 'sink_local_release':sorted(x for x in ends if 'sink|nes_domain_reset124:release_local|release_reset[' in x),
 'sink_idle_admission':sorted(x for x in ends if re.search(r'sink\|(host_ready|idle_ss\[|idle_write\[)',x)),
 'sink_fault_sync':sorted(x for x in ends if x.startswith('sink_rom_fault[')),
}
assert sorted(map(len,classes.values()))==[2,2,4,5] and set().union(*(set(v) for v in classes.values()))==ends
s=(q/'nes_sink_bridge165.sv').read_text();m=(q/'nes_native_mailbox165.sv').read_text();t=(q/'fxpak_nes_screen137_top.sv').read_text()
assert 'if(raw_cancel)begin idle_ss<=0;idle_write<=0;host_ready<=0;end' in s and 'if(!reset&&idle_ss[1]&&idle_write[1])host_ready<=1' in s
assert 'if(core_reset)sink_rom_fault<=0' in t and 'wire src_reset=!sr[1],dst_reset=!dr[1]' in m
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
r={'sampled_negative_rows':len(neg),'unique_endpoints':len(ends),'corners':sorted({x['corner'] for x in neg}),'worst_sampled_recovery_ns':min(float(x['slack']) for x in neg),'endpoint_classes':classes,'input_sha256':{str(x.name):h(x) for x in [p/'boundary165-paths.tsv',q/'nes_sink_bridge165.sv',q/'nes_native_mailbox165.sv',q/'fxpak_nes_screen137_top.sv']},'scope':'sampled path report only; local release structure reviewed, physical reset recovery/metastability and full reset/CDC/IO closure not proven'}
(ROOT/'analysis/nrom450-reset.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ('sampled_negative_rows','unique_endpoints','worst_sampled_recovery_ns')}))
