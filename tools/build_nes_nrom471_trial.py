# SPDX-License-Identifier: MIT
"""Package only the verified471 pair, moving/static fixtures and known restores."""
import argparse,hashlib,json,zipfile,zlib
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--arm',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
r=json.loads((ROOT/'analysis/nrom471-verification.json').read_text(encoding='utf8'));assert r['passed']
fw=a.arm/'obj-nes-100/firmware.stm';image=a.board/'fpga_nrom471.bi3';moving=BASE/'probes/nes-nrom471/scene02/nrom471.nes';static=BASE/'probes/nes-nrom428/fixture01/nrom16.nes'
assert sha(fw)==r['artifacts']['firmware_stm'] and sha(image)==r['artifacts']['FPGA_BI3'] and sha(moving)==r['artifacts']['moving_ROM']
# Independent byte decoder is intentionally not the encoder/programmer path.
b=image.read_bytes();decoded=bytearray();i=0
while i<len(b):
 op=b[i];i+=1
 if op==0x9b:assert i<len(b);decoded.append(b[i]);i+=1
 elif op in (0x5b,0x77):
  n=3 if op==0x77 else 2;assert i+n<=len(b);v=b[i];count=b[i+1]+(b[i+2]*256 if n==3 else 0);assert count;decoded.extend(bytes([v])*count);i+=n
 else:decoded.append(op)
assert bytes(decoded)==(a.board/'board.rbf').read_bytes()
files={'01-NROM471-MOVING-SD-ROOT/sd2snes/firmware.stm':fw.read_bytes(),'01-NROM471-MOVING-SD-ROOT/sd2snes/fpga_nrom471.bi3':b,'01-NROM471-MOVING-SD-ROOT/sd2snes/nes/nrom471.nes':moving.read_bytes(),'01-NROM471-MOVING-SD-ROOT/NES NROM 471.nh1':b'','03-STATIC-COMPARE-SD-ROOT/sd2snes/nes/nrom471.nes':static.read_bytes()}
old=BASE/'probes/nes-nrom467/trial01/NROM467-LIMITED-TRIAL.zip';oldspec=json.loads((ROOT/'analysis/nrom467-trial.json').read_text(encoding='utf8'));assert sha(old)==oldspec['zip_sha256']
with zipfile.ZipFile(old) as z:
 for n in z.namelist():
  if n.startswith('01-NROM-SD-ROOT/'):files[n.replace('01-NROM-SD-ROOT/','02-RESTORE467-SD-ROOT/',1)]=z.read(n)
  elif n.startswith('02-RESTORE164-SD-ROOT/'):files[n.replace('02-RESTORE164-SD-ROOT/','04-RESTORE164-SD-ROOT/',1)]=z.read(n)
 for n in ['sd2snes/fpga_base.bi3','sd2snes/m3nu.bin']:files['01-NROM471-MOVING-SD-ROOT/'+n]=z.read('01-NROM-SD-ROOT/'+n)
files['읽어주세요.txt']=(ROOT/'docs/nes-nrom471-trial.ko.md').read_bytes()
files['기술검증.txt']=(ROOT/'docs/nes-nrom471-contract.ko.md').read_bytes()
files['verification.json']=(ROOT/'analysis/nrom471-verification.json').read_bytes()
manifest={'trial':'NROM471','input_wire_header':'2232','output_client':'2271','firmware_sha256':sha(fw),'FPGA_sha256':sha(image),'moving_scene_crc32_hex':f'{zlib.crc32(moving.read_bytes()):08x}','static_scene_crc32_hex':f'{zlib.crc32(static.read_bytes()):08x}','whole_physical_timing_measured':False,'fps60_proven':False,'files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in files.items()}}
files['manifest.json']=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode();out=a.out/'NROM471-COST-PROBE.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for n,v in files.items():z.writestr(n,v)
with zipfile.ZipFile(out) as z:assert set(z.namelist())==set(files) and all(z.read(n)==v for n,v in files.items())
r={'passed':True,'zip_sha256':sha(out),'zip_bytes':out.stat().st_size,'manifest':manifest,'scope':'verified pair and offline restore package; user hardware required for total time/FPS'};(a.out/'result.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf8');print(json.dumps({'zip':str(out),'bytes':out.stat().st_size,'sha256':sha(out),'moving_crc':manifest['moving_scene_crc32_hex'],'static_crc':manifest['static_scene_crc32_hex']}))
