# SPDX-License-Identifier: MIT
import argparse,sys,zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from check_nes_sd_inventory073 import check
def repair(raw):
    prefix=raw.split(b'payload_crc32=')[0];return prefix+('payload_crc32=%08x\r\nSDINFO073_END\r\n'%zlib.crc32(prefix)).encode()
def run(raw):
    count=0;result=check(raw);assert result['original_firmware_preliminary'] and result['original_distinct_crc'] and not result['nes_pair_installable'];count+=1
    cases=[raw[:-1],raw+b'bad',raw.replace(b'finished=1',b'finished=0'),raw.replace(b'blocked=0',b'blocked=1'),raw.replace(b'read_only_inputs=yes',b'read_only_inputs=no'),raw.replace(b'file0_status=1',b'file0_status=9'),raw.replace(b'file0_size=1024',b'file0_size=1023'),raw.replace(b'file0_size=1024',b'file0_size=4294967296'),raw.replace(b'file0_consumed=1024',b'file0_consumed=1023'),raw.replace(b'header0_available=1',b'header0_available=0'),raw.replace(b'header0_address=0000ffb0',b'header0_address=00000000'),raw.replace(b'file1_path=/sd2snes/firmware.stm',b'file1_path=/unknown'),raw.replace(b'identity=SDINFO073-BASE069',b'identity=SDINFO071'),raw.replace(b'finished=1\r\n',b'finished=1\r\nfinished=1\r\n'),raw.replace(b'finished=1\r\n',b'finished=1\r\nextra=1\r\n')]
    for i,bad in enumerate(cases):
        for candidate in ([bad] if i<2 else [bad,repair(bad)]):
            try:check(candidate)
            except (ValueError,UnicodeError):count+=1
            else:raise AssertionError('Malformed report accepted')
    print('PASS073 report integrity/shape checks='+str(count)+' no_install_approval=1')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args();run(a.report.read_bytes())
