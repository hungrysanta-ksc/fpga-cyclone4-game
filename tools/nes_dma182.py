# SPDX-License-Identifier: MIT
"""Materialize RUN-only DMA transport from the exact deployed181 ARM inputs."""
from pathlib import Path
import argparse,json
from nes_board181 import copy_pins
from nes_game147 import ROOT,sha
from nes_clip178 import replace


def bulk(s):
    s=replace(s,'bool nes_native165_bulk(', '#include "nes_dma182.inc"\nbool nes_native165_bulk(')
    s=replace(s,' (void)NES165_READ();(void)NES165_SR();',
                ' if(!nes182_available())return nes_cf86_fail094();\n (void)NES165_READ();(void)NES165_SR();')
    s=replace(s,' io->select(io->ctx,false);\n SPI1->CR1=',
                ' struct nes182_saved saved;nes182_claim(&saved,tx,rx,count);\n io->select(io->ctx,false);\n SPI1->CR1=')
    start=s.index(' for(unsigned i=0;i<count;i++) {')
    end=s.index(' if(!nes165_wait(SPI_SR_TXE,true)||',start)
    s=s[:start]+' if(!nes182_run())goto fail;\n'+s[end:]
    s=replace(s,' io->wait_us(io->ctx,2);\n if(!nes_cf86_check094())goto fail;\n io->select(io->ctx,false);',
                ' nes182_restore(&saved);\n io->wait_us(io->ctx,2);\n if(!nes_cf86_check094())goto fail;\n io->select(io->ctx,false);')
    s=replace(s,' GPIOB->BSRR=', ' nes182_restore(&saved);\n GPIOB->BSRR=')
    s=s.replace('No DMA, no queued second byte, no retry of a possibly committed command.',
                'RUN-only DMA; no queued packet or retry of a possibly committed command.')
    s=s.replace('Hardware clocks one byte autonomously; CF86 is checked on every status poll.',
                'Hardware clocks the bounded packet; CF86 is checked on every DMA/status poll.')
    return s


def prepare(prior,out):
    assert sha(prior/'src/obj-nes-100/firmware.stm')=='cf16e9c124a20ab0e25e9f0d0646d8dfd33f706300b8df600318e3020bcc5d1c'
    prep=json.loads((prior/'preparation-paired181.json').read_bytes())
    pins=prep['copied']|prep['changed']|prep['added'];copy_pins(prior,out,pins)
    changed={};added={}
    def write(n,s,table):
        (out/n).write_text(s,encoding='utf8',newline='\n');table[n]=sha(out/n)
    write('src/nes_native165_bulk.inc',bulk((prior/'src/nes_native165_bulk.inc').read_text()),changed)
    write('src/nes_dma182.inc',(ROOT/'src/nes/firmware/nes_dma182.inc').read_text(),added)
    for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
        s=(out/n).read_text()
        for a,b in [('NES-GAME-181','NES-GAME-182'),('GAME 181','GAME 182'),('game181.nes','game182.nes'),
                    ('fpga_n181.bi3','fpga_n182.bi3'),('last-181.txt','last-182.txt'),('NES181 seq=','NES182 seq='),
                    ('nes-progress-181.txt','nes-progress-182.txt'),('NES-GAME181-DEV','NES-GAME182-DEV')]:s=s.replace(a,b)
        write(n,s,changed)
    r=dict(copied=pins,changed=changed,added=added,baseline_firmware=sha(prior/'src/obj-nes-100/firmware.stm'),
           ingress_version='1813',sink_version='1815',fpga_unchanged=True,hardware_package=False,
           public_sources={n:sha(ROOT/n) for n in ['tools/nes_dma182.py','src/nes/firmware/nes_dma182.inc']})
    for n in ['preparation-dma182.json','preparation-runlease165.json']:
        (out/n).write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=prepare(a.prior,a.out);print(json.dumps(dict(changed=r['changed'],added=r['added'])))
