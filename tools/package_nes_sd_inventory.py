# SPDX-License-Identifier: MIT
"""Create the separately authorized firmware-only diagnostic kit; no SD mutation."""
from pathlib import Path
import argparse,hashlib,json,zlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
FW_SHA='8215d81dd84a07f3dfffe5163163c07ef1166fcbfab25b95cbc4942dbc42f724'
def digest(b):return hashlib.sha256(b).hexdigest()
def package(firmware,source_zip,out):
    fw=firmware.read_bytes();assert len(fw)==132768 and digest(fw)==FW_SHA
    assert fw[:4]==b'STM3' and int.from_bytes(fw[8:12],'little')==len(fw)-512 and int.from_bytes(fw[12:16],'little')==zlib.crc32(fw[512:])
    assert b'SDINFO072-BASE069' in fw
    with zipfile.ZipFile(source_zip) as z:assert {'source/src/nes_sd_inventory.c','source/src/main.c','source/LICENSE','source/src/Makefile'}<=set(z.namelist()) and z.testzip() is None
    out.mkdir(exist_ok=False)
    m=dict(candidate='NES-SD-INSPECTION-072',identity='SDINFO072-BASE069',payload_paths=['sd2snes/firmware.stm'],
           firmware=dict(size=len(fw),sha256=digest(fw)),corresponding_source=dict(name=source_zip.name,sha256=digest(source_zip.read_bytes())),
           physical_execution=False,nes_pair_installable=False,collect_inputs_read_only=True,
           new_report_pattern='/HW003000.TXT .. /HW003999.TXT',restore_required=True)
    raw=(json.dumps(m,ensure_ascii=False,indent=2)+'\n').encode();(out/'manifest.json').write_bytes(raw)
    entries={'sd2snes/firmware.stm':fw,'manifest.json':raw,'README.ko.md':(ROOT/'docs/SDINFO072-RUN.ko.md').read_bytes(),'LICENSE.txt':(ROOT/'licenses/sd2snes-COPYING').read_bytes()}
    with zipfile.ZipFile(out/'FXPAK-SDINFO072-SD.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n,b in entries.items():
            info=zipfile.ZipInfo(n,(2026,10,7,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
    return m
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--firmware',type=Path,required=True);p.add_argument('--source-zip',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    print(json.dumps(package(a.firmware,a.source_zip,a.out),indent=2))
