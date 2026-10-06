# Capture new original Mapper4 video workloads. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,hashlib,json,os,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('mesen','probe','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();exe=a.mesen.resolve();probe=a.probe.resolve();out=a.out.resolve()
 assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
 m=json.loads((probe/'manifest.json').read_text())
 assert m['original_diagnostic'] and sha(probe/'mmc3.nes')==m['sha256']
 script=Path(__file__).resolve().parents[1]/'tests/nes-functional/capture_video_workloads.lua'
 (out/'capture.lua').write_text('local OUT_DIR='+json.dumps(out.as_posix())+'\n'+script.read_text(),encoding='utf-8',newline='\n')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (out/'mesen.log').open('wb') as log:
  proc=subprocess.run([str(exe),'--testRunner',str(out/'capture.lua'),str(probe/'mmc3.nes'),'--timeout=30',
    '--doNotSaveSettings','--enableStdout'],stdout=log,stderr=subprocess.STDOUT,env=env,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
 result=dict(candidate=m['candidate'],case=m['case'],exit_code=proc.returncode,rom_sha256=m['sha256'],
   manifest_sha256=sha(probe/'manifest.json'),runner_sha256=sha(__file__),capture_script_sha256=sha(script),
   tools={n:sha(exe.parent/n) for n in ('Mesen.exe','Mesen.dll','MesenCore.dll','settings.json')})
 (out/'capture.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 assert proc.returncode==0,(out/'mesen.log').read_text(errors='replace')
 print(json.dumps(dict(case=m['case'],exit_code=proc.returncode,frames=(out/'frames.tsv').read_text().splitlines()),indent=2))
if __name__=='__main__':main()