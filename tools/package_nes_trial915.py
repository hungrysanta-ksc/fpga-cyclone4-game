"""Gate the 60-second SD root on the final firmware, 65816 ROM and fitted 914I image."""
import argparse
import re
import struct
import zlib
from pathlib import Path

from analyze_nes_overlap913 import BASE, OUT, PERIOD, audit, guards, measure, ms
from analyze_nes_port914 import audit_polls
from package_nes_frame862 import board
from package_nes_trial704 import digest, read, sha
from package_nes_trial872 import ROOT, write_verified_archive
from prepare_nes_trial915 import WORK, PROBES
from read_nes_supply905 import decode


def pack(temp,step=False):
    release=WORK.parent/'nes-trial915-step' if step else WORK
    prefix='915step' if step else '915'
    parent=read(ROOT/'analysis/trial907-package.json')
    fitted=read(ROOT/'analysis/port914-results.json')['guards']
    bi3,board_checks=board(temp/'nes-port914I',914,OUT/'consumer',temp/'nes-trial915-image')
    assert board_checks['image']['SOF']==fitted['board_sof']
    assert sha(OUT/'consumer/sink165.sfc')==fitted['consumer']
    fw=(release/'link/src/obj-nes-100/firmware.stm').read_bytes()
    n,crc,inverse=struct.unpack_from('<III',fw,8)
    assert n+512==len(fw)<=212992 and fw[:4]==b'STM3' and crc==zlib.crc32(fw[512:]) and crc^inverse==0xffffffff
    for name in ('nes-frame-mmc915.bin','nes-game-last-mmc915.txt','nes-progress-mmc915.txt','nes-budget-mmc915.txt',
                 'fpga_mmc915.bi3','mmc915.nes','NES MMC3 915.nh1'):
        assert name.encode()+b'\0' in fw,name
    proof=guards(release)
    assert proof['firmware']==digest(fw)
    for label,field in [('windows','firmware_SHA256'),('selector','firmware')]:
        proof[label]=read(release/f'proof/{label}.json')
        assert proof[label][field]==digest(fw)
    assert proof['selector']['selected_generation']==1212 and proof['selector']['retained_grants']==64
    for name,status in [('stop',228),('invalid-seal',224)]:
        proof[name]=read(release/f'proof/{name}.json')
        assert proof[name]==dict(commits=4,status=status)
    ref913=read(ROOT/'analysis/overlap913-results.json')['comparisons']
    case={}
    for p in (1,2):
        for cache in ('warm','cold'):
            key=f'{p}-{cache}'
            def d(tag):return temp/f'nes-tile821-obj-jointmirror-p{p}-{tag}-{cache}-pair'
            feedback=not step and p==2 and cache=='warm'
            tag='915physical' if feedback else prefix+'final'
            folder=d(tag)
            j=read(folder/'joint.json')
            assert j['passed'] and j['commits']==8 and j['last_status']==1 and j['vram_DMA_B']==22512
            assert (j['firmware_SHA256'],j['client_SHA256'])==(digest(fw),fitted['consumer'])
            ref,packets=measure(d('907'),BASE)
            r=audit(folder,release,ref,packets,d('907'))
            assert r['intervals']<ref['intervals'] and r['ACK_delta_ms']<0 and r['E0']<ref['frames'][912]['masterclocks']['E0_response']
            if cache=='cold':assert r['intervals']<=(16 if p==1 else 17) and r['exact_496']
            else:assert r['intervals']==14
            rtl_dir=temp/('nes-trial915-rtl-feedback' if feedback else 'nes-trial'+prefix+'-rtl')
            trace=(rtl_dir/f'trace-{key}.log').read_text(errors='replace')
            assert 'PASS914 trace chunks=8 bytes=656' in trace and 'Errors: 0,' in trace
            checks=[audit_polls(trace)]
            if cache=='warm':
                for g in (910,911):
                    lead=(rtl_dir/f'lead-{g}-{p}-warm.log').read_text(errors='replace')
                    assert 'PASS914 trace' in lead and 'Errors: 0,' in lead
                    checks.append(audit_polls(lead))
            assert all(not check['differences'] for check in checks)
            # The linked replay used the same plan schedule against which the
            # RTL produced the heads. Compare both the bytes and the seal times.
            def seals(tag):
                return [x['seal'] for x in read(d(tag)/'banks904.json')['912']['banks557']]
            def events(tag):
                return [(e['generation'],e['start'],e['reply']) for e in read(d(tag)/'events.json')
                        if e.get('opcode')=='0xe8' and e['generation'] in ((910,911,912) if cache=='warm' else (912,))]
            if feedback:
                # All three generations, including early readiness, were
                # physically replayed from this corrected run's own E9 bytes.
                for g in (910,911,912):
                    dump=trace if g==912 else (rtl_dir/f'lead-{g}-2-warm.log').read_text(errors='replace')
                    descriptors=re.findall(r'DESC914 edge=\d+ local_token=(\d+) kind=(\d+) bytes=(\d+) slot=(\d+) gen=(\d+)',dump)
                    replies=[bytes.fromhex(reply) for gen,_,reply in events(tag) if gen==g and bytes.fromhex(reply)[6]]
                    tokens=sorted(set(int.from_bytes(r[14:18],'little') for r in replies))
                    expected=[(tokens.index(int.from_bytes(r[14:18],'little'))+1,r[7],int.from_bytes(r[8:10],'little'),
                               int.from_bytes(r[10:12],'little')//(16<<r[7]),int.from_bytes(r[12:14],'little')) for r in replies]
                    assert expected and [tuple(map(int,v)) for v in descriptors]==expected
            else:
                assert seals(prefix+'wire')==seals(tag) and events(prefix+'wire')==events(tag)
            row=next(v for v in decode(folder/'records.bin',915,direct_probe=not step)['rows'] if 'detail' in v)
            assert row['commit_age_ticks512'] is not None and row['first_query_ticks512']>0
            if step:
                spans=read(folder/'step915.json')
                assert row['commit_step_ticks512']>0 and len(spans)==6
            edge=ref913[key]['912bleading']['stamps']['912']['capture_ready']-240*341*4-PERIOD
            margin=round(ms(edge-r['stamps'][911]['commit_D2'])*1000,3)
            if cache=='warm':assert margin>0
            previous_margin=-ref913[key]['913idle']['commit911_minus_target_edge_ms']*1000
            case[key]=dict(tag=tag,intervals=r['intervals'],before_SEAL_B=r['pre_bytes'],uploads=r['preDMA'],RGB=8,
                           final_ACK=r['ACK'],MMC907_final_ACK=ref['final_ACK'],ACK_delta_ms=r['ACK_delta_ms'],
                           capture_margin_us=margin,prior_capture_margin_us=round(previous_margin,3),
                           E8_samples=sum(c['samples'] for c in checks))
    source=PROBES/'nes-trial907'/parent['ZIP']
    reference=dict(edition=907,files=parent['members'],ZIP_SHA256=parent['ZIP_SHA256'])
    report=dict(edition=915,firmware=digest(fw),Flash_B=len(fw),free_B=212992-len(fw),client=fitted['consumer'],
                board=board_checks,proof=proof,cases=case,physical=False,
                capture_observer='paired COMMIT step timers' if step else 'COMMIT D2 return timestamp')
    write_verified_archive(WORK,reference,fw,bi3,report,source=source)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('temp',type=Path);p.add_argument('--step',action='store_true')
    a=p.parse_args();pack(a.temp,a.step)
