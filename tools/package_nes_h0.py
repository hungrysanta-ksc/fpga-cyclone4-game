# Package previously verified, original SNES diagnostics. SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,struct,zlib,zipfile
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def png(rgb):
 assert len(rgb)==256*239*3
 def chunk(kind,b):return struct.pack('>I',len(b))+kind+b+struct.pack('>I',zlib.crc32(kind+b)&0xffffffff)
 raw=b''.join(b'\0'+rgb[y*768:(y+1)*768] for y in range(239))
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',256,239,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
def build(out,repo):
 assert not out.exists() and not out.with_suffix('.zip').exists()
 old=json.loads((repo/'analysis/chr-residency-artifacts.json').read_text())
 entries={e['path']:e for v in old.values() if isinstance(v,list) for e in v if isinstance(e,dict) and 'sha256' in e}
 def checked(rel):
  p=repo/rel;e=entries[rel];assert sha(p)==e['sha256'] and p.stat().st_size==e['bytes'];return p.read_bytes()
 proof=json.loads(checked('analysis/chr-residency-verification.json'));assert proof['audit_pass']
 files={};origins=[]
 for name in ('top','bottom','fine_x'):
  base='analysis/local-chr-residency-025/'+name
  info=json.loads(checked(base+'/build/manifest.json'))
  assert info['fault']=='none' and proof['cases'][name]['normal_pass']
  rom=checked(base+'/build/replay.sfc');assert len(rom)==131072
  assert hashlib.sha256(rom).hexdigest()==info['rom_sha256']
  rgb=checked(base+'/capture/frame-003.rgb')
  assert rgb==checked(base+'/build/expected-4.rgb')
  files['nes-h0-'+name+'.sfc']=rom
  files['expected-'+name+'.png']=png(rgb)
  origins.append({'case':name,'source_candidate':info['candidate'],'rom_sha256':info['rom_sha256'],'viewport':info['viewport'],'capture_sha256':hashlib.sha256(rgb).hexdigest()})
 files['READ-ME.ko.md']=(repo/'docs/nes-hardware-first-test.ko.md').read_bytes()
 files['results.tsv']='case\tcold_or_warm\tfirst_picture\tstable_30sec\treset_to_menu\tphoto_id\tnotes\n'.encode()
 checker="""param([string]$Folder=$PSScriptRoot)
$ErrorActionPreference='Stop'
$m=Get-Content -LiteralPath (Join-Path $Folder 'manifest.json') -Raw | ConvertFrom-Json
foreach($f in $m.files){
 $p=Join-Path $Folder $f.path
 if((Get-Item -LiteralPath $p).Length -ne $f.bytes -or (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() -ne $f.sha256){throw ('Mismatch: '+$f.path)}
}
Write-Output 'PASS H0 package files; this does not certify hardware behavior.'
"""
 files['Verify-Package.ps1']=checker.encode()
 out.mkdir(parents=True)
 for name,b in files.items():(out/name).write_bytes(b)
 manifest={'candidate':'NES-H0-REPLAY-029','source_candidate':'NES-R2-CHR-RESIDENCY-025','hardware_tested':False,'firmware_update':False,'nes_fpga_included':False,'cases':origins,'files':[{'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in files.items()]}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 with zipfile.ZipFile(out.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(out.iterdir()):z.write(p,p.name)
 return {'package':out.as_posix(),'zip_sha256':sha(out.with_suffix('.zip')),'manifest_sha256':sha(out/'manifest.json'),'roms':origins}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 print(json.dumps(build(a.out,Path(__file__).resolve().parents[1]),indent=2))
