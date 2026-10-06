"""Reject damaged IRQ/A12/handler evidence through the full verifier. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,hashlib,json,shutil
from verify_nes_mmc3_integrated import verify
p=argparse.ArgumentParser()
for n in ('run','reference','rom','out'):p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
for name in ['manifest.json','prg.hex','chr.hex','simulation.log','build.json','frames.tsv','fetch.tsv','control.tsv','edges.tsv',*[f'frame-{n:3}.hex' for n in range(1,5)]]:shutil.copy2(a.run/name,a.out/name)
start=int((a.out/'frames.tsv').read_text().splitlines()[0].split()[3]);results={}
for name,kind in [('missing_irq','IRQ'),('missing_a12','A12'),('bad_handler','W')]:
 file=a.out/('control.tsv' if kind=='W' else 'edges.tsv');original=file.read_text();rows=original.splitlines()
 if kind=='W':
  idx=next(i for i,s in enumerate(rows) if s.split()[0]=='W' and int(s.split()[1])>start and int(s.split()[4])==3)
  v=rows[idx].split();v[5]=str(int(v[5])^1);rows[idx]=' '.join(v)
 else:idx=next(i for i,s in enumerate(rows) if s.split()[0]==kind and int(s.split()[1])>start and s.split()[4]=='1');rows.pop(idx)
 file.write_text('\n'.join(rows)+'\n',encoding='utf-8');r=verify(a.out,a.reference,a.rom);results[name]={'rejected':not r['passed'],'errors':r['errors']};file.write_text(original,encoding='utf-8')
 assert not r['passed'],name
result={'passed':all(v['rejected'] for v in results.values()),'cases':results,'verifier_sha256':hashlib.sha256(Path(__file__).with_name('verify_nes_mmc3_integrated.py').read_bytes()).hexdigest()}
(a.out/'negative-tests.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
