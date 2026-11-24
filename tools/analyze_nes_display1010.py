"""Collect measured routing and linked firmware evidence for the alternative observer."""
import argparse
import csv
import hashlib
import json
import struct
import zlib
from pathlib import Path

from analyze_nes_chr951 import board_cost
from prepare_nes_display1010_arm import PROBE
from nes_display1010 import ROOT

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def summarize(temp):
    board=temp/'nes-display1010-boardD'
    baseline=json.loads((ROOT/'analysis/trial966-package.json').read_bytes())
    proof=PROBE.parent/'proof'
    arm=PROBE/'src/obj-nes-100/firmware.stm'
    firmware=arm.read_bytes()
    size,crc,inverse=struct.unpack_from('<III',firmware,8)
    assert firmware[:4]==b'STM3' and size+512==len(firmware)<=212992
    assert crc^inverse==0xffffffff and crc==zlib.crc32(firmware[512:])
    for name in (' 1010.nh1','mmc1010.nes','fpga_mmc1010.bi3','nes-progress-mmc1010.txt',
                 'nes-budget-mmc1010.txt','nes-game-last-mmc1010.txt','nes-frame-mmc1010.bin'):
        assert name.encode()+b'\0' in firmware and name.replace('1010','966').encode()+b'\0' not in firmware
    windows=json.loads((proof/'windows.json').read_bytes())
    assert windows['firmware_SHA256']==sha(arm) and windows['Flash_free_B']==212992-len(firmware)
    arm_log=(PROBE.parent/'arm-final.log').read_text(encoding='utf-8-sig')
    if 'PASS1010 ARM timer, menu, SRAM, loader CRC, STOP and base' not in arm_log:
        raise ValueError('ARM validation incomplete')
    wire=(temp/'nes-display1010-wire/wire1010.log').read_text()
    for message in ['PASS1010 phase 1 seven','PASS1010 phase 2 seven','PASS1010 cold']:
        assert message in wire
    for name in ('nes_display1010.sv','sink-program.hex'):
        src=ROOT/'tests/nes-functional'/name if name.endswith('.sv') else temp/'nes-trial816-board964'/name
        assert sha(src)==sha(board/name)
    stages=json.loads((ROOT/'analysis/demo-loss1009-results.json').read_bytes())['replay978']
    ppu={}
    for phase in (1,2):
        run=temp/f'nes-display1010-ppu-p{phase}'
        assert sha(run/'client.sfc')==baseline['client']
        assert json.loads((run/'result.json').read_bytes())['passed']
        with (run/'window.csv').open() as f:
            rows=list(csv.DictReader(f))
        ppu[str(phase)]={}
        for g,r in stages[str(phase)].items():
            events=[x for x in rows if r['SEAL_header']<=int(x['clock'])<=r['final_ACK']]
            writes=[(int(x['clock']),int(x['value'])) for x in events if x['event']=='inidisp1010']
            dma=[x for x in events if x['event']=='port1010'][-1]
            assert writes==[(r['show'],15)] and int(dma['clock'])==r['last_dma']
            port=int(dma['value'])
            assert port>>8==0x7f and port&255 in (4,0x18,0x19,0x22)
            ppu[str(phase)][g]=dict(last_WRAM_bank=port>>8,last_PPU_port=hex(0x2100+(port&255)),
                                 reveal=writes[0][0],last_DMA=r['last_dma'],ACK=r['final_ACK'])
    route=board_cost(board)
    return dict(reference='MMC966',physical_trial=False,reference_route=baseline['route'],
         earlier_routes={s or 'A':board_cost(temp/('nes-display1010-board'+s)) for s in ('','B','C') if (temp/('nes-display1010-board'+s)/'output_files/board.sta.summary').is_file()},
         final_route=route,positive_STA=min(route['slack_ns'].values())>0,
         ARM=dict(firmware=sha(arm),flash_B=arm.stat().st_size,free_B=212992-arm.stat().st_size,
                  trace_B=(proof/'mode0.bin').stat().st_size,reference_trace_B=8044,
                  SPI_query_B=32,reference_header_B=16,guard_log=sha(PROBE.parent/'arm-final.log'),
                  guards=['timer','menu','SRAM D0','loader CRC','base','identity','partial','capacity','file modes']),
         wire_log=sha(temp/'nes-display1010-wire/wire1010.log'),rtl=sha(board/'nes_display1010.sv'),
         ROM=baseline['client'],ppu=ppu)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('temp',type=Path)
    args=parser.parse_args()
    (ROOT/'analysis/display1010-results.json').write_text(json.dumps(summarize(args.temp),indent=2)+'\n')
