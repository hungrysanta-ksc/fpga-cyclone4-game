# SPDX-License-Identifier: MIT
"""Only restore140's menu-return source: the extra post-report work must fail."""
from pathlib import Path
import argparse,shutil,subprocess,json
from nes_spi_boot import sha,ROOT
p=argparse.ArgumentParser()
for n in ['baseline','host','out','gcc']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();S=a.host;O=a.out;assert not O.exists()
e=a.baseline/'nes-response140/evidence'
meta=json.loads((ROOT/'analysis/response140-verification.json').read_bytes())
assert sha(e/'manifest.json')==meta['manifest_sha256']
assert sha(e/'host01/nes_menu_return.c')==json.loads((e/'manifest.json').read_bytes())['files']['host01/nes_menu_return.c']
shutil.copytree(S,O,ignore=shutil.ignore_patterns('*.exe','*.log','case-*','*.txt','result.json'))
shutil.copy2(a.baseline/'nes-response140/evidence/host01/nes_menu_return.c',O/'nes_menu_return.c')
sources=['card.c','host109.c','printf103.c','linked109-css.c','linked112-checkpoint.c']+['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
with (O/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=O,stdout=f,stderr=subprocess.STDOUT)
assert not r.returncode
with (O/'old-budget.log').open('wb') as f:r=subprocess.run([str(O/'host.exe'),'20','0',*[str(O/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=O,stdout=f,stderr=subprocess.STDOUT,timeout=180)
log=(O/'old-budget.log').read_text();assert r.returncode!=0 and 'nes_return_io_step()' in log,log[-1000:]
(O/'result.json').write_text(json.dumps(dict(negative_rejected=True,returncode=r.returncode,only_old_menu_return_restored=True,post_report_extra_polls=20000,physical=False),indent=2)+'\n');print('PASS141 causal control: old log budget blocks post-report work; new host case20 passes')
