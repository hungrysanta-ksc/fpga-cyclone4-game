"""Read-only P0 provenance audit. SPDX-License-Identifier: MIT.
Never opens a commercial ROM or the original GBC checkout.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--upstream',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--plan-evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
commit=subprocess.check_output(['git','-C',str(a.upstream),'rev-parse','HEAD'],text=True).strip();assert commit=='49a0a662e244469ca77b2155746a066df704ffae'
manifest=json.loads(a.evidence.read_text(encoding='utf-8-sig'));checks=[]
for f in manifest['files']:
 path=a.evidence.parent/f['copy'];actual=sha(path)
 checks.append(dict(file=f['copy'],sha256=actual,match=actual==f['sha256'].lower()))
 assert checks[-1]['match'],f['copy']
plan=json.loads(a.plan_evidence.read_text(encoding='utf-8-sig'));snapshots=[]
for f in plan['reference_files']:
 path=a.plan_evidence.parent.parent/f['snapshot'];actual=sha(path)
 snapshots.append(dict(file=Path(f['snapshot']).name,sha256=actual,match=actual==f['sha256'].lower()))
 assert snapshots[-1]['match'],f['snapshot']
files=['COPYING','rtl/nes.v','rtl/ppu.sv','rtl/apu.sv','rtl/regs_savestates.sv','rtl/bus_savestates.vhd','rtl/dpram.vhd','rtl/mappers/MMC3.sv','sys/iir_filter.v']+[f'rtl/t65/{n}.vhd' for n in ['T65_Pack','T65_ALU','T65_MCode','T65']]
entries=[]
for f in files:
 path=a.upstream/f;data=path.read_text(encoding='utf-8',errors='replace');header='\n'.join(data.splitlines()[:100])
 if '/t65/' in f:
  license='LicenseRef-T65-source-synthesized-BSD-style';basis='file header; source and synthesized-form notice, non-endorsement, disclaimer';status='candidate-locked'
 elif f=='sys/iir_filter.v':license='GPL-2.0-or-later';basis='explicit file header';status='candidate-locked'
 elif f=='rtl/apu.sv':license='GPL-3.0';basis='explicit GPLv3 file header; no later-version grant asserted';status='candidate-locked'
 elif 'See COPYING' in header or f=='COPYING':license='GPL-3.0';basis='file points to repository COPYING (GPLv3 text)';status='candidate-locked'
 else:license='repository GPLv3; individual grant not stated';basis='no per-file notice; repository COPYING is evidence, not blanket clearance';status='hold-before-vendoring'
 notice=[]
 for line in data.splitlines():
  if not line.strip():continue
  if line.lstrip().startswith(('//','--')):notice.append(line)
  else:break
 entries.append(dict(path=f,sha256=sha(path),bytes=path.stat().st_size,license=license,basis=basis,status=status,notice_lines=notice))
result=dict(candidate='NES-P0-001',upstream=dict(url='https://github.com/MiSTer-devel/NES_MiSTer',commit=commit,files=entries),
 current_adoption='P1 original MIT Python/Lua only; no upstream HDL copied into this checkout by P1',
 exclusions=['MiSTer OPLL/VM2413 noncommercial condition','N8 permission unconfirmed'],
 evidence_manifest_sha256=sha(a.evidence),evidence_files=checks,plan_manifest_sha256=sha(a.plan_evidence),plan_snapshots=snapshots,
 gbc_baseline='C44 / sd2snesHST 0.9.0 / development 8240299b1b6c061f14d88e591ccd4c9b64d113da',
 limitations=['HDL per-file holds unresolved; no P2 vendoring or distribution clearance','board pins, external RAM response, full fit/STA unverified'])
a.out.parent.mkdir(parents=True,exist_ok=True)
with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps(dict(evidence_files=len(checks),plan_snapshots=len(snapshots),source_files=len(entries),holds=[e['path'] for e in entries if e['status'].startswith('hold')]),indent=2))
