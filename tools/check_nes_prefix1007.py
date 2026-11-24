"""Verify the plan-prefix experiment against the 978 ARM and 65816 traces."""
import argparse
import json
from collections import Counter
from pathlib import Path

from check_nes_plan975 import directory, milliseconds, packet_path, read, sha
from check_nes_output970 import counters
from check_nes_blank959 import rows


def inspect(temp, phase, count):
    folder = directory(temp,phase,f'1007c{count}','cold')
    baseline = directory(temp,phase,'978returned','cold')
    run = read(folder/'joint.json')
    assert run['passed'] and run['commits']==8 and run['last_status']==1
    for name in ('firmware_SHA256','client_SHA256'):
        assert run[name]==read(baseline/'joint.json')[name]
    win = rows(folder/'window.csv')
    old = rows(baseline/'window.csv')
    if str(count)=="0":
        for name in ('events.json','window.csv','producer.jsonl','records.bin'):
            assert sha(folder/name)==sha(baseline/name),name
    assert [r for r in win if int(r['g'])<912]==[r for r in old if int(r['g'])<912]
    for g in range(905,913):
        assert sha(folder/f'frame-{g}.rgb')==sha(baseline/f'frame-{g}.rgb')
    dma909 = sum(int(r['value']) for r in win if (r['g'],r['op'],r['event'])==('909','-1','ppu_dma'))
    assert dma909 == 624
    events = read(folder/'events.json')
    protected = read(baseline/'events.json')
    def last_d2(trace):
        return max(e['clock'] for e in trace if e.get('input_generation')==910 and e.get('opcode')=='0xd2')
    assert last_d2(events)==last_d2(protected)
    planner, = [e['clock'] for e in events if e['generation']==912 and e['event']=='planner_enter']
    packets = [e for e in events if e.get('generation')==912 and e.get('opcode')=='0xe9']
    def records(path):
        return [r['records'] for r in read(path/'e9931.json') if r['g']==912]
    transmitted = records(folder)
    assert Counter(r for batch in transmitted for r in batch)==Counter(r for batch in records(baseline) for r in batch)
    assert len(transmitted)==len(packets)
    assert all(sum(len(x)//2 for x in batch)+8==packet['bytes'] for batch,packet in zip(transmitted,packets))
    def destinations(path):
        image = {}
        for line in (path/'packets.jsonl').read_text().splitlines():
            _, _, raw, bulk = json.loads(line)
            header = bytes.fromhex(raw)
            if header[0]!=7 or int.from_bytes(header[8:10],'little')!=912:
                continue
            offset = int.from_bytes(header[10:12],'little')
            payload = bytes.fromhex(bulk)
            assert len(payload)==int.from_bytes(header[14:16],'little')
            for i, byte in enumerate(payload):
                key = (header[1],offset+i)
                assert key not in image
                image[key] = byte
        return image
    tiles_written = destinations(folder)
    assert tiles_written==destinations(baseline)
    if str(count)=='12ordered':
        original = records(baseline)
        assert transmitted==[original[0][:12],original[0][12:],original[1]]
    marks = read(temp/f'nes-prefix1007-c{count}-p{phase}.json')
    # The append hook observes SRAM after the sorted suffix copy, before CRC or E8.
    first_batch = [r for r in marks if r['sent']==0]
    assert first_batch[-1]['body']==''.join(transmitted[0])
    assert [r['count'] for r in first_batch]==list(range(1,len(first_batch)+1))
    tiles = [json.loads(l) for l in (folder/'producer.jsonl').read_text().splitlines()]
    tiles = [j for j in tiles if j['generation']==912]
    if str(count)=='12ordered':
        original_tiles = [json.loads(l) for l in (baseline/'producer.jsonl').read_text().splitlines()]
        fields = ('token','kind','bytes')
        assert [tuple(j[k] for k in fields) for j in tiles] == [
            tuple(j[k] for k in fields) for j in original_tiles if j['generation']==912]
    wire = Counter()
    for e in events:
        if e['generation']==912 and e['event']=='SPI':
            wire[e['opcode']]+=e['bytes']
    last_small = None
    if str(count) in ('0','12ordered'):
        commands, ledger = packet_path(folder,912,expected_shape=(21,8))
        packet, row = next((bytes.fromhex(c[3]),r) for c,r in zip(commands[-len(ledger):],ledger,strict=True)
                           if c[1]==7 and int.from_bytes(bytes.fromhex(c[3])[16:20],'little')==36)
        assert int.from_bytes(packet[14:16],'little')==32
        last_small = row
    checks = counters(folder,912)
    base = counters(baseline,912)
    committed = []
    previous = Counter()
    for row in first_batch:
        body = bytes.fromhex(row['body'])
        assert body[:3]==bytes.fromhex('829003') and (len(body)-3)%8==0
        current = Counter([body[:3]]+[body[i:i+8] for i in range(3,len(body),8)])
        entry, = (current-previous).elements()
        assert not previous-current
        previous = current
        committed.append(dict(count=row['count'],record=entry.hex(),
                              after_planner_ms=milliseconds(row['clock']-planner),
                              before_E9_ms=milliseconds(packets[0]['start']-row['clock'])))
    dma = [[int(r[k]) for k in ('clock','frame','line','value','op')] for r in win
           if r['g']=='912' and r['event']=='ppu_dma']
    return dict(first_batch=committed,DMA912=dma,early_DMA912_B=sum(x[3] for x in dma if x[-1]==-1),
                checked_tile_bytes=len(tiles_written),token36=last_small,
                vb46_receipts=[dict(event=r['event'],line=int(r['line']),op=int(r['op']),section=int(r['section']))
                               for r in win if r['g']=='912' and r['frame']=='46' and 225<=int(r['line'])<=252
                               and r['event'] in ('load','ack')],
                batches=transmitted,E9=[dict(bytes=e['bytes'],issue=e['start'],end=e['clock']) for e in packets],
                first_accept_gain_ms=milliseconds(next(e['clock'] for e in protected if e.get('generation')==912
                                                       and e.get('opcode')=='0xe9')-packets[0]['clock']),
                tile_ready=[[j['kind'],j['bytes'],j['producer']] for j in tiles],
                seal_to_ACK=checks,ack_gain_ms=milliseconds(base['ack'][0]-checks['ack'][0]),
                wire_bytes=wire, dma909=dma909, reveal908=counters(folder,908)['reveal'],
                last_D2_910=last_d2(events),source_sha256=run['firmware_SHA256'],RGB_equal=8)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--counts',nargs='+',choices=('0','1','2','12','12ordered'),default=['0','1','2','12','12ordered'])
    a=p.parse_args()
    result = {phase:{n:inspect(a.temp,phase,n) for n in a.counts} for phase in (1,2)}
    guards = {}
    for phase in (1,2):
        for fault, expected in (('stop_decode',228),('bad_seal',224)):
            out = a.temp/f'nes-prefix1007-c2-p{phase}-{fault}'
            raw = read(out/'result.json')
            assert raw['passed'] and (raw['commits'],raw['last_status'])==(7,expected)
            trace = directory(a.temp,phase,'978returned','cold')
            assert sha(out/'retained.rgb')==sha(trace/'frame-911.rgb')
            guards[f'{phase}-{fault}'] = dict(status=expected,retained=911)
    a.out.write_text(json.dumps(dict(phases=result,guards=guards),indent=2)+'\n',encoding='utf8',newline='\n')
