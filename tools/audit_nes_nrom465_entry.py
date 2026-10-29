# SPDX-License-Identifier: MIT
"""Read-only entry audit. Never installs files or waives timing failures."""
import argparse,collections,csv,hashlib,json,re,zipfile
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--sd-root',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
d=BASE/'probes/nes-nrom457/fit01';text=(d/'implementation-unconstrained204.rpt').read_text()
ports={'input':set(),'output':set()};kind=None
for line in text.splitlines():
 if re.search(r'; Unconstrained Input Ports\s*;',line):kind='input'
 elif re.search(r'; Unconstrained Output Ports\s*;',line):kind='output'
 elif '; Unconstrained Input Port Paths' in line or '; Unconstrained Output Port Paths' in line:kind=None
 m=re.match(r';\s*([A-Z][A-Z_0-9]*(?:\[\d+\])?)\s*;\s*(?:No |Partially constrained)',line)
 if m and kind:ports[kind].add(m[1])
assert len(ports['input'])==54 and len(ports['output'])==56,{k:len(v) for k,v in ports.items()}
groups={k:dict(collections.Counter(re.sub(r'\[\d+\]$','',n) for n in v)) for k,v in ports.items()}
rows=list(csv.DictReader((d/'inventory206.tsv').open(),delimiter='\t'))
neg=[x for x in rows if x['kind']=='recovery' and float(x['slack'])<0 and ((x['from_clock']=='nes')!=(x['to_clock']=='nes'))]
endpoints=sorted({x['to'] for x in neg});assert len(neg)==525 and len(endpoints)==45
release=[];admission=[];fault=[];other=[]
for n in endpoints:
 if re.search(r'\|(release_reset|memory_reset|source_reset|sr|dr|dac_release)\[',n):release.append(n)
 elif n.startswith('nes_sink_bridge165:sink|') and re.search(r'\|(host_ready|idle_ss\[|idle_write\[)',n):admission.append(n)
 elif n.startswith('sink_rom_fault['):fault.append(n)
 else:other.append(n)
assert not other,other
spec=json.loads((ROOT/'analysis/nrom458-artifacts.json').read_text())
artifacts={'sd2snes/firmware.stm':(BASE/'probes/nes-nrom418/arm01/src/obj-nes-100/firmware.stm',spec['firmware_stm_sha256']),'sd2snes/fpga_nrom16.bi3':(BASE/'probes/nes-nrom458/asm01/fpga_nrom16.bi3',spec['bi3_sha256']),'sd2snes/nes/nrom16.nes':(BASE/'probes/nes-nrom428/fixture01/nrom16.nes',spec['rom_sha256'])}
local={}
for name,(path,h) in artifacts.items():assert sha(path)==h;local[name]={'sha256':h,'bytes':path.stat().st_size}
release_spec=json.loads((ROOT/'analysis/release227-verification.json').read_text())
with zipfile.ZipFile(BASE/'probes/nes-repeat227/release01/NES227-SMB3-OAMREPEAT.zip') as z:
 for name in ('sd2snes/fpga_base.bi3','sd2snes/m3nu.bin'):
  payload=z.read('01-GAME227-SD-ROOT/'+name);h=hashlib.sha256(payload).hexdigest();assert h==release_spec['preserved']['01-GAME227-SD-ROOT/'+name];local[name]={'sha256':h,'bytes':len(payload)}
local['NES GAME 227.nh1']={'sha256':hashlib.sha256(b'').hexdigest(),'bytes':0}
sd={}
if a.sd_root:
 assert a.sd_root.is_dir(),'SD root must exist'
 for name,v in local.items():
  f=a.sd_root/name;sd[name]={'exists':f.is_file(),'matches':f.is_file() and sha(f)==v['sha256']}
sdc=(d/'board.sdc').read_text();assert 'set_clock_groups' not in sdc
r={'audit_passed':True,'trial_approved':False,'physical_configuration_tested':False,'sd_root':str(a.sd_root.resolve()) if a.sd_root else None,'sd_files':sd,'expected_files':local,'timing':{'unconstrained_ports':{k:sorted(v) for k,v in ports.items()},'port_groups':groups,'negative_cross_recovery_sample_rows':len(neg),'distinct_sampled_endpoints':len(endpoints),'reset_release_endpoints':release,'admission_endpoints':admission,'fault_sync_endpoints':fault,'raw_setup_ns':-7.040,'raw_recovery_ns':-9.659,'related_setup_ns':0.226,'related_hold_ns':0.151,'complete_cdc_inventory':False,'io_electrical_bounds_measured':False},'inputs':{'unconstrained_report':sha(d/'implementation-unconstrained204.rpt'),'sample_inventory':sha(d/'inventory206.tsv')},'scope':'existing routed reports and artifact identity; no new timing, configuration, SD write, physical recovery or 60fps; exact port lists, sampled recovery endpoints only'}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'audit_passed':True,'groups':groups,'reset_classes':{'release':len(release),'admission':len(admission),'fault':len(fault)},'trial_approved':False}))
