"""Build and re-read the two SD roots from qualified images and final links."""
import argparse
import csv
import json
import re
import struct
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from analyze_nes_output822 import resources
from package_nes_trial704 import decode, digest, read, save, sha
from prepare_nes_frame862 import PARENTS, PROBES, ROOT, WORK
from read_nes_frame862 import decode as read_trace


def board(temp, n, client):
    project = temp / f'nes-trial816-board{n}'
    reports = project / 'output_files'
    packed = temp / f'nes-frame862-final{n}'
    image = read(packed / 'image.json')
    data = (packed / f'fpga_mmc{n}.bi3').read_bytes()
    assert sha(reports / 'board.sof') == image['SOF']
    assert image['BI3'] == digest(data) == image['programmer']['image_sha256']
    assert digest(decode(data)) == image['RBF'] == image['programmer']['rbf_sha256']
    assert image['programmer']['passed'] and image['number'] == str(n)
    fit = resources(temp, str(n))
    assert 'Fitter Status : Successful' in (reports / 'board.fit.summary').read_text()
    assert len(fit['min_slack_ns']) == 5 and min(fit['min_slack_ns'].values()) >= 0
    targets = {}
    for name in ('io612', 'paths612', 'paths801', 'phase801', 'reader661', 'word660'):
        lines = (project / f'{name}.tsv').read_text().splitlines()
        values = [float(line.split('\t')[3 if name == 'phase801' else 2])
                  for line in (lines if name == 'phase801' else lines[1:])]
        assert min(values) >= 0
        targets[name] = min(values)
    mif, = (project / 'db').glob('board.ram*_nes_sink_bus165_*.hdl.mif')
    cells = sorted((int(i), int(v, 2)) for i,v in re.findall(
        r'^\s*(\d+)\s*:\s*([01]{8});', mif.read_text(), re.M))
    assert [i for i,_ in cells] == list(range(5120))
    assert bytes(v for _,v in cells) == bytes.fromhex((client/'sink-program.hex').read_text())
    sta = (reports/'board.sta.rpt').read_text(errors='replace')
    unconstrained = re.findall(r'^; (Unconstrained [\w ]+?)\s*;\s*(\d+)\s*;\s*(\d+)\s*;', sta, re.M)
    return data, dict(fit=fit, target_minimum_ns=targets, image=image, unconstrained=unconstrained)


def replay(directory):
    with (directory/'window.csv').open() as f:
        frames = {int(r['g']): (int(r['frame']), int(r['clock'])) for r in csv.DictReader(f)
                  if r['event']=='ack' and r['op']=='3'}
    return dict(intervals=frames[915][0]-frames[906][0], final_ACK=frames[915][1])


def package(temp):
    files = {'README-KO.txt': (ROOT/'docs/nes-mmc862-863-trial.ko.md').read_bytes()}
    result = {}
    for n,parent in PARENTS.items():
        original = read(ROOT/f'analysis/trial{parent}-package.json')
        src = WORK/f'delivery/build{n}/src'
        proof = WORK/f'delivery/proof{n}'
        fw = (src/'obj-nes-100/firmware.stm').read_bytes()
        size,crc,inverse = struct.unpack_from('<III',fw,8)
        assert fw[:4]==b'STM3' and size+512==len(fw)<=212992
        assert crc==zlib.crc32(fw[512:]) and crc^inverse==0xffffffff
        for label in [f'NES {kind} {n}.nh1' for kind in ('MMC3','CONTROL')]+[
            f'nes-frame-{kind}{n}.bin' for kind in ('mmc','ctl')]+[
            f'nes-{kind}-mmc{n}.txt' for kind in ('progress','budget','game-last')]:
            assert label.encode()+bytes(1) in fw
        client = PROBES/('nes-column854/client-e' if n==862 else 'nes-seal858/client-e')
        assert sha(client/'sink165.sfc')==original['client']
        bi,board_checks = board(temp,n,client)
        assert read(proof/'timer.json')['passed'] and read(proof/'timer.json')['firmware']==digest(fw)
        assert read(proof/'wire-arm.json')['identity_fault_rejected']
        checks = {f:sha(proof/f) for f in ('menu.json','windows.json','wire-arm.json','timer.json',
                                             'base/result.json','loader.json','sample.bin','sample-control.bin')}
        runs = {}
        for phase in (1,2):
            prefix = f'nes-tile821-demo-jointmirror-p{phase}-'
            runs[phase] = {'parent':replay(temp/(prefix+f'861-{parent}-128-high'))}
            for mode,suffix in [('on',''),('off','-control')]:
                directory = temp/(prefix+f'frame{n}-delivery'+suffix)
                verified = read(directory/'checked.json')
                assert verified['verified_RGB']==11 and verified['firmware']==digest(fw)
                trace = read_trace(directory/'records.bin')
                assert trace['control']==(mode=='off') and len(trace['rows'])==9 and not trace['dropped']
                runs[phase][mode] = dict(**replay(directory), mean_SPI_read_ms=sum(
                    r['probe_ms'] for r in trace['rows'])/len(trace['rows']))
        z = PROBES/f'nes-trial{parent}/MMC{parent}-ADVENTURE-60SEC-SD-ROOT.zip'
        assert sha(z)==original['ZIP_SHA256']
        with ZipFile(z) as prior:
            for name in prior.namelist():
                if '/' not in name:continue
                data=prior.read(name)
                assert digest(data)==original['files'][name]
                target=name.replace(str(parent),str(n))
                if name.endswith('/firmware.stm'):data=fw
                elif name.endswith(f'/fpga_mmc{parent}.bi3'):data=bi
                elif name.endswith('ROM-NOT-INCLUDED.txt'):data=data.replace(str(parent).encode(),str(n).encode())
                files[target]=data
                if name.endswith(f'/NES MMC3 {parent}.nh1'):
                    files[target.replace('NES MMC3','NES CONTROL')]=data
        result[n]=dict(parent=parent,ARM=digest(fw),flash_B=len(fw),client=original['client'],
                       **board_checks,checks=checks,phase_replay=runs)
    assert 'PASS862 wire' in (temp/'nes-frame862-wire/wire.log').read_text()
    path=WORK/'MMC862-MMC863-ADVENTURE-DMA-60SEC.zip'
    hashes={name:digest(data) for name,data in files.items()}
    files['manifest.json']=json.dumps(hashes,indent=2).encode()
    with ZipFile(path,'w',ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):
            archive.writestr(ZipInfo(name),data,compress_type=ZIP_DEFLATED)
    with ZipFile(path) as archive:
        assert len(files)==len(archive.namelist()) and archive.testzip() is None
        assert all(archive.read(name)==data for name,data in files.items())
    save(ROOT/'analysis/frame862-package.json',dict(physical=False,editions=result,
         wire_log_sha256=sha(temp/'nes-frame862-wire/wire.log'),ZIP_SHA256=sha(path),members=hashes))
    print(path,sha(path))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('temp',type=Path)
    package(parser.parse_args().temp)
