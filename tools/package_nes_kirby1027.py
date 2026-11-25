"""Release only a fitted, timing-closed board and its verified, renamed ARM link."""
import re
import struct
import tempfile
import zlib
from pathlib import Path

from nes_cf68_pair_preflight import encode, decode
from package_nes_trial700 import checked
from package_nes_trial872 import ROOT, digest, read, write_verified_archive
from check_nes_kirby1027_header import WORK


def timing(routed):
    fit=(routed/'board.fit.summary').read_text()
    assert 'Fitter Status : Successful' in fit and 'Lite Edition' in fit
    le=int(re.search(r'Total logic elements : ([\d,]+)',fit)[1].replace(',',''))
    usage=(routed/'board.fit.rpt').read_text(errors='replace')
    def resource(name):
        return int(re.search(r'; '+re.escape(name)+r'\s*;\s*([\d,]+) /',usage)[1].replace(',',''))
    sta=(routed/'board.sta.summary').read_text()
    slacks=[float(v) for v in re.findall(r'^Slack : ([-.\d]+)',sta,re.M)]
    tns=[float(v) for v in re.findall(r'^TNS +: ([-.\d]+)',sta,re.M)]
    assert len(slacks)==len(tns)==57 and min(slacks)>=0 and all(v==0 for v in tns)
    io={}
    for line in (routed/'io.tsv').read_text().splitlines():
        corner,group,ns=line.split()
        io.setdefault(corner,{})[group]=float(ns)
    assert len(io)==3
    for delays in io.values():
        assert delays.keys()=={'address','upper','active','capture'}
        for group,edges in [('address',17),('upper',17),('active',16)]:
            delays[group+'_margin_ns']=round(edges*5.952-74-delays[group]-delays['capture'],3)
            assert delays[group+'_margin_ns']>0

    return dict(LE=le,LAB=resource('Total LABs:  partially or completely used'),M9K=resource('M9Ks'),
                STA_checks=len(slacks),min_slack_ns=min(slacks),io=io)


def programmer(routed,work,edition):
    raw=(routed/'board.rbf').read_bytes()
    packed=encode(raw)
    assert decode(packed)==raw
    scratch=Path(tempfile.mkdtemp(prefix=f'kirby{edition}-pgm-'))
    name=f'fpga_mmc{edition}.bi3'
    for n,d in [('board.rbf',raw),(name,packed)]:
        (scratch/n).write_bytes(d)
    checked('test_nes_nrom458_programmer.py',['--image',scratch/name,'--rbf',scratch/'board.rbf',
            '--out',scratch/'programmer'],work/'programmer.log')
    p=read(scratch/'programmer/result.json')
    assert p['passed'] and p['image_sha256']==digest(packed) and p['rbf_sha256']==digest(raw)
    return packed,p


def package():
    routed=WORK/'lite-tag'
    board=timing(routed)
    src=WORK/'link/src'
    fw=(src/'obj-nes-100/firmware.stm').read_bytes()
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and size+512==len(fw)<=212992 and zlib.crc32(fw[512:])==crc==(inverse^0xffffffff)
    for name in (' 1027.nh1','mmc1027.nes','fpga_mmc1027.bi3','nes-frame-mmc1027.bin',
                 *(f'nes-{k}-mmc1027.txt' for k in ('budget','game-last','progress'))):
        assert name.encode()+b'\0' in fw
    proof={k:read(WORK/'proof'/(k+'.json')) for k in ('timer','menu','base-result','sram','loader','sampling','journal','windows','header','trace')}
    status=(WORK/'status.log').read_text()
    assert 'PASS1027_STATUS 346 SPI73 bits' in status and 'PASS1027_BUS 10966 observed clocks' in status
    assert len(proof['header'])==7 and all(row['rejected'] for row in proof['header'][-2:])
    assert all(proof[k]['firmware']==digest(fw) for k in ('menu','timer','journal','sampling'))
    assert proof['base-result']['firmware_sha256']==proof['windows']['firmware_SHA256']==digest(fw)
    assert proof['base-result']['safe_return'] and proof['menu']['rows']['normal']['released'] and proof['timer']['passed']
    assert proof['journal']['end'][0]=='MENU_PREPARED' and proof['loader']['kirby']['program'] and proof['loader']['bad-last']['error']==4
    assert proof['sram']['cases']['normal']['checked_retire'] and 'bad-crc' in proof['sram']['cases']
    assert proof['sampling']['wire_reads']==proof['sampling']['windows']==75 and proof['trace']['reset']

    packed,p=programmer(routed,WORK,1027)
    report=dict(edition=1027,physical=False,reference_gameplay=1024,reference_trace=1025,
                **board,
                flash_B=len(fw),flash_free_B=212992-len(fw),firmware=digest(fw),board_BI3=digest(packed),
                SOF=digest((routed/'board.sof').read_bytes()),programmer=p,
                sampling=proof['sampling'],observer=proof['header'],stack_gap_B=proof['sram']['cases']['normal']['static_gap_bytes'])
    archive=WORK.parent/'nes-kirby1025/MMC1025-KIRBY-60SEC-SD-ROOT.zip'
    write_verified_archive(WORK,read(ROOT/'analysis/trial1025-package.json'),fw,packed,report,source=archive,game_label='KIRBY')


if __name__=='__main__':
    package()
