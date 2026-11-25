"""Qualify and package the 871 warm_dual firmware with its matching SNES client."""
import argparse
import json
from pathlib import Path
import shutil
import struct
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import zlib

from package_nes_trial704 import digest, image, read, save, sha
from package_nes_trial855 import board_proof, loader
from analyze_nes_map830 import window
from prepare_nes_trial802 import PROBES, rename_edition
from prepare_nes_trial816 import fit


ROOT = Path(__file__).resolve().parents[1]
WORK = PROBES / 'nes-trial872'
PARENT = PROBES / 'nes-capture871-warm_dual'
SRC = WORK / 'link-credit/src'
CLIENT = WORK / 'client02'
QUARTUS = Path('C:/altera_lite/25.1std/quartus/bin64')


def board(temp):
    parent = read(ROOT / 'analysis/trial866-package.json')
    dest = compile_board(temp, '855', '872', CLIENT, parent['board']['image']['SOF'],
                         read(ROOT/'analysis/capture871-results.json')['detail']['client'])
    image(SimpleNamespace(board=dest, out=temp/'nes-trial872-packed', quartus=QUARTUS, number='872'))


def compile_board(temp, base_edition, edition, client, expected_sof, expected_client):
    base = temp / f'nes-trial816-board{base_edition}'
    assert sha(base/'output_files/board.sof') == expected_sof
    rom = (client/'sink165.sfc').read_bytes()
    assert digest(rom) == expected_client
    assert bytes.fromhex((client/'sink-program.hex').read_text()) == rom[:5056] + rom[-64:]
    dest = temp / f'nes-trial816-board{edition}'
    dest.mkdir()
    for sub in ('rtl', 'sys'):
        shutil.copytree(base/sub, dest/sub)
    for f in base.iterdir():
        if f.suffix in ('.sv','.v','.vhd','.qpf','.qsf','.sdc','.tcl','.hex'):
            shutil.copyfile(client/f.name if f.name == 'sink-program.hex' else f, dest/f.name)
    fit(temp, edition, QUARTUS)
    return dest



def verify_link():
    fw = (SRC/'obj-nes-100/firmware.stm').read_bytes()
    old = (PARENT/'link-credit/src/obj-nes-100/firmware.stm').read_bytes()
    parent = read(ROOT/'analysis/capture871-results.json')['detail']
    assert parent['meets_request'] and digest(old) == parent['ARM']
    assert fw[32:] == old[32:].replace(b'866', b'872')
    size, crc, inverse = struct.unpack_from('<III', fw, 8)
    assert fw[:4] == b'STM3' and len(fw) == size + 512 <= 212992
    assert crc == zlib.crc32(fw[512:]) and crc ^ inverse == 0xffffffff
    for name in ('NES MMC3 872.nh1','mmc872.nes','fpga_mmc872.bi3','nes-budget-mmc872.txt',
                 'nes-progress-mmc872.txt','nes-game-last-mmc872.txt'):
        assert name.encode() + b'\0' in fw, name
    return fw, parent


def qualification(temp, firmware, parent):
    current = read(WORK/'summary.json')
    assert current['ARM'] == firmware and current['client'] == parent['client']
    assert current['meets_request']
    clips = {}
    for scene in ('opening','transition','demo'):
        for phase in (1,2):
            key = f'{scene}-{phase}'
            result = current['scenes'][key]
            actual = result['candidate']
            assert actual == parent['scenes'][key]['candidate'], key
            root = f'nes-tile821-{scene}-jointmirror-p{phase}-'
            folder = temp/(root+'872-final')
            joint = read(folder/'joint.json')
            assert joint['passed'] and joint['last_status'] == 1
            shows = [e for e in window(folder) if e['event']=='reveal']
            previous = [e for e in window(temp/(root+'871-warm_dual')) if e['event']=='reveal']
            assert shows == previous and len(shows) == actual['pictures'], key
            clips[key] = dict(pictures=len(shows), intervals=actual['after_two_VBlanks'],
                              last_ACK=actual['last_ACK'], ACK_delta_clocks=result['ACK_delta_clocks'],
                              opening_marks=actual['opening_marks'])
            if scene == 'transition':
                assert actual['after_two_VBlanks'] == 119
            if scene == 'demo':
                g = current['generation936'][str(phase)]['872-final']
                assert g['gap'] == 2 and actual['after_two_VBlanks'] == 141 and result['ACK_delta_clocks'] < 0
                clips[key]['generation936'] = g['gap']
    checks = {k:read(WORK/(k+'.json')) for k in ('timer','windows','loader','menu869','input-guards','guards')}
    assert checks['windows']['firmware_SHA256'] == firmware
    assert checks['windows']['unfinished_excluded'] and [(r['start_s'],r['end_s']) for r in
            checks['windows']['accepted']] == [(1,30),(30,60)]
    assert all(checks[k]['firmware']==firmware for k in ('timer','loader','menu869','input-guards'))
    assert checks['timer']['passed'] and checks['menu869']['rows']['normal']['released']
    assert checks['input-guards']['cases'] == parent['input_guards']['cases']
    assert checks['guards']['cases'] == parent['consumer_guards']['cases']
    assert checks['guards']['two_column_cancel'] == parent['consumer_guards']['two_column_cancel']
    base = read(WORK/'base/result.json')
    assert base['firmware_sha256']==firmware and base['passed'] and base['base_restored'] and base['safe_return']
    assert base['config_paths']==['/sd2snes/fpga_mmc872.bi3','/sd2snes/fpga_base.bi3']
    boot = read(temp/'nes-trial872-boot/result.json')
    assert boot['passed'] and sorted((r['fault'], r['kind']) for r in boot['cases']
        if r['ROM']==current['client']) == [(False,'restored'),(True,'rejected')]
    checks.update(base=base, boot=boot, begin=current['begin_guards'], strip_E0=current['strip_E0_guards'])
    return clips, checks


def package(temp):
    fw, parent = verify_link()
    clips, checks = qualification(temp, digest(fw), parent)
    proof, bitstream = board_proof(temp, read(ROOT/'analysis/trial826-package.json'), '872', CLIENT, '855')
    rom = (CLIENT/'sink165.sfc').read_bytes()
    assert digest(rom) == parent['client'] and digest(rom[:5056]+rom[-64:]) == proof['ROM_bus']
    reference = read(ROOT/'analysis/trial866-package.json')
    assert checks['loader']['cases']==reference['checks']['loader']['cases']
    assert checks['loader']['rom']==reference['checks']['loader']['rom']
    report = dict(edition=872, physical=False, ARM=digest(fw), client=parent['client'], flash_B=len(fw),
                  flash_free_B=212992-len(fw), board=proof, final_link_runs=clips, checks=checks)
    write_verified_archive(WORK,reference,fw,bitstream,report)


def write_verified_archive(work,reference,fw,bitstream,report,*,source=None,game_label='ADVENTURE'):
    edition = report['edition']
    prior = reference['edition']
    if source is None:
        source = PROBES/f'nes-trial{prior}/MMC{prior}-ADVENTURE-60SEC-SD-ROOT.zip'
    assert sha(source)==reference['ZIP_SHA256']
    files = {}
    with ZipFile(source) as original:
        for name, checksum in reference['files'].items():
            data = original.read(name)
            assert digest(data)==checksum
            if name=='README-KO.txt':
                data = (ROOT/f'docs/nes-mmc{edition}-trial.ko.md').read_bytes()
            elif name.endswith('/firmware.stm'):
                data = fw
            elif name.endswith(f'/fpga_mmc{prior}.bi3'):
                data = bitstream
            elif name.endswith('/ROM-NOT-INCLUDED.txt'):
                assert f'mmc{prior}.nes'.encode() in data
                data = data.replace(f'mmc{prior}.nes'.encode(),f'mmc{edition}.nes'.encode())
            files[name.replace(str(prior),str(edition))] = data
    assert len(files)==len(reference['files']) and all('restore' not in n.lower() and not n.lower().endswith('.nes') for n in files)
    report.update(reference_ZIP=sha(source),files={n:digest(data) for n,data in files.items()})
    files['manifest.json'] = (json.dumps(report,indent=2)+'\n').encode()
    archive = work/f'MMC{edition}-{game_label}-60SEC-SD-ROOT.zip'
    partial = archive.with_suffix('.partial')
    with ZipFile(partial,'w') as z:
        for name,data in files.items():
            z.writestr(ZipInfo(name), data, compress_type=ZIP_DEFLATED)
    with ZipFile(partial) as z:
        assert z.testzip() is None and z.namelist()==list(files) and all(z.read(n)==b for n,b in files.items())
    partial.replace(archive)
    report.update(ZIP_SHA256=sha(archive), ZIP_B=archive.stat().st_size)
    save(ROOT/f'analysis/trial{edition}-package.json',report)
    print(archive, report['ZIP_SHA256'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare','board','loader','pack'))
    p.add_argument('path', type=Path, nargs='?', help='ROM for loader, temporary board and replay root for board/pack')
    a = p.parse_args()
    if a.action != 'prepare' and a.path is None:
        p.error(f'{a.action} requires a path')
    if a.action == 'prepare':
        rename_edition(PARENT/'link-credit/src', WORK/'patch', 866, 872)
        shutil.copytree(PARENT/'client02', CLIENT)
    elif a.action == 'board':
        board(a.path)
    elif a.action == 'loader':
        loader(a.path, SRC, 872, WORK)
    else:
        package(a.path)
