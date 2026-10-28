# SPDX-License-Identifier: MIT
"""Canonical storage credit, cache requester ownership and hint yielding."""
import json,shutil
from nes_delta231 import ROOT,sha,once
from nes_capture368 import COMMON as PREVIOUS
NAMES=('nes_transport257.sv','nes_joint257.sv','nes_chr_cache192.sv','nes_source_tile192.sv','nes_plan_path267.sv')
COMMON=tuple(dict.fromkeys(PREVIOUS+NAMES))
def materialize(d):
 folder=ROOT/'src/fpga/nes_ingress371';m=json.loads((folder/'manifest.json').read_text())
 for n,h in m['source_files'].items():assert sha(folder/n)==h;shutil.copyfile(folder/n,d/n)
def arm(d):
 old=(ROOT/'tools/nes_source368.c').read_text();old=old[old.index('unsigned source_receive367(void)'):]
 p=d/'nes_decode280.c';s=once(p.read_text(),old,(ROOT/'tools/nes_receive371.c').read_text())
 s=once(s,'int feed280(uint8_t *base,','int source_progress371(void);\nint feed280(uint8_t *base,')
 s=once(s,'p+=take;n-=take;continue;','p+=take;n-=take;if(!source_progress371())return reject();continue;')
 s=once(s,'  p+=take;n-=take;\n','  p+=take;n-=take;if(!source_progress371())return reject();\n')
 # One validated compact row can expose several distinct required tags.
 # Keep the fixed7-lane EA/cache ABI, but do not discard all but its first
 # missing column. Prior-bank fallback remains bounded and advisory.
 s=once(s,'for(unsigned g=0;g<32&&n<5;g++)','for(unsigned g=0;g<32&&n<7;g++)')
 s=once(s,'for(unsigned i=0;i<33&&n<5;i++)','for(unsigned i=0;i<33&&n<7;i++)')
 s=once(s,'n=add_tag367(tags,n,tag,5);break; /* One causal frontier tag per changed group. */','n=add_tag367(tags,n,tag,7); /* All verified columns,never future records. */')
 s=once(s,'if(n&&n<3)for(unsigned i=r->bg_slots;i&&n<3;)', 'if(n&&n<7)for(unsigned i=r->bg_slots;i&&n<7;)')
 s=once(s,'n=add_tag367(tags,n,tag,3);','n=add_tag367(tags,n,tag,7);')
 p.write_text(s,newline='\n')
