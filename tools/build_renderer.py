"""Rebuild the C44 renderer from source; never reads a commercial ROM."""
import os
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--rgb774',action='store_true',help='Build the dual-layer RGB555 renderer');a=p.parse_args()
out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
src=ROOT/'src/renderer';base=out/'results/g13c15-renderer-v4'
shutil.copytree(src/'base',base)
for f in src.glob('*.py'):shutil.copy2(f,out/f.name)
env=os.environ.copy();env['GBC_RENDERER_PROFILE']='rgb774' if a.rgb774 else 'c44'
for script in [base/'build.py',out/'build_g13c26_renderer.py',out/'build_g13c40_renderer.py']:
 with (out/(script.stem+'.log')).open('w') as log:
  subprocess.run([sys.executable,'-X','utf8',str(script)],check=True,env=env,stdout=log,stderr=subprocess.STDOUT)
final=out/'results/g13c40-renderer-v2/gbc_snes.bin'
expected=json.loads((ROOT/'release/c44-artifacts.json').read_text())['files']['gbc_snes.bin']['sha256']
actual=hashlib.sha256(final.read_bytes()).hexdigest()
if not a.rgb774 and actual!=expected:raise SystemExit('Renderer differs from hardware-tested C44: '+actual)
shutil.copy2(final,out/'gbc_snes.bin')
print('Built RGB774 renderer' if a.rgb774 else 'PASS: byte-identical C44 renderer',actual)
