# SPDX-License-Identifier: MIT
"""Check actual081 ARM init/mount binding and exact unchanged native prefix."""
from pathlib import Path
import argparse,json,re,subprocess
from nes_report081_prepare import sha, ROOT
def main():
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--objdump',type=Path,required=True);a=p.parse_args()
    s=a.arm/'source/src';o=s/'obj-report079'
    dis=subprocess.check_output([str(a.objdump),'-d',str(o/'sd2snes.elf')]).decode().replace('\r\n','\n')
    (a.arm/'disassembly.txt').write_text(dis,encoding='utf-8')
    fs=dict(re.findall(r'^[0-9a-f]+ <([^>]+)>:\n(.*?)(?=^[0-9a-f]+ <|\Z)',dis,re.M|re.S));edges={}
    for parent,child,count in [('main','sdreport_run081',1),('sdreport_run081','report_session081',1),
        ('report_session081','sdn_report_initialize081',1),('report_session081','file_init',1),
        ('file_init','f_mount',1),('find_volume','disk_initialize',1),('disk_initialize','sdn_report_mounted081',1),
        ('report_session081','report_boot080',1),('report_boot080','report_decode080',2),
        ('report_session081','report_line080',5),('report_session081','sdinv_write_report',1),('write_report','sdinv_checkpoint079',7),
        ('report_half081','nes_return_delay',1)]:
        n=len(re.findall(r'\b(?:bl|b\.w)\s+[0-9a-f]+ <'+child+r'>',fs[parent]));assert n==count,(parent,child,n)
        edges[parent+' -> '+child]=n
    assert '<file_init>' not in fs['main']
    assert fs['report_session081'].index('<sdn_report_initialize081>')<fs['report_session081'].index('<file_init>')<fs['report_session081'].index('<report_boot080>')
    for name in ['sdn_initialize','send_command_slow','cmd_slow','acmd_slow','sdn_getinfo','printf']:
        assert '<'+name+'>' not in fs['sdn_report_initialize081']+fs['report_command081']+fs['sdn_report_mounted081'],name
    prep=json.loads((a.arm/'preparation081.json').read_bytes());prefix='work/arm-02/source/src/'
    same=['ff.c','fileops.c','stm32f4xx/timer.c','fpga_spi.c','fpga.c','memory.c','nes_menu_return.c','nes_diag_runtime.c','snes.c','nes_report_checkpoint079.c','nes_report_boot080.c','nes_report_decode080.c']
    for n in same:assert sha(s/n)==prep['inputs'][prefix+n],n
    native=(s/'stm32f4xx/sdnative.c').read_bytes();suffix=b'\n#include <string.h>\n#include "nes_report_init081.inc"\n';assert native.endswith(suffix)
    import hashlib
    assert hashlib.sha256(native[:-len(suffix)]).hexdigest()==prep['native_prefix_sha256']==prep['inputs'][prefix+'stm32f4xx/sdnative.c']
    for n,rel in [('nes_report_init081.inc','stm32f4xx/nes_report_init081.inc'),('nes_report_disk081.c','nes_report_disk081.c')]:assert sha(s/rel)==sha(ROOT/'src/nes/firmware'/n)
    fw=o/'firmware.stm';assert b'SDREPORT081' in fw.read_bytes()
    result=dict(edges=edges,firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(o/'sd2snes.elf'),unchanged_native=same,native_original_prefix_preserved=True,arm_executed=False,installable=False)
    (a.arm/'arm-check081.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
