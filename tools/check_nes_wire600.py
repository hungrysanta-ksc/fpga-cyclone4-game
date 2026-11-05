"""Reprice the MMC577 SPI record format on two dense frames; no product build selection."""
import argparse
import binascii
import csv
import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from nes_transfer512 import arm_patches, input_rtl, legacy_packets
from test_nes_transfer512_spi import prepare, run

ROOT = Path(__file__).resolve().parents[1]
GENERATIONS = (952, 954)

def read(path):
    return json.loads(path.read_bytes())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pin(path, expected):
    assert sha(path) == expected, path

def prepare_probe(a):
    a.out.mkdir(parents=True, exist_ok=False)
    manifest = read(ROOT/'analysis/whole580-manifest.json')
    pins = read(ROOT/'analysis/body581-verification.json')['inputs']
    rtl = a.board/'nes_native_spi165.sv'
    pin(rtl, manifest['FPGA_inputs'][rtl.name]['sha256'])
    records = a.out/'records.csv'
    with records.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(('generation','word'))
        for g in GENERATIONS:
            files = [a.data/f'frame{g}.{ext}' for ext in ('geometry','raw')]
            for path in files: pin(path,pins[path.name])
            packets = legacy_packets(*(p.read_bytes() for p in files),g)[0]
            for b in packets:
                pos = 0
                while pos < len(b):
                    tag = int.from_bytes(b[pos:pos+2],'big')
                    assert int.from_bytes(b[pos+2:pos+4],'big') == g
                    k, idx = tag>>13, tag&8191
                    n = 8 if k==0 and idx&4096 else (2,1,7,4,7,1,2,8)[k]
                    val = b[pos+4:pos+4+n]
                    assert len(val)==n
                    word = k<<93 | g<<77 | idx<<64 | int.from_bytes(val,'big')
                    writer.writerow((g,f'{word:024x}'))
                    pos += n+4
    changed = a.out/'patched'
    changed.mkdir()
    input_rtl(a.board,changed)
    for variant, source in [('legacy',rtl),('shared',changed/rtl.name)]:
        prepare(SimpleNamespace(out=a.out/variant,rtl=source,records=records,legacy=variant=='legacy'),GENERATIONS)
    pin(a.arm/'src/obj-nes-100/firmware.stm',read(ROOT/'analysis/trial577-package.json')['firmware_SHA256'])
    shutil.copytree(a.arm,a.out/'ARM',ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    arm_patches(a.arm/'src',changed/'receiver',False,True)
    shutil.copyfile(changed/'receiver/nes_native165.c',a.out/'ARM/src/nes_native165.c')

def simulate(a):
    for variant in ('legacy','shared'):
        run(SimpleNamespace(out=a.out/variant,bin=a.bin,data=a.data,legacy=variant=='legacy'),GENERATIONS)

def pin_packets(d,g):
    packets=[]
    for line in (d/f'transactions-{g}.txt').read_text().splitlines():
        size,tx,rx=line.split()
        tx,rx=bytes.fromhex(tx),bytes.fromhex(rx)
        assert len(tx)==len(rx)==int(size)
        if tx[0]==0xd1:
            payload=rx[1:-2]
            assert binascii.crc_hqx(payload,65535)==int.from_bytes(rx[-2:],'big')
            packets.append(payload)
    return packets

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('prepare','sim'))
    for key in ('arm','board','data','out','bin'):
        p.add_argument('--'+key,type=Path,required=key in ('data','out'))
    a=p.parse_args()
    (prepare_probe if a.mode=='prepare' else simulate)(a)
