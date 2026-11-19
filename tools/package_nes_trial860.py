"""Qualify and package only the final 60-second MMC860 link and fitted ROM."""
import argparse
import json
import struct
import zlib
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

import check_nes_seal858 as guards
from analyze_nes_map830 import window
from analyze_nes_output852 import measure
from check_nes_tail859 import tail_gap
from package_nes_trial704 import digest, read, save, sha
from package_nes_trial855 import board_proof, loader, reset_policy
from prepare_nes_trial860 import ARM, CLIENT, PROBES, ROOT, WORK

SRC=WORK/'link/src'
FW=SRC/'obj-nes-100/firmware.stm'
ARCHIVE='MMC860-ADVENTURE-60SEC-SD-ROOT.zip'


def qualify(temp):
    prior=read(ROOT/'analysis/tail859-results.json')
    baseline=read(ROOT/'analysis/seal858-results.json')['comparisons']['demo']
    result={}
    for scene in ('opening','transition','demo'):
        for phase in (1,2):
            original=prior['scenes'][scene][str(phase)]
            selected=original['859g']
            final,_,_=measure(temp,scene,phase,'on','860',column=True)
            assert final['arm']==sha(FW) and final['client']==sha(CLIENT/'sink165.sfc')==selected['client']
            keys=('gaps','display_VBlanks','verified_pictures','held_blank_VBlanks','final_ACK')
            assert all(final[k]==selected[k] for k in keys),(scene,phase)
            directory=temp/f'nes-tile821-{scene}-jointmirror-p{phase}-860-on'
            events=window(directory)
            shows=[e for e in events if e['event']=='reveal']
            assert [e['clock'] for e in shows]==selected['all_display_clocks']
            assert len(shows)==final['verified_pictures']
            summary={k:final[k] for k in keys}
            if scene=='demo':
                assert len(final['gaps'])==60 and sum(final['gaps'])==125
                frames={e['clock']:e['frame'] for e in shows}
                for source in ('2616','2617'):
                    clocks=selected['frames'][source]['clocks']
                    assert frames[clocks['reveal']]-frames[clocks['previous_reveal']]==2
                physical_link=baseline[str(phase)]['856-855']
                assert physical_link['display_VBlanks']==133 and final['final_ACK']<physical_link['final_ACK']
                summary['ACK_saved_masterclocks_vs_MMC855_matched']=physical_link['final_ACK']-final['final_ACK']
                assert final['final_ACK']<original['858e']['final_ACK']
                summary['ACK_saved_masterclocks_vs_858E']=original['858e']['final_ACK']-final['final_ACK']
            if scene=='opening':
                by_clock={e['clock']:e for e in shows}
                summary['opening_deadlines']={}
                for source in ('703','759'):
                    expected=selected['frames'][source]
                    event=by_clock[expected['clocks']['reveal']]
                    assert (event['frame'],event['line'])==(expected['reveal_frame'],expected['reveal_line'])
                    summary['opening_deadlines'][source]=dict(VBlank=event['frame'],line=event['line'])
            result[f'{scene}-{phase}']=summary
    return result


def pack(temp):
    evidence=read(ROOT/'analysis/tail859-results.json')
    parent=read(ROOT/'analysis/trial855-package.json')
    fw=FW.read_bytes()
    old=(ARM/'obj-nes-100/firmware.stm').read_bytes()
    assert digest(old)==evidence['links']['g']['sha256']
    assert fw[32:]==old[32:].replace(b'855',b'860')
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==size+512<=212992
    assert zlib.crc32(fw[512:])==crc and crc^inverse==0xffffffff
    for name in ('NES MMC3 860.nh1','mmc860.nes','fpga_mmc860.bi3',
                 'nes-progress-mmc860.txt','nes-budget-mmc860.txt','nes-game-last-mmc860.txt'):
        assert name.encode()+b'\0' in fw
    board,image=board_proof(temp,parent['board'],'860',CLIENT,'855')
    assert set(board['fit']['min_slack_ns'])==set(parent['board']['fit']['min_slack_ns'])
    programmer_src=PROBES/'nes-repeat227/arm01/src'
    board['programmer_sources']={}
    for file in ('fpga.c','ff.c','ff.h','ffconf.h','diskio.h','ccsbcs.c'):
        checksum=sha(SRC/file)
        assert checksum==sha(programmer_src/file)
        board['programmer_sources'][file]=checksum
    assert board['programmer_sources']['fpga.c']==board['image']['programmer']['programmer_sha256']
    board['default_column_policy']=reset_policy(SRC)
    runs=qualify(temp)
    checks={k:read(WORK/f'{k}.json') for k in ('loader','menu','timer','windows')}
    base=read(WORK/'base/result.json')
    assert checks['windows']['firmware_SHA256']==base['firmware_sha256']==digest(fw)
    assert all(checks[k]['firmware']==digest(fw) for k in ('loader','menu','timer'))
    assert checks['loader']['rom']==parent['checks']['loader']['rom']
    assert checks['menu']['rows']['normal']['released'] and checks['timer']['passed']
    assert base['passed'] and base['safe_return'] and base['base_restored']
    assert base['config_paths']==['/sd2snes/fpga_mmc860.bi3','/sd2snes/fpga_base.bi3']
    assert checks['windows']['unfinished_excluded'] and checks['windows']['layout']=='demo'
    assert [(r['start_s'],r['end_s']) for r in checks['windows']['accepted']]==[(1,30),(30,60)]
    checks['base']=base
    faults={k:read(WORK/f'860-{k}.json') for k in ('stop','identity','consumer','table','coverage','gap')}
    assert faults['stop']['no_EA_or_D3'] and faults['identity']['committed_unchanged']
    assert faults['gap']==dict(commits=1,status=224) and faults['table']['status']==224
    assert all(v['status']==224 for v in faults['coverage'].values())
    assert all(faults['consumer'][k]['status']==228 for k in ('stop','late-stop'))
    assert faults['consumer']['partial']['active_bank_preserved'] and faults['consumer']['restart']==dict(commits=2,status=1)
    boot=[c for c in read(temp/'nes-trial860-boot/result.json')['cases'] if c['ROM']==sha(CLIENT/'sink165.sfc')]
    assert sorted((c['fault'],c['kind']) for c in boot)==[(False,'restored'),(True,'rejected')]
    original=PROBES/'nes-trial855/MMC855-ADVENTURE-60SEC-SD-ROOT.zip'
    assert sha(original)==parent['ZIP_SHA256']
    files={}
    with ZipFile(original) as z:
        for name,checksum in parent['files'].items():
            data=z.read(name)
            assert digest(data)==checksum
            if name=='README-KO.txt':
                data=(ROOT/'docs/nes-mmc860-trial.ko.md').read_bytes()
            elif name.endswith('/firmware.stm'):
                data=fw
            elif name.endswith('/fpga_mmc855.bi3'):
                data=image
            elif name.endswith('/ROM-NOT-INCLUDED.txt'):
                assert b'mmc855.nes' in data
                data=data.replace(b'mmc855.nes',b'mmc860.nes')
            files[name.replace('855','860')]=data
    assert len(files)==11 and not any('restore' in n.lower() or n.lower().endswith('.nes') for n in files)
    report=dict(edition=860,physical=False,ARM=digest(fw),flash_B=len(fw),flash_free_B=212992-len(fw),
                client=sha(CLIENT/'sink165.sfc'),parent_zip=sha(original),board=board,
                checks=checks,guards=faults,boot=boot,final_link_runs=runs,
                files={name:digest(data) for name,data in files.items()})
    files['manifest.json']=(json.dumps(report,indent=2)+'\n').encode()
    archive=WORK/ARCHIVE
    tmp=archive.with_suffix('.partial')
    with ZipFile(tmp,'w') as z:
        for name,data in files.items():
            z.writestr(ZipInfo(name),data,compress_type=ZIP_DEFLATED)
    with ZipFile(tmp) as z:
        assert z.testzip() is None and z.namelist()==list(files) and all(z.read(n)==v for n,v in files.items())
    tmp.replace(archive)
    report.update(ZIP_SHA256=sha(archive),ZIP_B=archive.stat().st_size)
    save(ROOT/'analysis/trial860-package.json',report)
    print(archive,report['ZIP_SHA256'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('loader','consumer','arm-guards','pack'))
    p.add_argument('path',type=Path)
    a=p.parse_args()
    if a.action=='loader':
        loader(a.path,SRC,860,WORK)
    elif a.action=='pack':
        pack(a.path)
    else:
        with patch.object(guards,'ROOT',WORK):
            for case in (('consumer','table','coverage') if a.action=='consumer' else ('stop','identity')):
                guards.check(a.path,'860',CLIENT,SRC,case)
        if a.action=='consumer':
            save(WORK/'860-gap.json',tail_gap(a.path,'860'))
