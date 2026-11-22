"""Account for the first BG receipt and palette transfer on one master clock."""
import argparse
import json
from pathlib import Path

from analyze_nes_first918 import tile_bytes
from analyze_nes_issue917 import MASTER, coverage, read_csv, summarize
from nes_credit919 import ARM, MODES, work, sha
from test_nes_raw506_joint import crc


def read(path):
    return json.loads(path.read_bytes())


def ms(clocks):
    return round(clocks*1000/MASTER, 4)


def receipt908(folder):
    events=[e for e in read(folder/'events.json') if e.get('generation')==908 and e.get('event')=='SPI']
    e1=[e for e in events if e['opcode']=='0xe1']
    packets=[bytes.fromhex(json.loads(s)[2]) for s in (folder/'packets.jsonl').read_text().splitlines()]
    packets=[p for p in packets if int.from_bytes(p[8:10],'little')==908]
    assert [p[0] for p in packets]==[e['packet_opcode'] for e in e1]
    tile=next(i for i,p in enumerate(packets) if p[:2]==bytes([7,0]))
    first=packets[tile]
    assert first[10:12]==bytes(2) and first[14:16]==bytes([16,0])
    palette=next(i for i,p in enumerate(packets) if p[1]==3)
    token=int.from_bytes(first[16:20],'little')
    returns=dict(read(folder/'returns904.json'))
    actual_return=returns[token]
    expected=bytes([0,7])+first[2:10]+bytes.fromhex('659a')
    polls=[(e,bytes.fromhex(e['reply'])) for e in events if e['opcode']=='0xe0' and e['clock']>actual_return]
    checked,reply=next((e,r) for e,r in polls if r[7:19]==expected and r[2]&2)
    assert crc(reply[1:19],8,7,0)==reply[19]
    sent,retired=(int.from_bytes(reply[i:i+2],'big') for i in (3,5))
    issued=e1[palette]['start']
    after_tile=[e for e in events if e1[tile]['clock']<=e['start']<issued]
    oam=next(i for i,p in enumerate(packets) if p[1]==4)
    tail=next(i for i,p in enumerate(packets) if p[1]==5 and int.from_bytes(p[10:12],'little')>=1121)
    assert packets[-1][0]==3
    stages={}
    for label,left,right in [('palette_to_OAM',palette,oam),('OAM_to_tail',oam,tail),('tail_to_SEAL',tail,len(e1)-1)]:
        lo,hi=e1[left]['start'],e1[right]['start']
        traffic=[e for e in events if lo<=e['start']<hi]
        stages[label]=dict(elapsed_ms=ms(hi-lo),spi_ms=ms(sum(e['clock']-e['start'] for e in traffic)),
                           E0=sum(e['opcode']=='0xe0' for e in traffic),E8=sum(e['opcode']=='0xe8' for e in traffic))
    loads=[int(r['clock']) for r in read_csv(folder,'window.csv') if r['event']=='load' and r['g']=='908']
    assert len(loads)==len(packets)
    jobs={j['token']:j for l in (folder/'producer.jsonl').read_text().splitlines()
          if (j:=json.loads(l))['generation']==908}
    obj=[]
    prior_return=actual_return
    for i,p in enumerate(packets):
        if p[:2]!=bytes([7,1]):
            continue
        handle=int.from_bytes(p[16:20],'little')
        j=jobs[handle]
        found=next(bytes.fromhex(e['reply']) for e in events if e['opcode']=='0xe8' and
                   (d:=bytes.fromhex(e['reply']))[6]==1 and int.from_bytes(d[14:18],'little')==handle)
        assert found[7]==1 and int.from_bytes(found[8:10],'little')==j['bytes'] and crc(found[1:19],8,7,0)==found[19]
        seen=next(e['clock'] for e in events if e.get('reply')==found.hex())
        assert j['bytes']==int.from_bytes(p[14:16],'little') and j['producer']<=seen<=loads[i]<=returns[handle]
        head_visible=max(prior_return,j['producer'])
        assert head_visible<=seen
        obj.append(dict(size=j['bytes'],token=handle,ready=round(j['producer']),first_valid_E8=round(seen),
                        prior_head_ms=ms(head_visible-j['producer']),visible_to_E8_ms=ms(seen-head_visible),
                        accept=loads[i],retire=returns[handle],accept_to_retire_ms=ms(returns[handle]-loads[i]),
                        before_accept_ms=ms(loads[i]-j['producer'])))
        prior_return=returns[handle]
    return dict(token=token,tile_issue=round(e1[tile]['start']),retire_clock=actual_return,
                E0_start=round(checked['start']),E0_end=round(checked['clock']),queued=(sent-retired)&65535,
                receipt_after_return_ms=ms(checked['clock']-actual_return),palette_issue=round(issued),
                palette_after_receipt_ms=ms(issued-checked['clock']),E0_cost_ms=ms(checked['clock']-checked['start']),
                until_palette_SPI=[dict(op=e['opcode'],size=e['bytes'],start=round(e['start']),end=round(e['clock']))
                                   for e in after_tile],
                intermediate_spi=[e['opcode'] for e in events if checked['clock']<=e['start']<issued],
                before_tile=[[p[0],p[1],int.from_bytes(p[10:12],'little')] for p in packets[:tile]],
                stages=stages,OBJ=obj,output_order=[[p[0],p[1],int.from_bytes(p[10:12],'little')] for p in packets])


def batches(folder):
    return {g:[b['count'] for b in row['banks557']] for g,row in read(folder/'banks904.json').items()}


def analyze(temp):
    out={}
    for phase in (1,2):
        for cache in ('warm','cold'):
            def directory(tag):
                return temp/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{cache}-pair'
            baseline=directory('915stepfinal')
            ref,old,oldtime=summarize(baseline,ARM)
            payload=tile_bytes(baseline)
            group=out[f'{phase}-{cache}']={}
            for mode in ('915',*MODES):
                folder=baseline if mode=='915' else directory('919'+mode)
                arm=ARM if mode=='915' else work(mode)
                m,packets,t=summarize(folder,arm)
                assert m['parameters']==ref['parameters'] and m['client']==ref['client']
                assert tile_bytes(folder)==payload and batches(folder)==batches(baseline)
                for g in packets:
                    for pattern in ('frame-{}.rgb','map-{}.bin','colors636-{}.bin'):
                        name=pattern.format(g)
                        assert sha(folder/name)==sha(baseline/name)
                    assert [p for p in packets[g] if p[0]!=7]==[p for p in old[g] if p[0]!=7]
                for g in m['frames']:
                    assert m['frames'][g]['section5_hash']==ref['frames'][g]['section5_hash']
                measured=receipt908(folder)
                assert measured['before_tile']==[[1,0,0],[2,5,0],[5,5,21]]
                group[mode]=dict(receipt908=measured,palette_accept=t['palette'][0],OAM_accept=t['OAM'][0],
                    section5_tail=t['section5'][-2:],SEAL=t['SEAL'],upload=t['upload'],reveal=t['reveal'],
                    upload_gain_ms=ms(oldtime['upload'][0]-t['upload'][0]),pre908=m['preDMA'][908],
                    intervals=m['intervals'],ACK912=m['final_ACK'],ACK_gain_ms=ms(ref['final_ACK']-m['final_ACK']),
                    pre912=m['preDMA'][912],bytes912=len(coverage(m['preDMA'][912])),
                    same_coverage912=coverage(ref['preDMA'][912]).keys()==coverage(m['preDMA'][912]).keys(),
                    E0_bytes=m['wire']['0xe0'],E8_bytes=m['wire']['0xe8'],
                    flash_bytes=(arm/'link/src/obj-nes-100/firmware.stm').stat().st_size)
    guards={}
    for mode in MODES:
        arm=work(mode)
        proof=arm/'proof'
        digest=sha(arm/'link/src/obj-nes-100/firmware.stm')
        assert all(read(proof/f)['firmware']==digest for f in ('loader.json','timer.json','menu.json'))
        assert read(proof/'timer.json')['passed'] and read(proof/'menu.json')['rows']['normal']['released']
        base=read(proof/'base/result.json')
        assert base['safe_return'] and base['firmware_sha256']==digest
        rx=read(proof/'sram.json')['cases']
        assert len(rx['normal']['d0_sites'])==4 and rx['normal']['checked_retire'] and not rx['bad-crc']['checked_retire']
        for case,status in [('stop',228),('bad-seal',224)]:
            assert read(arm/(case+'.json'))==dict(commits=4,status=status)
        guards[mode]=dict(sha256=digest,SRAM_D0=4,bad_CRC_rejected=True,boot_base_menu=True,
                          stop_status=228,bad_seal_status=224)
    return dict(clock_Hz=MASTER,cases=out,guards=guards)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    args.output.write_text(json.dumps(analyze(args.temp),indent=2)+'\n',encoding='utf8')
