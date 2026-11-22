"""Partition time in the two physical logs, separately from a linked DMA replay."""
import argparse
import json
import struct
from hashlib import sha256
from collections import Counter
from pathlib import Path
from statistics import mean

from analyze_nes_section909 import coverage, measure, read_csv
from analyze_nes_section910 import bus_between
from compare_nes_trial915 import compare
from nes_postobj916 import AFTER_DMA, ARM, ONE_DRAIN, PROBES, REPEAT
from read_nes_supply905 import ROW, MS, decode
from test_nes_raw506_joint import MASTER


def physical(logs):
    comparison=compare(logs,logs)
    keys=('input_E9','E9_head','head_ACK','total')
    by_tick={}
    hashes={}
    for n in (907,915):
        path=logs/f'nes-frame-mmc{n}.bin'
        raw=path.read_bytes()
        hashes[n]=sha256(raw).hexdigest()
        by_tick[n]={}
        for i,r in enumerate(decode(path,n)['rows']):
            tick,g,_,ia,ea,probe,_,_,_,bank,h,_=ROW.unpack_from(raw,16+i*ROW.size)
            origin,anchor,head=struct.unpack_from('<3H',h,6)
            # Query samples the anchor after ARM samples its ages. Quantisation
            # of a pair of FPGA stamps is bounded by one FPGA tick.
            before=((ia+probe/2)/64-((anchor-origin)&1023))*MS
            supply=((head-origin)&1023)*MS
            tail=(((anchor-head)&1023)-(ea+probe/2)/64)*MS
            total=(ia-ea)*MS/64
            assert abs(before+supply+tail-total)<1e-6
            assert tick not in by_tick[n]
            by_tick[n][tick]=dict(generation=g,bank=bank,kind=r.get('last_kind'),size=r.get('last_bytes',0),
                input_E9=before,E9_head=supply,head_ACK=tail,total=total,
                bridge_error_ms=MS+(probe/2+2)*MS/64)
    pairs=[]
    for match in comparison['matched_summary_ACK_ms']:
        tick=match['tick']
        a,b=(by_tick[n][tick] for n in (907,915))
        pairs.append(dict(tick=tick,old=a,new=b,saved_ms={k:a[k]-b[k] for k in keys}))
    def summary(rows):
        return {k:round(mean(r['saved_ms'][k] for r in rows),3) for k in keys}
    slower=[r for r in pairs if r['new']['kind']==1 and r['saved_ms']['E9_head']<0]
    return dict(trace_SHA256=hashes,pairs=pairs,mean_saved_ms=summary(pairs),slower_OBJ_mean_saved_ms=summary(slower),
                stage_delta_error_ms=max(round(r['old']['bridge_error_ms']+r['new']['bridge_error_ms'],3) for r in pairs))


def partition(folder,fw,reference):
    measurement,payloads=measure(folder,fw)
    ref,ref_packets=reference
    assert measurement['parameters']==ref['parameters']
    for g,packets in payloads.items():
        assert Counter(ref_packets[g])==Counter(packets)
        for bulk in (True,False):
            assert [b for b in packets if (b[0]==7)==bulk]==[b for b in ref_packets[g] if (b[0]==7)==bulk]
    clocks=measurement['clocks_per_second']
    assert clocks==MASTER
    trace=read_csv(folder,'window.csv')
    grants=json.loads((folder/'grants904.json').read_bytes())
    spi=[e for e in json.loads((folder/'events.json').read_bytes()) if e['event']=='SPI']
    ahead=folder/'ahead911.json'
    speculative=json.loads(ahead.read_bytes()) if ahead.is_file() else []
    result={}
    for g,f in measurement['frames'].items():
        assert f['section5_hash']==ref['frames'][g]['section5_hash']
        w=[(r['event'],int(r['clock'])) for r in trace if int(r['g'])==g and r['op']=='3']
        times=f['masterclocks']
        # Count only time inside wait169 and the true PPU DMA start/last-byte
        # callbacks. Setup, validation, publication and CPU overhead stay separate.
        opened={}
        used={'wait':0,'dma':0}
        for event,clock in w:
            if event in ('wait169','ppu_dma'):
                k='wait' if event=='wait169' else 'dma'
                assert not opened
                opened[k]=clock
            elif event.startswith('wait_return_') or event=='ppu_last':
                k='dma' if event=='ppu_last' else 'wait'
                used[k]+=clock-opened.pop(k)
        assert not opened
        marks=dict(w)
        residual=times['ACK']-times['SEAL']-sum(used.values())
        demand=[v for v in grants if v[0]==g and v[1]==1]
        uploads=[r for r in trace if r['g']==str(g) and r['op'] in ('3','-1')]
        for start,end in zip((r for r in uploads if r['event']=='ppu_dma'),
                             (r for r in uploads if r['event']=='ppu_last'),strict=True):
            assert start['frame']==end['frame'] and 225<=int(start['line'])<=int(end['line'])<262
        result[g]=dict(OBJ_demand_grants=len(demand),OBJ_demand_wait=sum(v[3]-v[2] for v in demand),
            OBJ_prefetch_grants=sum(v[0]==g for v in speculative),
            OBJ_to_SEAL=times['SEAL']-times['last_OBJ'],
            validation=marks['upload165_entry']-marks['validate181'],
            VBlank_wait=used['wait'],DMA=used['dma'],
            other_SEAL_to_ACK=residual-(marks['upload165_entry']-marks['validate181']),
            ARM_observe=times['E0_response']-times['ACK'],display=f['VBlank'][3],
            SEAL=times['SEAL'],ACK=times['ACK'],before_SEAL_B=len(coverage(measurement['preDMA'][g])),
            before_SEAL_same_addresses=coverage(measurement['preDMA'][g]).keys()==coverage(ref['preDMA'][g]).keys(),
            E0=times['E0_response'])
        row=result[g]
        row['OBJ_to_SEAL_SPI_count_ms']=bus_between(spi,times['last_OBJ'],times['SEAL'])
        assert sum(row[k] for k in ('validation','VBlank_wait','DMA','other_SEAL_to_ACK'))==row['ACK']-row['SEAL']
    return dict(frames=result,intervals=measurement['intervals'],final_ACK=measurement['final_ACK'],
                ARM=measurement['firmware'],consumer=measurement['client'],SPI_B=measurement['wire'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs',type=Path);p.add_argument('temp',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args()
    result=dict(hardware=physical(args.logs),replay_clock_Hz=MASTER,replays={})
    for phase in (1,2):
        for cache in ('warm','cold'):
            baseline=args.temp/f'nes-tile821-obj-jointmirror-p{phase}-915stepfinal-{cache}-pair'
            reference=measure(baseline,ARM)
            for tag,arm in [('907',PROBES/'nes-trial907'),('915stepfinal',ARM),('916index',ARM),
                            ('916drain',ONE_DRAIN),('916repeat',REPEAT),('916afterdma',AFTER_DMA)]:
                path=args.temp/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{cache}-pair'
                result['replays'][f'{phase}-{cache}-{tag}']=partition(path,arm,reference)
    result['guards']={}
    for arm in (ARM,ONE_DRAIN,REPEAT,AFTER_DMA):
        fw=(arm/'link/src/obj-nes-100/firmware.stm').read_bytes()
        checksum=sha256(fw).hexdigest()
        def proof(name):return json.loads((arm/'proof'/name).read_bytes())
        assert proof('sram.json')['cases']['normal']['checked_retire'] and not proof('sram.json')['cases']['bad-crc']['checked_retire']
        assert proof('timer.json')['passed'] and proof('menu.json')['rows']['normal']['released']
        assert proof('base/result.json')['safe_return'] and proof('base/result.json')['firmware_sha256']==checksum
        result['guards'][arm.name]=dict(Flash_B=len(fw),SHA256=checksum,SRAM_D0_sites=len(proof('sram.json')['cases']['normal']['d0_sites']),
            bad_CRC_rejected=True,timer_STOP=True,base_return=True,menu_return=True)
    result['guards']['65816_fault_injection']=json.loads((PROBES/'nes-postobj916/guards.json').read_bytes())
    for tag in ('916drain','916repeat','916afterdma'):
        for case,status in [('stop',228),('invalid-seal',224)]:
            guard=json.loads((PROBES/f'nes-postobj916/{tag}-{case}.json').read_bytes())
            assert guard==dict(commits=4,status=status)
            result['guards'][f'{tag}-{case}']=guard
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
