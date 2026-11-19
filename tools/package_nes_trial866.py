"""Build and verify the 865 offer sender with the physical MMC855 board and client."""
import argparse
import json
import struct
import zlib
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import check_nes_seal858
from analyze_nes_ack861 import observe
from analyze_nes_map830 import packets, window
from analyze_nes_output852 import measure
from analyze_nes_raw864 import elapsed
from check_nes_opening865 import empty_offer
from check_nes_raw864 import guards
from package_nes_trial704 import digest, read, save, sha
from package_nes_trial855 import board_proof, loader, reset_policy
from prepare_nes_trial802 import PROBES, rename_edition
from prepare_nes_trial855 import CLIENT, ROOT
from replay_nes_ack861 import replay
from replay_nes_column853 import run


WORK = PROBES / 'nes-trial866'
OFFER = PROBES / 'nes-opening865/offer/src'
SRC = WORK / 'link/src'
FW = SRC / 'obj-nes-100/firmware.stm'
TAG = '866-on'


def run_scene(temp, scene, phase):
    if scene == 'dense':
        replay(temp, 855, phase, 128, high=True, arm_override=SRC, tag_override=TAG)
    else:
        run(temp, scene, phase, True, TAG, arm=SRC, client=CLIENT,
            budget=Path.home()/'Downloads/nes-budget-mmc855.txt')


def qualify(temp, firmware, client):
    evidence = read(ROOT/'analysis/opening865-results.json')
    selected = evidence['variants']['offer']
    assert selected['passed_replay_and_guards']
    result = {}
    for phase in (1, 2):
        key = str(phase)
        for scene in ('opening', 'transition', 'demo'):
            folder = temp/f'nes-tile821-{scene}-jointmirror-p{phase}-{TAG}'
            parent = folder.with_name(folder.name.replace('-866-on', '-865offer-on'))
            joint = read(folder/'joint.json')
            old = read(parent/'joint.json')
            assert joint['passed'] and joint['last_status']==1
            assert joint['firmware_SHA256']==firmware and old['firmware_SHA256']==selected['arm_SHA256']
            assert joint['client_SHA256']==old['client_SHA256']==client
            assert joint['parameters']==old['parameters'] and packets(folder)==packets(parent)
            shows = [r for r in window(folder) if r['event']=='reveal']
            assert shows==[r for r in window(parent) if r['event']=='reveal']
            name = f'{scene}-{phase}'
            if scene=='demo':
                baseline = observe(temp,855,phase,128,high=True)
                final = observe(temp,855,phase,128,high=True,arm_override=SRC,tag_override=TAG)
                offer = observe(temp,855,phase,128,high=True,arm_override=OFFER,tag_override='865offer-on')
                assert final==offer and len(final)==len(baseline)==60
                for a,b in zip(final,baseline,strict=True):
                    assert all(a[k]==b[k] for k in ('source','work','map','tile','SEAL_payload_B'))
                counts = [sum(r['gap'] for r in rows) for rows in (baseline,final)]
                acks = [rows[-1]['marks'][6] for rows in (baseline,final)]
                e0 = [rows[-1]['marks'][7] for rows in (baseline,final)]
                assert counts==selected['dense'][key]['intervals'] and counts[1]<counts[0]
                assert acks==selected['dense'][key]['ACK_clocks'] and acks[1]<acks[0] and e0[1]<e0[0]
                result[name] = dict(intervals=counts,ACK_clocks=acks,ACK_change_ms=elapsed(acks[1]-acks[0]),
                                    ARM_E0_change_ms=elapsed(e0[1]-e0[0]),matched_intervals=len(final))
                continue
            metrics,_,_ = measure(temp,scene,phase,'on','866',column=True)
            result[name] = {k:metrics[k] for k in ('verified_pictures','display_VBlanks','final_ACK','held_blank_VBlanks')}
            if scene=='opening':
                limits = evidence['opening_controls'][key]['857ref']['deadlines']
                deadlines = {str(r['g']-905+698):[r['frame'],r['line']] for r in shows if r['g'] in (910,966)}
                assert deadlines==selected['opening'][key]['deadlines']
                assert all(deadlines[i]<=limits[i] for i in ('703','759'))
                result[name]['deadlines'] = deadlines
                assert metrics['display_VBlanks']==selected['opening'][key]['intervals']
            else:
                assert all(metrics[k]==v[1] for k,v in selected['transition'][key].items())
    return result


def package(temp):
    parent = read(ROOT/'analysis/trial855-package.json')
    fw = FW.read_bytes()
    firmware = digest(fw)
    old = (OFFER/'obj-nes-100/firmware.stm').read_bytes()
    evidence = read(ROOT/'analysis/opening865-results.json')['variants']['offer']
    assert digest(old)==evidence['arm_SHA256'] and fw[32:]==old[32:].replace(b'855',b'866')
    size,crc,inverse = struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==size+512<=212992
    assert crc==zlib.crc32(fw[512:]) and crc^inverse==0xffffffff
    for name in ('NES MMC3 866.nh1','mmc866.nes','fpga_mmc866.bi3','nes-budget-mmc866.txt',
                 'nes-progress-mmc866.txt','nes-game-last-mmc866.txt'):
        assert name.encode()+b'\0' in fw

    board,image = board_proof(temp,read(ROOT/'analysis/trial826-package.json'))
    assert all(board[k]==parent['board'][k] for k in board)
    client = sha(CLIENT/'sink165.sfc')
    rom = (CLIENT/'sink165.sfc').read_bytes()
    assert client==parent['client'] and digest(rom[:5056]+rom[-64:])==board['ROM_bus']
    assert reset_policy(SRC)==parent['board']['default_column_policy']
    runs = qualify(temp,firmware,client)
    checks = {k:read(WORK/f'{k}.json') for k in ('timer','menu','loader','windows','receiver','empty-offer','866-stop','866-identity')}
    base = read(WORK/'base/result.json')
    assert checks['windows']['firmware_SHA256']==base['firmware_sha256']==firmware
    assert all(checks[k]['firmware']==firmware for k in ('loader','timer','menu'))
    assert base['safe_return'] and base['base_restored'] and base['passed']
    assert base['config_paths']==['/sd2snes/fpga_mmc866.bi3','/sd2snes/fpga_base.bi3']
    assert checks['menu']['rows']['normal']['released'] and checks['timer']['passed']
    assert checks['loader']['cases']==parent['checks']['loader']['cases']
    assert checks['loader']['rom']==parent['checks']['loader']['rom']
    assert checks['windows']['layout']=='demo' and checks['windows']['unfinished_excluded']
    assert [(r['start_s'],r['end_s']) for r in checks['windows']['accepted']]==[(1,30),(30,60)]
    assert checks['receiver']==evidence['tests']['receiver'] and checks['empty-offer']==evidence['tests']['empty_offer']
    assert checks['866-stop']['no_EA_or_D3'] and checks['866-identity']['committed_unchanged']
    boot = [r for r in read(temp/'nes-trial866-boot/result.json')['cases'] if r['ROM']==client]
    assert sorted((r['fault'],r['kind']) for r in boot)==[(False,'restored'),(True,'rejected')]
    checks['base'] = base

    original = PROBES/'nes-trial855/MMC855-ADVENTURE-60SEC-SD-ROOT.zip'
    assert sha(original)==parent['ZIP_SHA256']
    files = {}
    with ZipFile(original) as z:
        for name,checksum in parent['files'].items():
            data = z.read(name)
            assert digest(data)==checksum
            if name=='README-KO.txt':
                data = (ROOT/'docs/nes-mmc866-trial.ko.md').read_bytes()
            elif name.endswith('/firmware.stm'):
                data = fw
            elif name.endswith('/fpga_mmc855.bi3'):
                assert data==image
            elif name.endswith('/ROM-NOT-INCLUDED.txt'):
                assert b'mmc855.nes' in data
                data = data.replace(b'mmc855.nes',b'mmc866.nes')
            files[name.replace('855','866')] = data
    assert len(files)==11 and all('restore' not in n.lower() and not n.lower().endswith('.nes') for n in files)
    report = dict(edition=866,physical=False,ARM=firmware,client=client,flash_B=len(fw),flash_free_B=212992-len(fw),
                  parent_zip=sha(original),board=board,boot=boot,checks=checks,final_link_runs=runs,
                  files={n:digest(b) for n,b in files.items()})
    files['manifest.json'] = (json.dumps(report,indent=2)+'\n').encode()
    archive = WORK/'MMC866-ADVENTURE-60SEC-SD-ROOT.zip'
    partial = archive.with_suffix('.partial')
    with ZipFile(partial,'w') as z:
        for name,data in files.items():
            z.writestr(ZipInfo(name),data,compress_type=ZIP_DEFLATED)
    with ZipFile(partial) as z:
        assert z.testzip() is None and z.namelist()==list(files) and all(z.read(n)==v for n,v in files.items())
    partial.replace(archive)
    report.update(ZIP_SHA256=sha(archive),ZIP_B=archive.stat().st_size)
    save(ROOT/'analysis/trial866-package.json',report)
    print(archive,report['ZIP_SHA256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('prepare')
    sub.add_parser('loader').add_argument('game', type=Path)
    sub.add_parser('guards').add_argument('temp', type=Path)
    sub.add_parser('arm-guards').add_argument('temp', type=Path)
    sub.add_parser('pack').add_argument('temp', type=Path)
    run_parser = sub.add_parser('replay')
    run_parser.add_argument('temp', type=Path)
    run_parser.add_argument('scene', choices=('opening','dense','transition'))
    run_parser.add_argument('phase', type=int, choices=(1,2))
    args = parser.parse_args()
    if args.action == 'prepare':
        rename_edition(OFFER, WORK/'patch', 855, 866)
    elif args.action == 'replay':
        run_scene(args.temp, args.scene, args.phase)
    elif args.action == 'loader':
        loader(args.game,SRC,866,WORK)
        save(WORK/'empty-offer.json',empty_offer(SRC))
    elif args.action == 'guards':
        guards(args.temp,args.temp/'nes-tile821-demo-jointmirror-p1-866-on',WORK/'receiver.json')
    elif args.action == 'arm-guards':
        with patch.object(check_nes_seal858,'ROOT',WORK):
            for case in ('stop','identity'):
                check_nes_seal858.check(args.temp,'866',CLIENT,SRC,case)
    elif args.action == 'pack':
        package(args.temp)
