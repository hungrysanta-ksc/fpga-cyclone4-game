"""Capture the original Mapper4 diagnostic in isolated Mesen. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,json,os,subprocess,hashlib
from build_nes_mmc3 import build

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('mesen','probe','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();probe=a.probe.resolve();exe=a.mesen.resolve();assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
 build(out/'original-check');assert (probe/'mmc3.nes').read_bytes()==(out/'original-check/mmc3.nes').read_bytes()
 script=Path(__file__).resolve().parents[1]/'tests/nes-functional/capture_mmc3_irq_phase.lua';(out/'capture.lua').write_text('local OUT_DIR='+json.dumps(out.as_posix())+'\n'+script.read_text(encoding='utf-8-sig'),encoding='utf-8',newline='\n')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (out/'mesen.log').open('wb') as log:r=subprocess.run([str(exe),'--testRunner',str(out/'capture.lua'),str(probe/'mmc3.nes'),'--timeout=50','--doNotSaveSettings','--enableStdout'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
 result=dict(exit_code=r.returncode,rom_sha256=sha(probe/'mmc3.nes'),capture_sha256=sha(script),runner_sha256=sha(Path(__file__)),tools={n:sha(exe.parent/n) for n in ('Mesen.exe','Mesen.dll','MesenCore.dll','settings.json')})
 (out/'capture.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2));raise SystemExit(r.returncode)
if __name__=='__main__':main()
