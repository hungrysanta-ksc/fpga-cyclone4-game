"""Verify the exact installed ARM, routed ROM and display schedule before archiving."""
import argparse
import re
import struct
import zlib
from pathlib import Path

from analyze_nes_obj923 import recovery
from analyze_nes_window924 import accepted_dma, coverage, directory, sample
from package_nes_trial704 import decode, digest, read, sha
from package_nes_trial872 import write_verified_archive
from prepare_nes_trial925 import ORIGINAL, PROBES, ROOT, WORK, client
from test_nes_raw506_joint import MASTER


def timing(temp, firmware, consumer):
    previous = read(ROOT/'analysis/window924-results.json')['cases']
    rows = {}
    for phase in (1,2):
        for cache in ('warm','cold'):
            key = f'{phase}-{cache}'
            folder = directory(temp,phase,'925final',cache)
            joint = read(folder/'joint.json')
            assert (joint['firmware_SHA256'],joint['client_SHA256'])==(firmware,consumer)
            row, content = sample(folder,WORK)
            prior, reference = sample(directory(temp,phase,'924objheader',cache),ORIGINAL)
            assert content == reference
            assert row == prior, (key,'final link changed the measured schedule')
            early = accepted_dma(folder,row['pre909'])
            base = previous['915'][key]
            edge = previous['923'][key]['commit_D2'] - previous['923'][key]['capture_offset']
            margin = edge-row['commit_D2']
            gain = base['ack912']-row['ack912']
            assert gain>0
            if cache=='warm':
                assert margin>0 and row['intervals']==13 and row['display908']==base['display908']-1
                assert any(d['address']>=0x4000 and d['VBlank']==d['shown']-1 for d in early)
            else:
                assert row['intervals']==16
                assert coverage(row['pre912']).keys()==coverage(base['pre912']).keys() and len(coverage(row['pre912']))==496
            rows[key]=dict(intervals=row['intervals'],gaps=row['gaps'],reveal908=row['display908'],
                           capture910_margin_clocks=margin if cache=='warm' else None,
                           pre912_B=len(coverage(row['pre912'])),final_ACK=row['ack912'],
                           MMC915_final_ACK=base['ack912'],gain_ms=round(gain*1000/MASTER,6),joint=sha(folder/'joint.json'))
    return rows


def package(temp):
    parent = read(ROOT/'analysis/trial915-package.json')
    cpu = client('first')/'sink165.sfc'
    consumer = sha(cpu)
    fw = (WORK/'link/src/obj-nes-100/firmware.stm').read_bytes()
    n,crc,inv = struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and n+512==len(fw)<=212992 and crc^inv==0xffffffff and crc==zlib.crc32(fw[512:])
    for path in ('NES MMC3 925.nh1','fpga_mmc925.bi3','mmc925.nes','nes-game-last-mmc925.txt',
                 'nes-budget-mmc925.txt','nes-progress-mmc925.txt','nes-frame-mmc925.bin'):
        assert path.encode()+b'\0' in fw and path.replace('925','915').encode()+b'\0' not in fw
    proof = recovery('final',WORK,trial=WORK)
    assert proof['firmware']==digest(fw) and proof['consumer']==consumer
    base = read(WORK/'proof/base/result.json')
    assert base['config_paths']==['/sd2snes/fpga_mmc925.bi3','/sd2snes/fpga_base.bi3'] and base['base_restored']
    windows = read(WORK/'proof/windows.json')
    assert windows['firmware_SHA256']==digest(fw) and windows['unfinished_excluded']
    assert [(w['start_s'],w['end_s']) for w in windows['accepted']]==[(1,30),(30,60)]
    out = temp/'nes-board925'
    board = out/'board925'
    route = read(out/'routing925.json')
    image = read(out/'packed925/image.json')
    bus = read(out/'bus/result.json')
    packed = (out/'packed925/fpga_mmc925.bi3').read_bytes()
    program = bytes.fromhex((board/'sink-program.hex').read_text())
    rom = cpu.read_bytes()
    assert program==rom[:5056]+rom[-64:] and len(program)==bus['bytes']==5120
    mif, = (board/'db').glob('board.ram*_nes_sink_bus165_*.hdl.mif')
    cells = sorted((int(i),int(v,2)) for i,v in re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',mif.read_text(),re.M))
    assert [i for i,_ in cells]==list(range(5120)) and bytes(v for _,v in cells)==program
    assert sha(mif)==route['MIF'] and sha(board/'sink-program.hex')==bus['program']
    assert bus['client']==consumer==route['ROM'] and sha(board/'nes_sink_bus165.sv')==bus['bus']
    assert route['base_SOF']==parent['board']['image']['SOF'] and route['FIT']==parent['board']['fit']['fit_sha256']
    assert sha(board/'output_files/board.sof')==image['SOF']!=route['base_SOF']
    assert image['programmer']['passed'] and digest(packed)==image['BI3']==image['programmer']['image_sha256']
    assert digest(decode(packed))==image['RBF']==image['programmer']['rbf_sha256']!=parent['board']['image']['RBF']
    report=dict(edition=925,firmware=digest(fw),Flash_B=len(fw),free_B=212992-len(fw),client=consumer,
                route=route,image=image,bus=bus,proof=proof,windows=windows,
                cases=timing(temp,digest(fw),consumer),physical=False)
    write_verified_archive(WORK,parent,fw,packed,report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    package(p.parse_args().temp)
