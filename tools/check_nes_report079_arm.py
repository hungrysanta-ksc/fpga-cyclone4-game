# SPDX-License-Identifier: MIT
"""Check final079 ELF callsites and executed source pins; not ARM execution."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--objdump',type=Path,required=True);a=p.parse_args()
    src=a.arm/'source/src';obj=src/'obj-report079';elf=obj/'sd2snes.elf'
    dis=subprocess.check_output([str(a.objdump),'-d',str(elf)]).decode().replace('\r\n','\n')
    (a.arm/'disassembly.txt').write_text(dis,encoding='utf-8',newline='\n')
    functions=dict(re.findall(r'^[0-9a-f]+ <([^>]+)>:\n(.*?)(?=^[0-9a-f]+ <|\Z)',dis,re.M|re.S))
    edges={}
    def calls(parent,child,count=None):
        n=len(re.findall(r'\b(?:bl|b\.w)\s+[0-9a-f]+ <'+re.escape(child)+r'>',functions[parent]))
        assert n>0 and (count is None or n==count),(parent,child,n)
        edges[parent+' -> '+child]=n
    calls('main','sdreport_run079',1)
    calls('sdreport_run079','sdinv_write_report',1)
    calls('sdinv_write_report','write_report',1)
    calls('write_report','sdinv_checkpoint079',7)
    for target in ['sram_writeblock','sram_readblock','snes_reset','nes_return_delay','nes_return_io_step','nes_return_fail']:
        calls('sdinv_checkpoint079',target)
    for target in ['f_open','f_write','f_sync','f_close','f_read']:calls('write_report',target)
    assert '<sdinv_collect>' not in functions['sdreport_run079']
    assert '<load_rom>' not in functions['main'] and '<nes_menu_diagnostic_run>' not in functions['main']
    for n in ['nes_report_checkpoint079.c','nes_report_checkpoint079.h','nes_report_platform079.c']:
        assert sha(src/n)==sha(ROOT/'src/nes/firmware'/n),n
    prep=json.loads((a.arm/'preparation079.json').read_bytes())
    for n in prep['unchanged_native']:assert sha(src/n)==prep['inputs']['077/arm/source/src/'+n],n
    mini=a.arm/'source/verilog/sd2snes_mini/fpga_mini.bi3'
    assert sha(mini)=='9ae79c3028391063338d42ae16b19acf48d0d80858939b015ef6481f55cbefe9'
    firmware=obj/'firmware.stm';raw=firmware.read_bytes();assert b'SDREPORT079' in raw
    result=dict(edges=edges,firmware_bytes=len(raw),firmware_sha256=sha(firmware),elf_sha256=sha(elf),mini_sha256=sha(mini),arm_executed=False,installable=False)
    (a.arm/'arm-check079.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__':main()
