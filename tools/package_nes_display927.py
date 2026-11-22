"""Verify the routed observer, final ARM and replay evidence before creating the SD archive."""
import argparse
import csv
import re
import struct
import zlib
from pathlib import Path

from arm_nes_display927 import WORK
from package_nes_trial704 import decode, digest, read, sha
from package_nes_trial872 import ROOT, write_verified_archive
from read_nes_display927 import decode as capture


def routed(temp,parent):
    build=temp/'nes927-verified'
    board=build/'nes-trial816-board927'
    out=board/'output_files'
    image=read(build/'nes-image927/image.json')
    packed=(build/'nes-image927/fpga_mmc927.bi3').read_bytes()
    assert sha(out/'board.sof')==image['SOF'] and image['programmer']['passed']
    assert digest(packed)==image['BI3']==image['programmer']['image_sha256']
    assert digest(decode(packed))==image['RBF']==image['programmer']['rbf_sha256']
    observer=sha(board/'nes_display927.sv')
    assert observer==sha(ROOT/'tests/nes-functional/nes_display927.sv')
    assert 'PASS927 wire' in (temp/'nes-display927-wire/wire.log').read_text()
    for name in ('nes_display927.sv','nes_screen_status151.sv','nes_sink_bus165.sv'):
        assert sha(temp/'nes-display927-wire'/name)==sha(board/name)
    mif,=(board/'db').glob('board.ram*_nes_sink_bus165_*.hdl.mif')
    cells=sorted((int(i),int(v,2)) for i,v in re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',mif.read_text(),re.M))
    assert [i for i,v in cells]==list(range(5120))
    assert bytes(v for i,v in cells)==bytes.fromhex((board/'sink-program.hex').read_text())
    assert sha(board/'sink-program.hex')==parent['bus']['program']
    assert 'Fitter Status : Successful' in (out/'board.fit.summary').read_text()
    fit=(out/'board.fit.rpt').read_text(errors='replace')
    def usage(pattern):
        m=re.search(pattern+r'\s*;\s*([0-9,]+) / ([0-9,]+)',fit)
        return [int(v.replace(',','')) for v in m.groups()]
    types=re.findall(r'^Type\s*:[^\n]+? (Setup|Hold|Recovery|Removal|Minimum Pulse Width) [^\n]*\nSlack\s*:\s*([-\d.]+)',(out/'board.sta.summary').read_text(),re.M)
    minima={k:min(float(v) for t,v in types if t==k) for k in ('Setup','Hold','Recovery','Removal','Minimum Pulse Width')}
    io=list(csv.DictReader((board/'io612.tsv').read_text().splitlines(),delimiter='\t'))
    minima['ROM_OE']=min(float(r['slack']) for r in io if r['port']=='ROM_OE')
    assert min(minima.values())>=0 and all(float(r['slack'])>=0 for r in io)
    return packed,dict(image=image,observer=observer,ROM_program=parent['bus']['program'],
                       LE=usage('Total logic elements'),LAB=usage('Total LABs:  partially or completely used'),
                       M9K=usage('M9Ks'),min_ns=minima,FIT=sha(out/'board.fit.rpt'),STA=sha(out/'board.sta.rpt'))


def package(temp):
    parent=read(ROOT/'analysis/trial925-package.json')
    fw=(WORK/'link/src/obj-nes-100/firmware.stm').read_bytes()
    n,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==n+512<=212992 and crc^inv==0xffffffff and crc==zlib.crc32(fw[512:])
    for name in ('NES MMC3 927.nh1','mmc927.nes','fpga_mmc927.bi3','nes-budget-mmc927.txt',
                 'nes-frame-mmc927.bin','nes-progress-mmc927.txt','nes-game-last-mmc927.txt'):
        assert name.encode()+b'\0' in fw
    proof=WORK/'proof'
    firmware=digest(fw)
    base_file=proof/'base-final/result.json'
    if not base_file.exists():
        base_file=proof/'base/result.json'
    base=read(base_file)
    assert base['firmware_sha256']==firmware and base['passed'] and base['base_restored'] and base['safe_return']
    assert base['config_paths']==['/sd2snes/fpga_mmc927.bi3','/sd2snes/fpga_base.bi3']
    windows=read(proof/'windows.json')
    assert windows['firmware_SHA256']==firmware and windows['unfinished_excluded']
    checks={k:read(proof/(k+'.json')) for k in ('loader','timer','menu')}
    assert all(r['firmware']==firmware for r in checks.values())
    assert checks['timer']['passed'] and checks['menu']['rows']['normal']['released']
    assert checks['loader']['cases']['original']['program'] and not checks['loader']['cases']['damaged']['program']
    cases=read(proof/'sram.json')['cases']
    assert len(cases['normal']['d0_sites'])==4 and cases['normal']['checked_retire']
    packed,board=routed(temp,parent)
    runs={}
    for phase in (1,2):
        for cache in ('warm','cold'):
            key=f'{phase}-{cache}'
            folder=temp/f'nes-tile821-obj-jointmirror-p{phase}-927final-{cache}-pair'
            joint=read(folder/'joint.json')
            assert joint['passed'] and joint['firmware_SHA256']==firmware and joint['client_SHA256']==parent['client']
            result=read(folder/'verified905.json')
            rows=capture(folder/'records.bin')['rows']
            assert len(rows)==6 and result['RGB']==8 and all('invalid' not in r for r in rows)
            runs[key]=dict(intervals=result['intervals'][-1],MMC925_intervals=parent['cases'][key]['intervals'],
                           last_ACK=result['final_ACK'][-1],MMC925_ACK=parent['cases'][key]['final_ACK'],
                           RGB=result['RGB'],records=len(rows),joint=sha(folder/'joint.json'))
    report=dict(edition=927,physical=False,firmware=firmware,Flash_B=len(fw),free_B=212992-len(fw),
                client=parent['client'],board=board,cases=runs,inputs=list(cases),
                normal_D0=cases['normal']['d0_sites'],stack_gap_B=cases['normal']['static_gap_bytes'],
                checks={k:sha(proof/(k+'.json')) for k in ('timer','loader','menu','windows','sram')},
                base=sha(base_file),scope='Diagnostic build. Joint replay uses a recorded RTL reply for ABI and independent Mesen PPU events for display timing.')
    write_verified_archive(WORK,parent,fw,packed,report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    package(p.parse_args().temp)
