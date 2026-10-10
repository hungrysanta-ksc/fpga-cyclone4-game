# SPDX-License-Identifier: MIT
"""Integrity and scope of frozen149, without repeating completed tests."""
from pathlib import Path
import argparse,json
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
    m=json.loads((ROOT/'analysis/game149-verification.json').read_bytes());e=a.baseline/'nes-game149/evidence'
    assert sha(e/'manifest.json')==m['manifest_sha256']
    files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['file_count']
    for n,h in files.items():assert sha(e/n)==h,n
    for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
    h=json.loads((e/'host/result.json').read_bytes());assert h['passed']
    for n,digest in h['production_sources'].items():assert sha(e/'arm/src'/n)==digest,n
    arm=json.loads((e/'armcheck/result.json').read_bytes())
    assert arm['strong_nmi'] and arm['firmware_bytes']==186860 and not arm['installable']
    assert sha(e/'arm/src/obj-nes-100/firmware.stm')==arm['firmware_sha256']
    spi=json.loads((e/'spi/result.json').read_bytes());assert spi['passed'] and spi['master_hz']==2625000
    old=a.baseline/'nes-game148/evidence/core03'
    for n in ['nes_rom_service.sv','nes_rom_physical.sv','nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_spi.sv']:
        assert sha(e/'spi'/n)==sha(old/n),n
    prep=json.loads((e/'arm/preparation149.json').read_bytes())
    assert prep['payload_bytes']==393216 and prep['board_id']==95 and prep['begin_argument']==2
    assert not m['sd_package'] and not m['physical_test']
    print('PASS149 frozen MCU transport/geometry evidence; FPGA unchanged; hardware/package pending')
if __name__=='__main__':main()
