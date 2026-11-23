"""Gate the installable supplier separately from the four-page calendar model."""
import json
import re
import struct
import sys
import zlib
from pathlib import Path

from analyze_nes_deadline947 import inspect, directory, coverage, read, sha, Calendar, MASTER
from analyze_nes_input949 import timing
from prepare_nes_trial950 import RELEASE, ROM
from read_nes_supply905 import decode

ROOT = Path(__file__).resolve().parents[1]


def compare(temp):
    ref = read(ROOT/'analysis/header950-results.json')['cases']
    cal = Calendar(temp/'nes-service509-rom03')
    fw = RELEASE/'link/src/obj-nes-100/firmware.stm'
    data = fw.read_bytes()
    n, crc, inv = struct.unpack_from('<III', data, 8)
    assert data[:4]==b'STM3' and n+512==len(data)<=212992 and crc^inv==0xffffffff and crc==zlib.crc32(data[512:])
    names = ('fpga_mmc950.bi3','mmc950.nes','nes-progress-mmc950.txt','nes-budget-mmc950.txt',
             'nes-game-last-mmc950.txt','nes-frame-mmc950.bin',' 950.nh1')
    for name in names:
        assert name.encode()+b'\0' in data and name.replace('950','925').encode()+b'\0' not in data
    rows = {}
    for cache in ('warm','cold'):
        for phase in (1,2):
            case = cache+str(phase)
            original = ref[case]['bound']
            old, content = inspect(directory(temp,phase,'950bound',cache), RELEASE.parent/'bound',cal)
            for provider in ('release','board'):
                folder = directory(temp,phase,'950'+provider,cache)
                m, quality = inspect(folder,RELEASE,cal)
                assert all(quality[k]==content[k] for k in ('map','colors','RGB','sections','tiles'))
                pages = decode(folder/'records.bin',950)
                assert all('invalid' not in r for r in pages['rows'])
                trace = timing(folder)
                margin = original['final_D2']+original['capture_line_margin']-m['capture_D2']
                ack_gain = original['final_ACK']+original['ACK_advance_vs935']-m['final_ACK']
                before = m['prior_blank_B']
                target = coverage([p for p in old['preDMA'] if p[-1]==old['stages'][912]['frame']-1])
                actual = coverage([p for p in m['preDMA'] if p[-1]==m['stages'][912]['frame']-1])
                good = (margin>=0 and trace['returned_before_show']==17 and before==496 and actual.keys()==target.keys() and
                        m['total']==(13 if cache=='warm' else 14) and ack_gain>0)
                rows.setdefault(provider,{})[case] = dict(capture911_margin_us=round(margin*1e6/MASTER,3),
                    capture911_clock=m['stages'][911]['capture'], blocks910=trace['returned_before_show'],
                    preDMA_B=before,same_DMA_coverage=actual.keys()==target.keys(), intervals=m['total'],gaps=m['gaps'],
                    ACK912_clock=m['final_ACK'],advance_vs935_ms=round(ack_gain*1000/MASTER,6),pass_timing=good,
                    last_tile_clock=m['stages'][912]['last_OBJ'],seal_clock=m['stages'][912]['SEAL'],
                    joint_sha256=sha(folder/'joint.json'))
    source_board=temp/'nes-port914I/nes-trial816-board914'
    board=temp/'nes-board950/board950'
    packed=board.parent/'packed950'
    image=packed/'fpga_mmc950.bi3'
    from package_nes_trial704 import decode as unpack
    assert unpack(image.read_bytes())==(packed/'board.rbf').read_bytes()
    reports=('board.fit.rpt','board.sta.rpt','board.pin','board.fit.summary','board.sta.summary')
    for name in reports:
        assert sha(source_board/'output_files'/name)==sha(board/'output_files'/name)
    assert sha(ROM/'sink-program.hex')==sha(board/'sink-program.hex')
    assert sha(ROM/'sink-program.hex')!=sha(source_board/'sink-program.hex')
    sof=sha(board/'output_files/board.sof')
    assert sof==sha(packed/'board.sof') and sof!=sha(source_board/'output_files/board.sof')
    programmer=next(read(f) for f in sorted(packed.glob('programmer*/result.json'))
                    if read(f)['passed'] and read(f)['image_sha256']==sha(image)
                    and read(f)['rbf_sha256']==sha(packed/'board.rbf'))
    proof=read(RELEASE/'safety950.json')
    ident=read(RELEASE/'identity950.json')
    assert proof['firmware']==sha(fw) and proof['consumer']==sha(ROM/'sink165.sfc')
    assert proof['CRC_rejected'] and proof['menu'] and proof['SRAM_D0_sites']==4 and ident['unexpected_chunk_tested']
    windows=read(RELEASE/'proof/windows.json')
    assert windows['firmware_SHA256']==sha(fw) and [(x['start_s'],x['end_s']) for x in windows['accepted']]==[(1,30),(30,60)]
    base=read(RELEASE/'proof/base/result.json')
    assert base['base_restored'] and base['config_paths']==['/sd2snes/fpga_mmc950.bi3','/sd2snes/fpga_base.bi3']
    port={}
    for p in (1,2):
        log=board/f'port950-cold{p}.log'
        raw=log.read_text(encoding='utf-8',errors='replace').replace('\x00','')
        polls,different=map(int,re.search(r'E8914 compared=(\d+) different=(\d+)',raw).groups())
        chunks,count,hits,grants=map(int,re.search(r'PASS914 trace chunks=(\d+) bytes=(\d+) hits=(\d+) grants=(\d+)',raw).groups())
        assert polls>0 and different==0 and chunks==8 and count==656
        folder=directory(temp,p,'950rtl','cold')
        assert read(folder/'verified905.json')['final_ACK'][1]==rows['board'][f'cold{p}']['ACK912_clock']
        port[p]=dict(polls=polls,different=different,chunks=chunks,bytes=count,hits=hits,grants=grants,log=sha(log))
    return dict(physical=False, Flash_B=len(data),free_B=212992-len(data),firmware=sha(fw),
                consumer=sha(ROM/'sink165.sfc'), trace_edition=950, names=names,cases=rows,
                board_port=port,base_restored=True,independent_checks=proof,identity=ident,programmer=programmer,
                board_sof=sof,board_timing_pass=all(r['pass_timing'] for r in rows['board'].values()))


if __name__=='__main__':
    result=compare(Path(sys.argv[1]))
    (ROOT/'analysis/trial950-final-link.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for provider,group in result['cases'].items():
        for case,row in group.items():
            print(provider,case,row)
