# SPDX-License-Identifier: MIT
"""Apply CF86 upper-session changes to a private, verified077 active-menu tree."""
from pathlib import Path
import argparse,json,shutil
from nes_cf86_session094 import adapt
from nes_mcu_loader import sha,ROOT

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 baseline=a.baseline.resolve();out=a.out.resolve();assert not out.exists()
 # The immutable077 manifest covers the post-build source, unlike build-inputs
 # which intentionally records generated files before Make changes them.
 manifest=json.loads((baseline.parents[1]/'manifest.json').read_text())
 entries=manifest['files']
 if isinstance(entries,list):entries={x['path']:x['sha256'] for x in entries}
 pins={k[len('arm/source/'):]:v for k,v in entries.items() if k.startswith('arm/source/')}
 assert pins and all(sha(baseline/k)==(v['sha256'] if isinstance(v,dict) else v) for k,v in pins.items())
 shutil.copytree(baseline,out);src=out/'src';adapt(src)
 f=src/'Makefile';s=f.read_text();assert s.count('nes_menu076.c')==1
 f.write_text(s.replace('nes_menu076.c','nes_menu076.c nes_cf86_session094.c'),encoding='utf-8',newline='\n')
 (src/'VERSION').write_text('RELEASE_VERSION = "CF86-MCU094"\n',encoding='utf-8')
 # Make's cache belongs to this fresh copy, not the frozen baseline.
 cache=src/'.ARG_VERSION'
 if cache.exists():cache.unlink()
 changed=[k for k in pins if k!='src/.ARG_VERSION' and sha(baseline/k)!=sha(out/k)]
 allowed=['src/nes_h1_stm32.c','src/nes_rom_spi.c','src/nes_rom_verify.c','src/nes_menu_diagnostic.c','src/Makefile','src/VERSION']
 assert sorted(changed)==sorted(allowed),changed
 (out/'preparation094.json').write_text(json.dumps(dict(baseline='077 active-menu, native SD077 and menu076 retained',baseline_manifest_sha256=sha(baseline.parents[1]/'manifest.json'),changed=changed,source_files={p.relative_to(src).as_posix():sha(p) for p in src.rglob('*') if p.is_file()},installable=False),indent=2)+'\n',encoding='utf-8')
 shutil.copy2(__file__,out/'executed-prepare094.py')
 print('PASS094 prepared077 baseline; 6 changed files plus 2 new session files')
if __name__=='__main__':main()
