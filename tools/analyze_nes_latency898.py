"""Separate physical frame-start bins from paired, clock-aligned source-frame replays."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from analyze_nes_output822 import CLK_MS
from compare_nes_latency898 import CLIPS


def read(p):
    return json.loads(p.read_bytes())


def hardware(downloads, reference):
    result = {}
    for n in ('872','897'):
        path = downloads/f'nes-budget-mmc{n}.txt'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == reference['runs'][n]['sha256'][path.name]
        b = dict(line.split('=',1) for line in path.read_text().splitlines() if '=' in line)
        result[n] = {}
        for clip,i in [('early',6),('late',11)]:
            vals = dict(zip(b['columns'].split(','), (int(x,16) for x in b[f'b{i:02}'].split(',')),strict=True))
            result[n][clip] = dict(counts=vals, ms_per_frame={
                k:int(b['tick_ms'])*vals[k]/vals['frames'] for k in ('recv','plan','seal')})
    return result


def collect(folder):
    summary = read(folder/'joint.json')
    assert summary['passed'] and summary['commits']==8 and summary['last_status']==1
    events = read(folder/'events.json')
    sent=[bytes.fromhex(json.loads(row)[2]) for row in (folder/'packets.jsonl').read_text().splitlines()]
    pushes=list(zip(sent,(e for e in events if e.get('opcode')=='0xe1'),strict=True))
    with (folder/'window.csv').open() as f:
        w = [{k:(v if k=='event' else int(v)) for k,v in row.items()} for row in csv.DictReader(f)]
    out = {}
    for i,fr in enumerate(summary['frames']):
        g=fr['generation']
        def select(kind):
            return [e for e in events if e.get('generation')==g and e['event']==kind]
        def wire(op, input=False):
            key='input_generation' if input else 'generation'
            return [e for e in events if e.get(key)==g and e.get('opcode')==op]
        def video(kind):
            return [r for r in w if r['g']==g and r['event']==kind]
        if i<2:
            show,=video('reveal')
            out[g]=dict(display=[show['frame'],show['line']],clock={'reveal':show['clock']})
            continue
        begin,=select('source_begin')
        plan,=select('planner_enter')
        seal,=video('seal')
        show,=video('reveal')
        ack,=[r for r in video('ack') if r['op']==3]
        assert ack['clock']==fr['ACK_masterclock']
        d1=wire('0xd1',True)
        d2=wire('0xd2',True)
        first_ea,=wire('0xea')
        def final_response(e):
            r=bytes.fromhex(e.get('reply',''))
            return (len(r)==20 and r[1]==0xf7 and r[2]&2 and r[3:5]==r[5:7]
                    and r[7:9]==b'\x01\x03' and int.from_bytes(r[15:17],'little')==g)
        valid_e0=[e for e in wire('0xe0') if ack['clock']<=e['clock']<=first_ea['start'] and final_response(e)]
        seal_tx,=[e for e in wire('0xe1') if e['packet_opcode']==3]
        dma=video('ppu_dma')
        ends=video('ppu_last')
        assert len(dma)==len(ends)>0 and all(a['clock']<=b['clock'] for a,b in zip(dma,ends))
        post=[r for r in dma if r['clock']>=seal['clock']]
        t = dict(capture_ready=begin['capture_ready'],source_begin=begin['clock'], first_d1=d1[0]['start'],
                 last_d2=d2[-1]['clock'],planner=plan['clock'],seal_issue=seal_tx['start'],
                 seal_accept=seal['clock'],first_dma=dma[0]['clock'],last_dma_end=ends[-1]['clock'],
                 first_residual_dma=post[0]['clock'] if post else None,
                 upload=video('upload165_entry')[0]['clock'],reveal=show['clock'],
                 final_ack=ack['clock'],valid_e0=valid_e0[0]['clock'],ea=first_ea['clock'])
        reuse=[(b,e) for b,e in pushes if b[:2]==bytes([9,4]) and int.from_bytes(b[8:10],'little')==g]
        reuse_load=[r for r in video('load') if r['op']==9 and r['section']==4]
        reuse_ack=[r for r in video('ack') if r['op']==9 and r['section']==4]
        assert len(reuse)==len(reuse_load)==len(reuse_ack)
        out[g]=dict(load=read(folder/'loads898.json')[i], clock=t,
                    oam_packets=[dict(issue=e['start'],load=r['clock'],ack=z['clock'],bytes=len(b))
                                 for (b,e),r,z in zip(reuse,reuse_load,reuse_ack)],
                    packet_order=[[b[0],b[1],int.from_bytes(b[10:12],'little'),len(b),e['start']]
                                  for b,e in pushes if int.from_bytes(b[8:10],'little')==g and g==910],
                    d1_count=len(d1),d1_wire=sum(e['bytes'] for e in d1),
                    dma=[[a['frame'],a['line'],a['value'],a['clock'],z['clock']] for a,z in zip(dma,ends)],
                    display=[show['frame'],show['line']],seal=[seal['frame'],seal['line']],
                    rgb=hashlib.sha256((folder/f'frame-{g}.rgb').read_bytes()).hexdigest(),
                    map_sha256=hashlib.sha256((folder/f'map-{g}.bin').read_bytes()).hexdigest())
    return out


def analyze(temp, downloads, dest):
    hw=hardware(downloads, read(dest.parent/'hardware897-results.json'))
    paired={}
    for clip,frames in CLIPS.items():
        paired[clip]={}
        for phase in (1,2):
            runs={n:collect(temp/f'nes-tile821-{clip}-jointmirror-p{phase}-898-{n}') for n in (872,897)}
            rows=[]
            for i,source in enumerate(frames[2:],2):
                g=905+i
                a,b=(runs[n][g] for n in runs)
                assert a['load']==b['load'] and a['rgb']==b['rgb'] and a['map_sha256']==b['map_sha256']
                assert a['d1_count']==b['d1_count'] and a['d1_wire']==b['d1_wire']
                prev=[runs[n][g-1] for n in runs]
                anchors=[p['clock']['reveal'] for p in prev]
                delta={k:round(((b['clock'][k]-anchors[1])-(a['clock'][k]-anchors[0]))/CLK_MS,4)
                       for k in a['clock'] if b['clock'][k] is not None and a['clock'][k] is not None}
                gap=[r['display'][0]-p['display'][0] for r,p in zip([a,b],prev)]
                rows.append(dict(source=source,g=g,previous_reveal=anchors,display_gap=gap,
                                 delta_ms_from_previous_reveal=delta,control=a,candidate=b))
            paired[clip][phase]=rows
    common={}
    for stem in ('nes_geometry_sender653','nes_native_export203','nes_native_mailbox165','nes_native_spi165',
                 'nes_chr_cache611','nes_obj_capture611','nes_native_frame201','nes_native_planes165',
                 'nes_patch_capture181','nes_patch_rows181','nes_native_compact181','nes_native_raster181'):
        data=(temp/'nes-trial816-board872'/f'{stem}.sv').read_bytes()
        assert data==(temp/'nes-trial816-board891E'/f'{stem}.sv').read_bytes()
        common[stem]=hashlib.sha256(data).hexdigest()
    dest.write_text(json.dumps(dict(physical=hw, paired=paired,master_clocks_per_ms=CLK_MS,
                                    preserved_RTL=common,rom=read(temp/'nes-latency898/index.json')['rom'],
                                    common_SPI_calibration='MMC872', warmup=2),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('temp','downloads','out'):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    analyze(a.temp,a.downloads,a.out)
