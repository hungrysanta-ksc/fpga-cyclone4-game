"""Attribute the delta from one 905 E8 reply with matched plans, pixels and binaries."""
import csv
import json
import re
import sys
from pathlib import Path

from analyze_nes_chr951 import logtext, port_log, read, sha, ROOT
from nes_admission954 import TAG, directory, evidence
from nes_companion952 import project
from test_nes_banks557 import MASTER


def measure(folder):
    events = read(folder/'events.json')
    with (folder/'window.csv').open() as f:
        seal = [r for r in csv.DictReader(f) if r['g']=='905' and r['op']=='3']
    def pipe(event, field='clock'):
        row, = [r for r in seal if r['event']==event]
        return int(row[field])
    def input_op(op):
        return [r for r in events if r.get('input_generation')==906 and r.get('opcode')==op]
    data = input_op('0xd2')
    commit, = input_op('0xd3')
    d1 = input_op('0xd1')
    assert len(data)==len(d1) and data[-2]['clock'] < commit['start'] < data[-1]['clock']
    wire = [json.loads(line) for line in (folder/'e9wire914-905.jsonl').read_text().splitlines()]
    tiles = [r for r in events if r.get('generation')==905 and r.get('packet_opcode')==7]
    assert len(tiles)==2
    stages = dict(last_E9_seal=round(wire[-1][0]),last_OBJ_E1=round(tiles[-1]['start']),SEAL_load=pipe('load'),
                  last_DMA_start=max(int(r['clock']) for r in seal if r['event']=='ppu_dma'),
                  reveal=pipe('reveal'),ACK=pipe('ack'),first_906_D1=round(d1[0]['start']),
                  last_906_data_D2=round(data[-2]['clock']),commit_906_D2=round(data[-1]['clock']))
    frames = read(folder/'joint.json')
    assert frames['passed'] and frames['commits']==8 and frames['frames'][0]['ACK_masterclock']==stages['ACK']
    return dict(stages=stages,reveal_frame_line=[pipe('reveal',k) for k in ('frame','line')],
                E9_seals=[round(t) for t,b in wire],E8_count=sum(e.get('generation')==905 and
                e.get('opcode')=='0xe8' for e in events),D2_blocks=len(data)), frames


def compare(temp, phase):
    original, change, idx, start, payload, cmd = evidence(temp,phase)
    candidate = directory(temp,phase,TAG,'cold')
    a,old_link = measure(original)
    b,new_link = measure(candidate)
    assert all(old_link[k]==new_link[k] for k in ('firmware_SHA256','client_SHA256','parameters','vram_DMA_B'))
    for pattern in ('map-{}.bin','frame-{}.rgb','colors636-{}.bin'):
        for g in range(905,913):
            assert sha(original/pattern.format(g))==sha(candidate/pattern.format(g))
    before,after=(read(d/'events.json') for d in (original,candidate))
    def prefix(events):
        i, = [i for i,e in enumerate(events) if e.get('opcode')=='0xe8' and
              e['generation']==905 and round(e['start'])==round(probe['start'])]
        return events[:i], events[i]
    from test_nes_banks557 import host_after
    probe, = [e for e in before if e.get('opcode')=='0xe8' and
              round(host_after(e['start']+7.5*MASTER/2625000,3))==change['sample']]
    prior, old = prefix(before)
    same, new = prefix(after)
    assert prior==same and old['reply']==change['before']['response'] and new['reply']==change['after']['response']
    issued=after[len(same)+1]
    assert issued['opcode']=='0xe9' and round(issued['start'])==start and issued['bytes']==len(payload)
    ports={}
    for g in (905,906):
        name=f'e9wire914-{g}.jsonl'
        wires=lambda folder:[json.loads(s)[1] for s in (folder/name).read_text().splitlines()]
        assert wires(original)==wires(candidate)
        tr=candidate/f'gen{g}'
        full=tr/'full.log'
        summary=port_log(full)
        ref=port_log(original/f'gen{g}'/'port952-checked.log')
        origin=int((tr/'origin914.txt').read_text())
        assert summary['error'] is None and summary['chunks_bytes_hits_grants'][:2]==ref['chunks_bytes_hits_grants'][:2]
        observed=summary['published']
        targets=[r for r in after if r.get('generation')==g and r.get('packet_opcode')==7]
        assert len(observed)==len(targets)==summary['chunks_bytes_hits_grants'][0]
        assert all(k==i and origin+at<=targets[i-1]['start'] for i,(k,n,at) in enumerate(observed,1))
        ports[g]=dict(chunks_bytes=summary['chunks_bytes_hits_grants'][:2],polls_differences=summary['polls'],
                      published=[origin+v[2] for v in observed],log_sha256=sha(full))
        if g==905:
            marker=r'ACCEPT954 batch=(\d+) edge=(\d+) bytes=(\d+) plans=(\d+) crc=([0-9a-fA-F]+)'
            prefixlog=temp/'nes-admission954'/f'p{phase}/prefix.log'
            record,=re.findall(marker,logtext(full))
            assert re.findall(marker,logtext(prefixlog))==[record]
            batch,edge,length,count=map(int,record[:4])
            assert (batch,length,count,int(record[4],16))==(idx,len(payload)-8,payload[3],int.from_bytes(payload[-4:-2],'big'))
            assert abs(edge+origin-round(issued['clock']))<=1
            ports[g].update(accepted_batch_one_based=batch+1,seal_absolute=edge+origin,
                            wire_SHA256=change['after']['payload_sha256'],body_B=length,plans=count,
                            prefix_log_sha256=sha(prefixlog))
            original_origin=int((original/'gen905/origin914.txt').read_text())
            for i,name in enumerate(('BG_publication','OBJ_publication')):
                a['stages'][name]=original_origin+ref['published'][i][2]
                b['stages'][name]=ports[g]['published'][i]
    return dict(phase=phase,wire_B=len(payload),issue_advance_clocks=round(cmd['start'])-start,
                original=a,early=b,delta_clocks={k:v-a['stages'][k] for k,v in b['stages'].items()},rtl=ports)


def main(temp):
    proofs=temp/'nes-admission954'
    fw=read(proofs/'arm/proof/menu.json')
    board=project(temp,'checked')
    ref=read(ROOT/'analysis/companion952-results.json')
    assert fw['firmware']==ref['safety']['firmware'] and fw['rows']['normal']['released']
    assert read(proofs/'arm/proof/base/result.json')['base_restored']
    assert read(proofs/'arm/proof/sram.json')['cases']['normal']['checked_retire']
    loader=read(proofs/'arm/proof/loader.json')['cases']
    assert loader['original']['program'] and not loader['damaged']['program']
    assert read(proofs/'consumer.json')==ref['safety']['STOP']
    sof=sha(board/'output_files/board.sof')
    assert sof==ref['variants']['checkedrows']['board']['reports']['board.sof']
    assert 'PASS914 checked' in logtext(board/'guards951.log')
    out=dict(master_Hz=MASTER,physical=False,single_E8_intervention=True,board_sof=sof,
             firmware=fw['firmware'],consumer=ref['safety']['consumer'],checks=read(proofs/'consumer.json'),
             menu_base_recovery=True,cases=[compare(temp,p) for p in (1,2)])
    (ROOT/'analysis/admission954-results.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    main(Path(sys.argv[1]))
