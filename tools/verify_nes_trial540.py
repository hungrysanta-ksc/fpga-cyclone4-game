# SPDX-License-Identifier: MIT
"""Bind the selected 539 schedule to the MMC540 labels, recovery checks and complete Lite board."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import zlib

from verify_nes_trial533 import ROOT, read, sha, timing, fpga, funcs


def verify(a):
    measured=read(ROOT/'analysis/first539-verification.json')
    assert measured['gate']['row']
    prior=read(ROOT/'analysis/trial533-verification.json')
    assert sha(a.reference/'output_files/board.sof')==prior['SOF_SHA256']
    pins=read(a.board/'inputs535.json')
    assert len(pins)==73 and all(sha(a.board/n)==h for n,h in pins.items())
    assert [n for n in pins if pins[n]!=prior['inputs'][n]]==['sink-program.hex']
    assert sha(a.client/'sink-program.hex')==pins['sink-program.hex']
    assert sha(a.client/'sink165.sfc')==measured['client']
    rom=(a.client/'sink165.sfc').read_bytes()
    assert bytes.fromhex((a.board/'sink-program.hex').read_text())==rom[:5056]+rom[-64:]
    assert 'Lite Edition' in (a.board/'flow.log').read_text(errors='replace')
    assert 'successful' in (a.board/'sta.log').read_text(errors='replace').lower()
    fitted=fpga(a.board)
    fields=('LE','comb','FF','RAM_bits','M9K','implementation_setup_ns','implementation_hold_ns','nominal_setup_ns','nominal_hold_ns')
    cost={key:fitted[key] for key in fields}
    assert all(cost[key]>=0 for key in fields[5:])
    summary,worst,unconstrained=timing(a.board)
    baseline,_,baseline_ucp=timing(a.reference)
    assert summary==baseline and unconstrained==baseline_ucp
    for view in ('implementation','nominal'):
        assert Counter((a.board/f'{view}-paths204.tsv').read_text().splitlines())==Counter((a.reference/f'{view}-paths204.tsv').read_text().splitlines())
    original=a.selected/'obj-nes-100'
    obj=a.arm/'obj-nes-100'
    digest=sha(obj/'firmware.stm')
    assert sha(original/'firmware.stm')==measured['phases'][0]['row']['ARM_SHA256']
    functions=funcs(obj/'sd2snes.elf')
    assert functions==funcs(original/'sd2snes.elf')
    image=(obj/'firmware.stm').read_bytes()
    source=(original/'firmware.stm').read_bytes()
    assert image[32:]==source[32:].replace(b'533',b'540')
    size,crc,inverse=struct.unpack_from('<III',image,8)
    assert image[:4]==b'STM3' and len(image)==size+512<=0x34000 and crc==zlib.crc32(image[512:]) and crc^inverse==0xffffffff
    window=read(a.checks/'windows.json')
    assert window['firmware_SHA256']==digest and [x['displays'] for x in window['accepted']]==[2,2]
    assert window['reset'] and window['unfinished_excluded']
    credit=read(a.checks/'credit.json')
    assert credit['sha']==digest and credit['rows']==read(ROOT/'analysis/tile532-verification.json')['credit']['rows']
    menu=read(a.checks/'menu.json')
    assert menu['firmware']==digest and all(x['released']==int(name=='normal') for name,x in menu['rows'].items())
    recover={}
    for name in ('none','program','done','busy','token'):
        r=read(a.checks/f'base-{name}/result.json')
        assert r['passed'] and r['firmware_sha256']==digest and r['safe_return']==r['base_restored']==int(name=='none')
        assert r['config_paths']==['/sd2snes/fpga_mmc540.bi3','/sd2snes/fpga_base.bi3']
        recover[name]=r['safe_return']
    return dict(candidate='MMC540',physical_verified=False,timing_criterion='matched-mmc529',selected='row',
                firmware_SHA256=digest,identical_functions=len(functions),Flash_B=len(image),free_Flash_B=0x34000-len(image),
                BSS_B=window['BSS_B'],SOF_SHA256=sha(a.board/'output_files/board.sof'),board=cost,
                inputs=pins,raw_worst_ns=worst,unconstrained=unconstrained,raw_summary_rows=len(summary),
                reports=fitted['report_SHA256'],base_return=recover,menu=menu,windows=window,credit=credit,
                timing_evidence_SHA256=sha(ROOT/'analysis/first539-verification.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('board','reference','client','arm','selected','checks','out'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(verify(a),indent=2)+'\n',newline='\n')
