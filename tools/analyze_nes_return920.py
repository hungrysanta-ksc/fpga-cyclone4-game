"""Match physical bank returns, CRC-checked E8 heads and visible PPU deadlines."""
import argparse
import json
from pathlib import Path

from analyze_nes_credit919 import batches, ms, read
from analyze_nes_first918 import tile_bytes
from analyze_nes_issue917 import coverage, read_csv, sha, summarize
from nes_return920 import MODES, WORK, arm, client
from test_nes_raw506_joint import crc


def path(temp,phase,mode,cache):
    return temp/f'nes-tile821-obj-jointmirror-p{phase}-920{mode}-{cache}-pair'


def heads(folder,edges=False):
    trace=[r for r in read_csv(folder,'window.csv') if r['g']=='908' and r['op']=='7']
    if edges:
        bus=folder/'guard-bus920'
        assert read(bus/'result.json')['passed']
        traced=[r for r in read_csv(bus,'window.csv') if r['g']=='908' and r['op']=='7']
        assert trace==[r for r in traced if r['event'] not in ('first_write920','last_write920','after_dma920')]
        trace=traced
    e8=[e for e in read(folder/'events.json') if e.get('generation')==908 and e.get('opcode')=='0xe8' and 'reply' in e]
    jobs=[j for s in (folder/'producer.jsonl').read_text().splitlines() if (j:=json.loads(s))['generation']==908]
    returns=dict(read(folder/'returns904.json'))
    packets=[bytes.fromhex(json.loads(s)[2]) for s in (folder/'packets.jsonl').read_text().splitlines()]
    tiles=[p for p in packets if p[0]==7 and p[8:10]==(908).to_bytes(2,'little')]
    output=[]
    for job,packet,row in zip(jobs,tiles,[r for r in trace if r['event']=='load'],strict=True):
        token=job['token']
        assert token==int.from_bytes(packet[16:20],'little')
        desc=bytes([1,packet[1]])+packet[14:16]+packet[10:12]+packet[8:10]+packet[16:20]
        times={r['event']:int(r['clock']) for r in trace if r['index']==row['index']}
        assert all(int(r['value'])==token for r in trace if r['index']==row['index'] and r['event'].endswith('920'))
        i,e=next((i,e) for i,e in enumerate(e8) if bytes.fromhex(e['reply'])[6:18]==desc)
        reply=bytes.fromhex(e['reply'])
        assert reply[1:3]==bytes([0xd7,4]) and crc(reply[1:19],8,7,0)==reply[19]
        timing=['load','header920','bulk194920','mark212920','append212920','first_read920','last_read920','consume920','ack']
        assert [times[x] for x in timing]==sorted(times[x] for x in timing)
        assert job['producer']<=e['clock']<=times['load'] and times['consume920']==returns[token]
        ready=max(job['producer'],output[-1]['times']['consume920'] if output else 0)
        assert ready<=e['clock']
        record=dict(token=token,size=job['bytes'],kind=job['kind'],ready=round(job['producer']),
                    head_eligible=round(ready),E8_ordinal=i+1,E8_start=round(e['start']),E8_end=round(e['clock']),
                    previous_E8_end=round(e8[i-1]['clock']) if i else None,
                    times=times,admit_setup_ms=ms(times['first_read920']-times['load']),
                    aperture_ms=ms(times['last_read920']-times['first_read920']),
                    after_read_ms=ms(times['consume920']-times['last_read920']),
                    service_ms=ms(times['consume920']-times['load']))
        if edges:
            # Mesen announces the opcode following STA before the transfer. Use
            # the actual aperture read and WRAM port write for the byte interval.
            assert times['DMA_instruction920']<=times['first_read920']<times['first_write920']
            assert times['first_write920']<times['last_read920']<times['last_write920']<times['after_dma920']<=times['consume920']
            record.update(copy_ms=ms(times['last_write920']-times['first_read920']),
                          before_copy_ms=ms(times['first_read920']-times['load']),
                          after_copy_ms=ms(times['consume920']-times['last_write920']))
        output.append(record)
    assert [(j['kind'],j['size']) for j in output]==[(0,16),(1,64),(1,544)]
    return output


def analyze(temp):
    cases={}
    for phase in (1,2):
        for cache in ('warm','cold'):
            base=temp/f'nes-tile821-obj-jointmirror-p{phase}-915stepfinal-{cache}-pair'
            ref,packets,t0=summarize(base,arm('reference'))
            expected=tile_bytes(base)
            group=cases[f'{phase}-{cache}']={}
            for mode in MODES:
                d=path(temp,phase,mode,cache)
                m,out,t=summarize(d,arm(mode))
                assert ref['parameters']==m['parameters'] and sha(client(mode)/'sink165.sfc')==m['client']
                assert batches(d)==batches(base) and tile_bytes(d)==expected
                for g in packets:
                    assert [p for p in packets[g] if p[0]!=7]==[p for p in out[g] if p[0]!=7]
                    for pattern in ('map-{}.bin','colors636-{}.bin','frame-{}.rgb'):
                        file=pattern.format(g)
                        assert sha(base/file)==sha(d/file)
                for g in ref['frames']:
                    assert ref['frames'][g]['section5_hash']==m['frames'][g]['section5_hash']
                measured=heads(d)
                if mode=='reference':
                    assert t0['reveal']==t['reveal'] and ref['final_ACK']==m['final_ACK'] and m['preDMA']==ref['preDMA']
                if mode in ('reference','joint') and cache=='warm':
                    extra=path(temp,phase,mode+'edges',cache)
                    exact=heads(extra,True)
                    assert read(d/'verified905.json')==read(extra/'verified905.json')
                    for a,b in zip(measured,exact,strict=True):
                        assert all(b['times'][k]==v for k,v in a['times'].items())
                        assert a['E8_end']==b['E8_end']
                    measured=exact
                prev=group.get('reference',{}).get('heads',measured)
                group[mode]=dict(heads=measured,E8_gain_ms=[ms(x['E8_end']-y['E8_end']) for x,y in zip(prev,measured)],
                    pre908=m['preDMA'][908],pre912=m['preDMA'][912],pre912_B=len(coverage(m['preDMA'][912])),
                    pre912_matches=coverage(m['preDMA'][912]).keys()==coverage(ref['preDMA'][912]).keys(),
                    palette=t['palette'],OAM=t['OAM'],section5=t['section5'],SEAL=t['SEAL'],upload=t['upload'],
                    last_return_to_SEAL_ms=ms(t['SEAL'][0]-measured[-1]['times']['consume920']),
                    upload_gain_ms=ms(t0['upload'][0]-t['upload'][0]),reveal=t['reveal'],intervals=m['intervals'],
                    ACK912=m['final_ACK'],ACK_gain_ms=ms(ref['final_ACK']-m['final_ACK']))
    guards={}
    for mode in MODES:
        proof=arm(mode)/'proof'
        firmware=arm(mode)/'link/src/obj-nes-100/firmware.stm'
        assert all(read(proof/f)['firmware']==sha(firmware) for f in ('loader.json','timer.json','menu.json'))
        base=read(proof/'base/result.json')
        rx=read(proof/'sram.json')['cases']
        assert base['safe_return'] and base['firmware_sha256']==sha(firmware) and read(proof/'timer.json')['passed']
        assert read(proof/'menu.json')['rows']['normal']['released']
        assert len(rx['normal']['d0_sites'])==4 and rx['normal']['checked_retire'] and not rx['bad-crc']['checked_retire']
        guards[mode]=dict(ARM=sha(firmware),Flash=firmware.stat().st_size,ROM=sha(client(mode)/'sink165.sfc'),
                          ROM_free=read(client(mode)/'build.json')['physical_free_B'],SRAM_D0=4,boot_STOP_base_menu=True)
        if mode in ('copy','mask','joint','first'):
            tests=read(WORK/f'{mode}-guards.json')
            assert all(tests[k]==dict(commits=c,status=s) for k,c,s in [
                ('stop-copy',3,228),('descriptor',3,224),('duplicate',3,224),('seal',4,224),('display_stop',4,228)])
            guards[mode]['consumer_faults']=tests
    return dict(cases=cases,guards=guards)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(analyze(args.temp),indent=2)+'\n',encoding='utf8')
