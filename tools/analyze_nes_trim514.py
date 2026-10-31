# SPDX-License-Identifier: MIT
"""Verify MMC509/control/trim against the same target-bank images and final display calendar."""
import argparse
import binascii
import csv
import json
from pathlib import Path
from statistics import mean
from analyze_nes_transfer512 import CLOCKS_PER_MS, equivalent_packets, fpga, logical_packets, read
from nes_raw506 import sha

def packets(folder,capture):
    result=[]
    saved=[]
    for p,tile in logical_packets(folder):
        if p[0]==10:
            g=int.from_bytes(p[8:10],"little")
            at,n,crc=(int.from_bytes(p[i:i+2],"little") for i in (10,12,14))
            lo,hi=at//64*64,(at+n+63)//64*64
            assert g>=907 and at%8==n%8==0 and 0<n<hi-lo<=192 and hi<=4096
            def bank(frame):
                return (capture/f"frame{frame}/expected-map.bin").read_bytes()
            old,new=bank(g-2),bank(g)
            prefix,suffix=old[lo:at],old[at+n:hi]
            assert prefix==new[lo:at] and suffix==new[at+n:hi] and new[at:at+n]==p[16:]
            assert binascii.crc_hqx(prefix+suffix,65535)==crc
            saved.append(dict(generation=g,start=lo,logical_B=hi-lo,sent_B=n,omitted_B=hi-lo-n))
            p=bytes([2])+p[1:10]+lo.to_bytes(2,'little')+(hi-lo).to_bytes(2,'little')+bytes(2)+prefix+p[16:]+suffix
        result.append((p,tile))
    return equivalent_packets(result),saved

def service(folder,saved):
    def read_cost(name):
        with (folder/name/'service.csv').open() as f:
            rows=[{k:int(v) for k,v in row.items()} for row in csv.DictReader(f)]
        assert len(rows)==396
        return {(r['generation'],r['offset']//64*64):r for r in rows if r['section']==2 and r['op'] in (2,4,10)}
    original,trim=read_cost('original'),read_cost('trim')
    rows=[]
    for packet in saved:
        key=packet['generation'],packet['start']
        a,b=original[key],trim[key]
        assert a['op']==2 and b['op']==10
        rows.append(dict(**packet,original_clocks=a['clocks'],partial_clocks=b['clocks']))
    return dict(records=len(rows),original_ms=sum(r['original_clocks'] for r in rows)/CLOCKS_PER_MS,
                partial_ms=sum(r['partial_clocks'] for r in rows)/CLOCKS_PER_MS,rows=rows,
                scope="Isolated packet-ready to ACK. The 12-frame common clock is reported separately.")

def check(a):
    base=a.temp/'nes-transfer512-original04'
    reference=read(base/'joint.json')
    oracle,_=packets(base,a.capture)
    boards={"original":fpga(a.temp/'nes-fault507-board01'),"trim":fpga(a.temp/'nes-trim514-fit01')}
    original_board=a.temp/'nes-fault507-board01'
    trim_board=a.temp/'nes-trim514-fit01'
    inputs=read(original_board/'source-pins.json')['board_inputs']
    assert all(sha(original_board/k)==v for k,v in inputs.items())
    changed=[k for k,v in inputs.items() if sha(trim_board/k)!=v]
    assert changed==['sink-program.hex'],changed
    views={}
    saved=[]
    for name,d,fw,client in (
        ('original',base,a.probes/'nes-service509/ARM03',a.probes/'nes-output489/client03'),
        ('control',a.temp/'nes-trim514-control-joint01',a.probes/'nes-trim514/ARM-control01',a.probes/'nes-output489/client03'),
        ('trim',a.temp/'nes-trim514-joint01',a.probes/'nes-trim514/ARM01',a.probes/'nes-trim514/design01/client')):
        j=read(d/'joint.json')
        assert j['passed'] and j['commits']==12 and j['last_status']==1 and j['parameters']==reference['parameters']
        assert j['future_ACK_filtered'] and j['max_bulk_banks']<=2 and j['ROM_read_allocations']==3280
        expanded,partials=packets(d,a.capture)
        assert expanded==oracle
        if name=='trim':saved=partials
        else:assert not partials
        if name!='original':assert j['map_WRAM_VRAM_verified']==12
        events=read(d/'events.json')
        assert sum(e.get('opcode')=='0xea' for e in events)==12
        for g in range(905,917):
            observed=[e['bytes'] for e in events if e.get('opcode')=='0xd1' and e['generation']==g]
            rtl=(a.temp/'nes-transfer512-spilegacy01'/f'transactions-{g}.txt').read_text().splitlines()
            assert observed==[int(l.split()[0]) for l in rtl if l.split()[1].startswith('d1')]
            assert sha(d/f'frame-{g}.rgb')==sha(base/f'frame-{g}.rgb')
        times=[f['ACK_masterclock'] for f in j['frames']]
        assert [f['generation'] for f in j['frames']]==list(range(905,917))
        gaps=[(b-a)/CLOCKS_PER_MS for a,b in zip(times,times[1:])]
        blob=fw/'src/obj-nes-100/firmware.stm'
        assert sha(blob)==j['firmware_SHA256']
        size=(fw/'size.log').read_text().splitlines()[-1].split()
        wire=j['wire_B']
        board=boards['trim' if name=='trim' else 'original']
        assert sha(client/'sink-program.hex')==board['report_SHA256']['sink-program.hex']
        views[name]=dict(first_ms=(times[0]-j['parameters']['start'])/CLOCKS_PER_MS,second_gap_ms=gaps[0],
                         later10_ms=sum(gaps[1:]),later_mean_ms=mean(gaps[1:]),later_min_ms=min(gaps[1:]),later_max_ms=max(gaps[1:]),
                         later_intervals_ms=gaps[1:],final_ACK_clocks=times,VRAM_DMA_B=j['vram_DMA_B'],E1_B=wire['0xe1'],
                         E0_queries=wire['0xe0']//20,wire_B=sum(wire.values()),wire_by_op=wire,
                         IRQ=j['SysTick_calls'],ARM_instructions=j['ARM_instructions'],ROM_reads=j['ROM_read_allocations'],
                         firmware_B=blob.stat().st_size,Flash_free_B=0x34000-blob.stat().st_size,data_B=int(size[1]),BSS_B=int(size[2]),
                         workspace_end=j['workspace_end'],observed_stack_low=j['observed_stack_low'],
                         stack_gap_B=int(j['observed_stack_low'],16)-int(j['workspace_end'],16),
                         SNES_body_B=read(client/'build.json')['body_bytes'],SNES_stack_B=j['observed_stack_B'],
                         extra_SNES_WRAM_B=8 if name=='trim' else 0,FPGA=name if name=='trim' else 'original',
                         firmware_SHA256=sha(blob),joint_SHA256=sha(d/'joint.json'),events_SHA256=sha(d/'events.json'),trace_SHA256=sha(d/'packets.jsonl'))
    omitted=sum(x['omitted_B'] for x in saved)
    for field in ('VRAM_DMA_B','E1_B'):
        assert views['original'][field]-views['trim'][field]==omitted
    queue=read(a.temp/'nes-trim514-queue01/result.json')
    assert queue['passed'] and queue['trace_SHA256']==views['trim']['trace_SHA256'] and queue['partial']==len(saved)
    assert queue['RTL_SHA256']==sha(trim_board/'nes_sink_spi165.sv')
    guard=read(a.temp/'nes-trim514-guards02/guards.json')
    assert len(guard)==10 and all(r['passed'] for r in guard.values())
    history=read(a.probes/'nes-trim514/history01.json')
    assert history['firmware_SHA256']==views['trim']['firmware_SHA256'] and history['passed']
    recovery={}
    for fault in ('none','program','done','busy','token'):
        item=read(a.probes/f'nes-trim514/recovery-{fault}/result.json')
        assert item['passed'] and item['firmware_sha256']==views['trim']['firmware_SHA256']
        recovery[fault]=dict(safe_return=item['safe_return'],base_restored=item['base_restored'])
    return dict(scope="12 pinned SMB3 captures, linked Cortex-M4 and actual 65816 on a modeled SPI/IRQ/ROM schedule. No new physical board run.",
                changed_board_inputs=changed,parameters=reference['parameters'],selected_hardware="MMC509",native_hz=21477272,runs=views,boards=boards,queue=queue,
                partial_records=len(saved),omitted_B=omitted,service=service(a.temp/'nes-trim514-cost01',saved),
                guards={k:[r['commits'],r['last_status']] for k,r in guard.items()},ARM_history=history,cleanup=recovery,
                RGB_equal=12,all_packet_lanes_equal_after_expansion=True,stop_reboot_maps_verified=2)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('probes','temp','capture','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    result=check(a)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
