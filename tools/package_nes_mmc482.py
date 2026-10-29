# SPDX-License-Identifier: MIT
"""Private482 diagnostic ZIP, no SMB3 ROM; preserve exact480 restore contents."""
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
    p.add_argument('--'+n, required=True, type=Path)
a = p.parse_args()
r = read(ROOT/'analysis/mmc482-verification.json')
old = read(ROOT/'analysis/mmc480-package.json')
assert r['passed'] and r['diagnostic_trial_ready']
assert digest(a.prior.read_bytes()) == old['ZIP_SHA256']
fw = (a.arm/'obj-nes-100/firmware.stm').read_bytes()
fpga = (a.assembly/'fpga_mmc482.bi3').read_bytes()
assert digest(fw) == r['ARM']['firmware_SHA256'] and digest(fpga) == r['FPGA']['BI3_SHA256']
files, restores = {}, {}
active = '01-MMC482-BOOTDIAG-SD-ROOT/'
with zipfile.ZipFile(a.prior) as z:
    for n in z.namelist():
        if n.startswith(('02-RESTORE476-SD-ROOT/', '03-RESTORE164-SD-ROOT/', '04-RESTORE467-SD-ROOT/')):
            files[n] = z.read(n)
            restores[n] = digest(files[n])
            assert digest(files[n]) == old['files'][n]['SHA256']
    for n in ['sd2snes/fpga_base.bi3', 'sd2snes/m3nu.bin']:
        files[active+n] = z.read('01-MMC480-SMB3-SD-ROOT/'+n)
assert restores and restores == old['restore_byte_preserved']
files[active+'sd2snes/firmware.stm'] = fw
files[active+'sd2snes/fpga_mmc482.bi3'] = fpga
files[active+'NES MMC3 482.nh1'] = b''
files[active+'sd2snes/nes/ROM-NOT-INCLUDED.txt'] = b'Copy your original mmc480.nes as mmc482.nes (393232 bytes, CRC32 5a04eed7). ROM bytes unchanged; SMB3 ROM not included.\n'
files['읽어주세요.txt'] = (ROOT/'docs/nes-mmc482-trial.ko.md').read_bytes()
files['verification.json'] = (ROOT/'analysis/mmc482-verification.json').read_bytes()
assert not any(n.startswith(active) and n.lower().endswith('.nes') for n in files)
manifest = {'candidate': 'MMC482 boot diagnostic', 'profile_hex': '7b', 'status_version': 3,
            'private_trial_ready': True, 'public_release': False, 'hardware_verified': False,
            'root_cause_confirmed': False, 'physical_FPS': None, 'SMB3_ROM_included': False,
            'required_ROM': {'file': 'sd2snes/nes/mmc482.nes', 'bytes': 393232, 'CRC32': '5a04eed7',
                             'SHA256': 'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'},
            'firmware_SHA256': digest(fw), 'FPGA_SHA256': digest(fpga),
            'restore_byte_preserved': restores,
            'files': {n: {'bytes': len(b), 'SHA256': digest(b)} for n, b in files.items()}}
files['manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode('utf8')
a.out.mkdir(parents=True, exist_ok=False)
archive = a.out/'MMC482-BOOTDIAG.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for n, b in files.items():
        z.writestr(n, b)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None and set(z.namelist()) == set(files)
    assert all(z.read(n) == b for n, b in files.items())
result = dict(manifest, passed=True, ZIP_name=archive.name, ZIP_bytes=archive.stat().st_size,
              ZIP_SHA256=digest(archive.read_bytes()), baseline480_ZIP_SHA256=old['ZIP_SHA256'])
(a.out/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps({k: result[k] for k in ['passed', 'ZIP_name', 'ZIP_bytes', 'ZIP_SHA256']}))
