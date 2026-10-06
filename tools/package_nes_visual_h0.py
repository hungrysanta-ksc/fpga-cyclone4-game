# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
from PIL import Image
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('build','capture','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();repo=Path(__file__).resolve().parents[1]
 assert not a.out.exists() and not a.out.with_suffix('.zip').exists()
 result=json.loads((a.capture/'result.json').read_text());assert result['passed']
 rom=a.build/'nes-h0-visual-030.sfc'
 assert sha(rom)==result['capture']['rom_sha256']==json.loads((a.build/'manifest.json').read_text())['rom_sha256']
 a.out.mkdir(parents=True)
 shutil.copyfile(rom,a.out/rom.name)
 for page,index in [(1,0),(2,2),(3,4)]:
  b=(a.capture/f'frame-{index:03}.rgb').read_bytes()
  assert b==bytes(7*256*3)+(a.build/f'expected-{page}.rgb').read_bytes()+bytes(8*256*3)
  Image.frombytes('RGB',(256,239),b).save(a.out/f'expected-{page}.png')
 shutil.copyfile(repo/'docs/nes-visual-h0-test.ko.md',a.out/'READ-ME.ko.md')
 (a.out/'results.tsv').write_text('date\tconsole_region\tcart\tfirmware\tdisplay\tcold_warm\treadable\tcycles_123\tdefects\treset_menu\n')
 checker="""param([string]$Folder=$PSScriptRoot)
$ErrorActionPreference='Stop'
$m=Get-Content -LiteralPath (Join-Path $Folder 'manifest.json') -Raw | ConvertFrom-Json
foreach($f in $m.files){
 $p=Join-Path $Folder $f.path
 if((Get-Item -LiteralPath $p).Length -ne $f.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() -ne $f.sha256){throw ('Mismatch: '+$f.path)}
}
Write-Output 'PASS package integrity; hardware observations are still required.'
"""
 (a.out/'Verify-Package.ps1').write_text(checker,newline='\n')
 m={'candidate':'NES-H0-VISUAL-030','hardware_tested':False,'rom_sha256':sha(rom),'emulator_result_sha256':sha(a.capture/'result.json'),
  'files':[{'path':f.name,'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(a.out.iterdir())]}
 (a.out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with zipfile.ZipFile(a.out.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(a.out.iterdir()):z.write(f,f.name)
 print(json.dumps({'package':str(a.out.with_suffix('.zip')),'zip_sha256':sha(a.out.with_suffix('.zip')),'rom_sha256':sha(rom)},indent=2))
if __name__=='__main__':main()
