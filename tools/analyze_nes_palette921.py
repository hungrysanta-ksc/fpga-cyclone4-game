"""Attribute palette latency using unmodified linked CPU instructions and checked SPI heads."""
import argparse
import json
from pathlib import Path

from analyze_nes_return920 import batches, coverage, heads, ms, read, sha, summarize, tile_bytes
from analyze_nes_issue917 import read_csv
from nes_palette921 import MODES, WORK, client, image


def directory(root, phase, mode, cache):
    return root/f'nes-tile821-obj-jointmirror-p{phase}-{mode}-{cache}-pair'


def palette(folder):
    events = [e for e in read(folder/'events.json') if e.get('opcode')=='0xe1']
    packets = [json.loads(row) for row in (folder/'packets.jsonl').read_text().splitlines()]
    for (_, end, header, _), event in zip(packets, events, strict=True):
        h = bytes.fromhex(header)
        if h[1]==3 and h[8:12]==bytes.fromhex('8c030000'):
            assert abs(event['clock']-end)<1 and event['packet_opcode']==h[0]
            return [round(event[key]) for key in ('start','clock')]
    raise AssertionError('missing first 908 palette')


def analyze(temp):
    result={}
    for phase in (1,2):
        for cache in ('warm','cold'):
            rows={}
            result[f'{phase}-{cache}']=rows
            ref=directory(temp,phase,'920reference',cache)
            refm,_,_=summarize(ref,image('baseline'))
            for mode in MODES:
                monitored=directory(temp,phase,'921'+mode,cache)
                folder=monitored
                if mode in MODES[:2] and cache=='cold':
                    folder=directory(temp,phase,'920'+('reference' if mode=='baseline' else 'first'),cache)
                if mode in ('prefix','stream'):
                    fault=read(folder/'fault.json')
                    def field(block,key,n=1):
                        part=fault[block]
                        pos=part['layout'][key]
                        return int.from_bytes(bytes.fromhex(part['bytes'])[pos:pos+n],'little')
                    assert field('plan','generation',2)==907 and field('plan','ending')==0
                    assert field('sink','error')==5
                    rows[mode]=dict(rejected=True,generation=907,ending=False,sink_error=5)
                    continue
                if mode in MODES[:2]:
                    original=directory(temp,phase,'920'+('reference' if mode=='baseline' else 'first'),cache)
                    assert (folder/'verified905.json').read_bytes()==(original/'verified905.json').read_bytes()
                m, packets, t=summarize(folder,image(mode))
                assert m['parameters']==refm['parameters']
                assert batches(folder)==batches(ref) and tile_bytes(folder)==tile_bytes(ref)
                for g in packets:
                    for filename in ('frame-{}.rgb','map-{}.bin','colors636-{}.bin'):
                        assert sha(folder/filename.format(g))==sha(ref/filename.format(g))
                assert all(f['section5_hash']==refm['frames'][g]['section5_hash'] for g,f in m['frames'].items())
                d=heads(folder)
                spi=palette(folder)
                steps={'E1_start':spi[0],'E1_end':spi[1],'SNES_load':t['palette'][0][0]}
                if (folder/'arm921.json').exists():
                    marks=read(folder/'arm921.json')
                    def first(name):
                        return next(r[1] for r in marks if r[0]==name)
                    # A prefix may be published before SEAL and before the
                    # generic span starts. Report absolute clocks in both cases.
                    steps.update(ARM_span=next((r[1] for r in marks if r[0]=='span'),None),ARM_packet=first('packet_wire'),
                                 ARM_enqueue=first('nes_window184_enqueue'),ARM_seal=first('nes_sink212_seal'),
                                 planner_OBJ_done=next((r[1] for r in marks if r[0]=='finish_obj810'),None))
                    assert steps['ARM_packet']<=steps['ARM_enqueue']<=spi[0]<=spi[1]<=steps['SNES_load']
                window=read_csv(folder,'window.csv')
                visible={int(r['g']):int(r['frame']) for r in window if r['event']=='reveal'}
                assert visible[912]-visible[906]==m['intervals']
                rows[mode]=dict(steps=steps,OBJ_E8=[[r['size'],r['E8_ordinal'],r['E8_end']] for r in d if r['kind']==1],
                     palette=t['palette'],OAM=t['OAM'],section5=t['section5'],seal=t['SEAL'],
                     upload=t['upload'],wait=t.get('upload_wait'),reveal=t['reveal'],
                     pre908=m['preDMA'][908],pre912=m['preDMA'][912],same912=coverage(m['preDMA'][912]).keys()==coverage(refm['preDMA'][912]).keys(),
                     E1_wire_bytes=m['wire']['0xe1'],visible=visible,intervals=m['intervals'],
                     followup={g:{r['event']:[int(r[k]) for k in ('clock','frame','line')]
                                  for r in window if r['g']==str(g) and r['op']=='3' and
                                  r['event'] in ('load','wait169','reveal','ack')} for g in (909,911,912)},
                     ack=m['final_ACK'],ACK_saved_ms=ms(refm['final_ACK']-m['final_ACK']),
                     flash=(image(mode)/'link/src/obj-nes-100/firmware.stm').stat().st_size)
    phase_cost={}
    for phase in (1,2):
        rows=result[f'{phase}-warm']
        ref,compact=rows['baseline'],rows['compact']
        assert compact['visible'][908]==ref['visible'][908]-1
        assert compact['intervals']==ref['intervals']==14
        assert compact['visible'][909]==ref['visible'][909] and compact['visible'][911]==ref['visible'][911]
        cold=result[f'{phase}-cold']['compact']
        assert cold['same912'] and len(coverage(cold['pre912']))==496
        def parts(steps):
            return [steps['ARM_span'], steps['ARM_packet']-steps['ARM_span'],
                    steps['ARM_enqueue']-steps['ARM_packet'],steps['E1_start']-steps['ARM_enqueue'],
                    steps['E1_end']-steps['E1_start'],steps['SNES_load']-steps['E1_end']]
        old,new=(rows[name]['steps'] for name in ('baseline','first'))
        delta=[b-a for a,b in zip(parts(old),parts(new),strict=True)]
        assert sum(delta)==new['SNES_load']-old['SNES_load']
        phase_cost[phase]=dict(zip(('before_palette','span','arbitration','issue','wire','consumer_queue'),
                                   delta,strict=True))
    return dict(cases=result,delta_920_minus_915_clocks=phase_cost,
                guards={name:verify_recovery(name) for name in ('handoff','overlap','tail','compact')})


def verify_recovery(name):
    proof=image(name)/'proof'
    firmware=image(name)/'link/src/obj-nes-100/firmware.stm'
    digest=sha(firmware)
    recovery=read(proof/'base/result.json')
    assert all(read(proof/f)['firmware']==digest for f in ('loader.json','timer.json','menu.json'))
    assert recovery['safe_return'] and recovery['firmware_sha256']==digest
    assert read(proof/'timer.json')['passed'] and read(proof/'menu.json')['rows']['normal']['released']
    rx=read(proof/'sram.json')['cases']
    assert len(rx['normal']['d0_sites'])==4 and rx['normal']['checked_retire'] and not rx['bad-crc']['checked_retire']
    guards=read(WORK/f'{name}-guards.json')
    assert all(guards[key]==dict(status=status,commits=count) for key,count,status in [
        ('stop-copy',3,228),('descriptor',3,224),('duplicate',3,224),('seal',4,224),('display_stop',4,228)])
    return dict(firmware=digest,consumer=sha(client('first')/'sink165.sfc'),
                flash_limit=212992,SRAM_D0=4,bad_CRC_rejected=True,menu=True,guards=guards)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    args.output.write_text(json.dumps(analyze(args.temp),indent=2)+'\n')
