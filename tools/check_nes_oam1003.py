"""Verify 978 packet service, full receivers, STOP and the two-slot display deadline."""
import argparse
import json
from pathlib import Path

from check_nes_overlap1002 import rows
from check_nes_output970 import counters
from check_nes_plan975 import directory, read, sha
from nes_oam1003 import assemble, ORIGIN, PACKED, TEMPLATE_SIZE
from nes_stage1001 import candidate
from pack_nes_column854 import encode, decode
from test_nes_banks557 import MASTER


def packing(kind, stage):
    build = read(PACKED/'build.json')
    body = bytearray((PACKED/'body.bin').read_bytes())
    assert len(encode(bytes(body),build['prefix_B'],2,short_pairs=True)) == build['encoded_B']
    patches = dict(candidate(False)) if stage else {}
    patches.update(assemble(kind,stage)[4])
    for address, data in sorted(patches.items()):
        at = address - ORIGIN
        assert 0 <= at <= len(body)
        body[at:at+len(data)] = data
    packed = encode(bytes(body),build['prefix_B'],2,short_pairs=True)
    assert decode(packed,build['prefix_B'],len(body),2,short_pairs=True) == body
    fixed = TEMPLATE_SIZE if kind == 'dma' else 0
    return dict(encoded_B=len(packed),template_B=fixed,
                remaining_B=5056-build['loader_B']-len(packed)-fixed)


def packet(window, op):
    times = {r['event']:int(r['clock']) for r in window
             if (r['g'],r['op'],r['section']) == ('912',str(op),'4')}
    marks = [times[event] for event in ('load','oam_dma_setup','oam_accepted','ack')]
    assert marks == sorted(marks)
    return dict(load=marks[0],header_range_setup=marks[1]-marks[0],
                restore_service=marks[2]-marks[1],receipt=marks[3]-marks[2],
                total=marks[-1]-marks[0])


def inspect(temp, phase, previous):
    ref = directory(temp,phase,'978returned','cold')
    prefix = [r for r in rows(ref/'window.csv') if int(r['g'])<912]
    actual = {}
    for kind,mode,stage in [('stock','reference',False),('dma','reference',False),
                            ('fallback','reference',False),('words','reference',False),
                            ('dma','arb',False),('dma','tail',False),('words','arb',False),
                            ('words','tail',True),('words','joint',False)]:
        tag = f'{kind}-{mode}' + ('-stage' if stage else '')
        d = (directory(temp,phase,'1003wordsB','cold') if mode=='joint' else
             temp/(f'nes-oam1003-{kind}-{mode}-p{phase}'+('-stage' if stage else '')))
        result = read(d/'result.json')
        assert result['passed'] and (result['commits'],result['last_status']) == (8,1)
        win = rows(d/'window.csv')
        assert [r for r in win if int(r['g'])<912 and r['event']!='group1002'] == prefix
        for g in range(905,913):
            assert sha(d/f'frame-{g}.rgb') == sha(ref/f'frame-{g}.rgb')
        assert sum(int(r['value']) for r in prefix if (r['g'],r['op'],r['event'])==('909','-1','ppu_dma')) == 624
        if kind=='fallback':
            assert any(r['event']=='oam_generic' for r in win) and not any(r['event']=='template_dma' for r in win)
        if kind=='dma':
            assert sum(int(r['value']) for r in win if r['event']=='template_dma')==356
        if kind=='words':
            assert any(r['event']=='oam_write' for r in win)
        clocks = counters(d,912)
        group, = [int(r['clock']) for r in win if (r['g'],r['op'],r['event'])==('912','3','group1002')]
        actual[tag] = info = dict(literal=packet(win,2),repeat=packet(win,8),
                                  group=group,group_late_ms=round((group-previous['vblank46_start'])*1000/MASTER,6),
                                  reveal=clocks['reveal'],seal=clocks['seal'],ack=clocks['ack'],
                                  ack_delta=clocks['ack'][0]-previous['baseline']['ack'][0])
        if mode=='joint':
            events = read(d/'events.json')
            d2 = max(e['clock'] for e in events if e.get('input_generation')==910 and e.get('opcode')=='0xd2')
            assert d2==previous['protected']['D2_910']
            joint = read(d/'joint.json')
            assert joint['passed'] and joint['firmware_SHA256']==read(ref/'joint.json')['firmware_SHA256']
            ref_events=read(ref/'events.json')
            # After the last tile credit, the final status is followed by EA.
            def completion(stream):
                bus=[e for e in stream if e.get('generation')==912 and e.get('event')=='SPI']
                assert [e['opcode'] for e in bus[-2:]] == ['0xe0','0xea']
                assert bytes.fromhex(bus[-2]['reply'])[7]==1
                return [bus[-2]['clock'],bus[-1]['clock']]
            info.update(D2_910=d2,ARM_final_E0_EA=completion(events),baseline_E0_EA=completion(ref_events),
                        wire_B=joint['wire_B'],ARM_firmware=joint['firmware_SHA256'])
            def seal_tx(stream):
                (event,) = (e for e in stream if e.get('generation')==912 and e.get('opcode')=='0xe1' and e.get('packet_opcode')==3)
                return [event['start'],event['clock']]
            info['seal_SPI']=seal_tx(events)
            assert info['seal_SPI']==seal_tx(ref_events)
            assert joint['wire_B']==read(ref/'joint.json')['wire_B']
            info['last_section5_to_SEAL_load']={}
            for label,folder in [('baseline',ref),('candidate',d)]:
                trace=rows(folder/'window.csv')
                last=max(int(r['clock']) for r in trace if (r['g'],r['section'],r['event'])==('912','5','ack'))
                info['last_section5_to_SEAL_load'][label]=counters(folder,912)['load'][0]-last
        if mode in ('arb','tail'):
            starts = [list(map(int,line.split())) for line in (d/'starts.txt').read_text().splitlines()]
            assert len(starts)==20 and max(r[3] for r in starts)<2
    guards={}
    for fault,status in [('bad_range',224),('bad_seal',224),('mid_stop',228),('alt_stop',228)]:
        d=temp/f'nes-oam1003-words-tail-p{phase}-{fault}-stage'
        res=read(d/'result.json')
        assert res['passed'] and (res['commits'],res['last_status'])==(7,status)
        assert sha(d/'retained.rgb')==sha(ref/'frame-911.rgb')
        win=rows(d/'window.csv')
        faultrow,=[r for r in win if r['g']==('913' if fault=='bad_seal' else '912') and r['event']=='ack' and int(r['value'])==status]
        assert int(faultrow['op'])==(3 if fault=='bad_seal' else 8)
        if fault=='alt_stop':
            assert any(r['event']=='arbitrary_checked' and r['value']=='360' for r in win)
        if fault=='mid_stop':
            assert any(r['event']=='oam_write' for r in win)
        if fault=='bad_range':
            assert not any(r['event']=='oam_write' for r in win)
        guards[fault]=dict(packet=int(faultrow['op']),status=status,retained=911)
    return dict(protected=previous['protected'],vb46=previous['vblank46_start'],
                end246=previous['line246_end'],runs=actual,guards=guards)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    prior=read(Path(__file__).resolve().parents[1]/'analysis/overlap1002-results.json')
    result=dict(phases={n:inspect(args.temp,n,prior[str(n)]) for n in (1,2)},
                packing={key:packing(kind,stage) for key,kind,stage in
                         [('words','words',False),('dma','dma',False),('words_stage','words',True)]})
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
