"""Match the input generation on D1/D2 to the preceding display identity."""
import argparse
import json
from pathlib import Path

from analyze_nes_section909 import coverage, measure, read_csv
from analyze_nes_section910 import guards, ms
from nes_overlap913 import BASE, work
from nes_prefetch912 import OUT, peer
from test_nes_raw506_joint import PERIOD


def audit(directory, firmware, baseline, packets, directory907):
    run,body=measure(directory,firmware)
    assert run['parameters']==baseline['parameters']
    for g,reference in packets.items():
        for tile in (True,False):
            assert [b for b in reference if (b[0]==7)==tile]==[b for b in body[g] if (b[0]==7)==tile]
        assert peer.sha(directory/f'frame-{g}.rgb')==peer.sha(directory907/f'frame-{g}.rgb')
    events=json.loads((directory/'events.json').read_bytes())
    window=read_csv(directory,'window.csv')
    for g,f in run['frames'].items():
        assert f['section5_hash']==baseline['frames'][g]['section5_hash']
        for op in ('3','-1'):
            w=[e for e in window if e['g']==str(g) and e['op']==op]
            starts=[e for e in w if e['event']=='ppu_dma']
            ends=[e for e in w if e['event']=='ppu_last']
            assert len(starts)==len(ends)
            for a,b in zip(starts,ends):
                assert a['frame']==b['frame'] and 225<=int(a['line'])<=int(b['line'])<262
    stamps={}
    for g in (911,912):
        src=next(e for e in events if e['event']=='source_begin' and e['generation']==g)
        output=[e for e in events if e.get('opcode')=='0xe1' and e['generation']==g]
        input_spi=[e for e in events if e.get('input_generation')==g and e['event']=='SPI']
        reads=[e for e in input_spi if e['opcode']=='0xd1']
        pops=[e for e in input_spi if e['opcode']=='0xd2']
        previous=run['frames'][g-1]['masterclocks']
        ea=next(e for e in events if e.get('opcode')=='0xea' and e['generation']==g-1)
        d3,=[e for e in input_spi if e['opcode']=='0xd3']
        assert previous['ACK']<=previous['E0_response']<=ea['start']<ea['clock']<d3['start']
        assert len(pops)==len(reads) and pops[-2]['clock']<d3['start']<pops[-1]['clock']<output[0]['start']
        stamps[g]=dict(capture_ready=src['capture_ready'],first_D1=round(reads[0]['start']),
            data_D2=round(pops[-2]['clock']),commit_D2=round(pops[-1]['clock']),
            reads_before_previous_show=sum(e['clock']<=previous['show'] for e in reads),
            reads_before_previous_ACK=sum(e['clock']<=previous['ACK'] for e in reads),
            previous_show=previous['show'],previous_ACK=previous['ACK'],previous_EA=round(ea['clock']),
            D3=round(d3['start']),first_ordinary=round(next(e['start'] for e in output if e['packet_opcode'] not in (1,3,7))),
            first_palette=next(int(r['clock']) for r in window if r['g']==str(g) and r['event']=='load' and r['section']=='3' and r['op']=='2'))
    uploads=run['preDMA'][912]
    f=run['frames'][912]
    return dict(intervals=run['intervals'],reveal=[r['VBlank'][3] for r in run['frames'].values()],
                ACK=run['final_ACK'],ACK_delta_ms=ms(run['final_ACK']-baseline['final_ACK']),
                E0=f['masterclocks']['E0_response'],SEAL=f['masterclocks']['SEAL'],show=f['masterclocks']['show'],
                last_240=f['section5_pair'][-1]['accept'],
                wait_lines=[[int(r['frame']),int(r['line'])] for r in window if r['g']=='912' and r['op']=='3' and r['event']=='wait169'],
                pre_bytes=len(coverage(uploads)),preDMA=uploads,stamps=stamps,
                exact_496=coverage(uploads).keys()==coverage(baseline['preDMA'][912]).keys() and len(coverage(uploads))==496)


def collect(temp,modes):
    result={}
    for phase in (1,2):
        for state in ('warm','cold'):
            def directory(tag):
                return temp/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{state}-pair'
            ref=directory('907')
            baseline,packets=measure(ref,BASE)
            rows=result[f'{phase}-{state}']={}
            for tag,fw in [('907',BASE),('912bleading',BASE)]+[('913'+m,work(m)) for m in modes]:
                rows[tag]=audit(directory(tag),fw,baseline,packets,ref)
                if tag!='907':
                    assert peer.sha(directory(tag)/'client.sfc')==peer.sha(OUT/'consumer/sink165.sfc')
            edge=rows['912bleading']['stamps'][912]['capture_ready']-240*341*4-PERIOD
            for row in rows.values():
                row['commit911_minus_target_edge_ms']=ms(row['stamps'][911]['commit_D2']-edge)
    return result


def acceptance(rows,mode):
    firmware=work(mode)
    arm=guards(firmware)
    assert arm['flash']<=212992
    obj=json.loads((firmware/f'obj-{mode}.json').read_bytes())
    assert obj['firmware']==arm['firmware']
    sram=json.loads((firmware/'proof/sram.json').read_bytes())['cases']
    gaps={k:v['static_gap_bytes'] for k,v in sram.items()}
    assert min(gaps.values())>0 and all(v['first_stack_write_to_static'] is None for v in sram.values())
    stop=json.loads((firmware/'stop.json').read_bytes())
    corrupt=json.loads((firmware/'bad-seal.json').read_bytes())
    assert stop==dict(commits=4,status=228) and corrupt==dict(commits=4,status=224)
    for condition,variants in rows.items():
        r=variants['913'+mode]; ref=variants['907']; prev=variants['912bleading']
        assert r['ACK']<ref['ACK'] and r['E0']<ref['E0']
        if condition.endswith('warm'):
            assert r['intervals']<ref['intervals'] and r['reveal'][-1]<prev['reveal'][-1]
            assert r['stamps'][912]['first_D1']<prev['stamps'][912]['first_D1']
            assert r['stamps'][912]['first_ordinary']<prev['stamps'][912]['first_ordinary']
            assert r['stamps'][912]['reads_before_previous_show']==17
            assert r['reveal'][-2]==prev['reveal'][-2] and r['reveal'][-1]==prev['reveal'][-1]-1
            assert r['commit911_minus_target_edge_ms']<0
        else:
            assert r['exact_496'] and r['intervals']<=17
            earlier=coverage(prev['preDMA']); after=coverage(r['preDMA'])
            assert earlier.keys()==after.keys() and all(after[k]<=earlier[k] for k in earlier)
    return dict(ARM=arm,stack_gap=gaps,OBJ=obj,STOP=stop,invalid_SEAL=corrupt,
                consumer_SHA256=peer.sha(OUT/'consumer/sink165.sfc'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('modes',nargs='+')
    p.add_argument('--select',choices=['idle','ordinary'])
    a=p.parse_args()
    rows=collect(a.temp,a.modes)
    proof=acceptance(rows,a.select) if a.select else None
    a.output.write_text(json.dumps(dict(comparisons=rows,selected=a.select,proof=proof),indent=2)+'\n',encoding='utf8')
