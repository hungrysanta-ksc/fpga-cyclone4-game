# SPDX-License-Identifier: MIT
"""Private limited480 trial, no SMB3 ROM; byte-preserved476/164/467 restores."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
digest = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf8'))
p = argparse.ArgumentParser(description=__doc__)
for n in ['arm', 'assembly', 'prior', 'out']:
    p.add_argument('--'+n, type=Path, required=True)
a = p.parse_args()
r = read(ROOT/'analysis/mmc480-verification.json')
old = read(ROOT/'analysis/receive476-package.json')
assert r['passed'] and r['limited_trial_ready'] and r['independent_PPU_pixels']['mismatches']==0
assert digest(a.prior.read_bytes()) == old['zip_sha256']
fw = (a.arm/'obj-nes-100/firmware.stm').read_bytes()
fpga = (a.assembly/'fpga_mmc480.bi3').read_bytes()
assert digest(fw) == r['ARM']['firmware_SHA256'] and digest(fpga)==r['FPGA']['BI3_SHA256']
for marker in [b'NES MMC3 480.nh1',b'mmc480.nes',b'fpga_mmc480.bi3',b'nes-progress-mmc480.txt',b'nes-game-last-mmc480.txt',b'nes-budget-mmc480.txt',b'board_expected_hex=79',b'cost_schema=474']:
    assert marker in fw, marker
files = {}
restored = {}
roots = {'01-NROM476-MOVING-SD-ROOT/':'02-RESTORE476-SD-ROOT/', '05-RESTORE164-SD-ROOT/':'03-RESTORE164-SD-ROOT/', '06-RESTORE467-SD-ROOT/':'04-RESTORE467-SD-ROOT/'}
with zipfile.ZipFile(a.prior) as z:
    for n in z.namelist():
        for before, after in roots.items():
            if n.startswith(before):
                target = n.replace(before,after,1)
                files[target] = z.read(n)
                restored[target] = digest(files[target])
    for n in ['sd2snes/fpga_base.bi3','sd2snes/m3nu.bin']:
        files['01-MMC480-SMB3-SD-ROOT/'+n] = z.read('01-NROM476-MOVING-SD-ROOT/'+n)
files['01-MMC480-SMB3-SD-ROOT/sd2snes/firmware.stm'] = fw
files['01-MMC480-SMB3-SD-ROOT/sd2snes/fpga_mmc480.bi3'] = fpga
files['01-MMC480-SMB3-SD-ROOT/NES MMC3 480.nh1'] = b''
files['01-MMC480-SMB3-SD-ROOT/sd2snes/nes/ROM-NOT-INCLUDED.txt'] = ('SMB3(J) original required: mmc480.nes,393232 bytes,CRC32=5a04eed7.\nExisting SD game227.nes may be copied if it is the identical original.\nDo not substitute another region/revision or the NROM pattern.\n').encode()
for name, source in [('읽어주세요.txt','docs/nes-mmc480-trial.ko.md'),('기술검증.txt','docs/nes-mmc480-contract.ko.md'),('verification.json','analysis/mmc480-verification.json')]:
    files[name] = (ROOT/source).read_bytes()
assert not any(n.startswith('01-') and n.endswith('.nes') for n in files)
manifest = {'candidate':'MMC480','scope':__doc__,'private_limited_trial':True,'public_release':False,'hardware_verified':False,'physical_FPS':None,'SMB3_ROM_included':False,'required_ROM':{'file':'sd2snes/nes/mmc480.nes','bytes':393232,'CRC32':'5a04eed7'},'profile_hex':'79','input':'2232','client':'2271','cost_schema':474,'firmware_SHA256':digest(fw),'FPGA_SHA256':digest(fpga),'restore_byte_preserved':restored,'files':{n:{'bytes':len(b),'SHA256':digest(b)} for n,b in files.items()}}
files['manifest.json'] = (json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf8')
a.out.mkdir(parents=True,exist_ok=False)
archive = a.out/'MMC480-SMB3-TRIAL.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for n,b in files.items():
        z.writestr(n,b)
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist())==set(files) and all(z.read(n)==b for n,b in files.items())
result = {'passed':True,'ZIP_name':archive.name,'ZIP_bytes':archive.stat().st_size,'ZIP_SHA256':digest(archive.read_bytes()),'firmware_SHA256':digest(fw),'FPGA_SHA256':digest(fpga),'files':manifest['files'],'restore_byte_preserved':restored,'required_ROM':manifest['required_ROM'],'SMB3_ROM_included':False,'private_trial_ready':True,'hardware_verified':False,'physical_FPS':None,'baseline476_ZIP_SHA256':old['zip_sha256'],'package_tool_SHA256':digest(Path(__file__).read_bytes())}
(a.out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
print(json.dumps({k:result[k] for k in ['passed','ZIP_name','ZIP_bytes','ZIP_SHA256','SMB3_ROM_included']}))
