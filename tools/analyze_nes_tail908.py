"""Separate the two physical rows from the linked DMA/VBlank replays."""
import argparse
import csv
import json
import struct
from hashlib import sha256
from pathlib import Path
from statistics import median

from check_nes_game478 import Machine
from compare_nes_trial907 import capture
from nes_tail908 import BASE, WORK, ACK_WORK, FILL_WORK, sha
from read_nes_supply905 import ROW, MS, decode
from read_nes_frame900 import read_trace
from read_nes_tile903 import decode as tile903
from test_nes_raw506_joint import MASTER

TICKS=(5630,5767)
FIELDS=('BG','OBJ','map','bank','tiles','chunks','last_kind','last_bytes','last_offset')
ARM_TICK=MS/64


def bounds(mid,lower,upper):
    return [round(mid-lower,3),round(mid+upper,3)]


def measurements(folder):
    output={}
    by_tick={}
    for edition in (905,907):
        capture(folder,edition)  # checks ROM run, whole time window and menu recovery
        path=folder/f'nes-frame-mmc{edition}.bin'
        data=path.read_bytes()
        records=decode(path,edition)['rows']
        out={}
        tails=[]
        for i,row in enumerate(records):
            _,_,_,input_age,ack_age,probe,*_,header,_=ROW.unpack_from(data,16+i*ROW.size)
            origin,anchor,last=struct.unpack_from('<3H',header,6)
            # One FPGA subtraction, avoiding a double charge for the E9 phase.
            # ACK age is sampled before issuing SPI; anchor occurs within the measured query.
            mid=((anchor-last)&1023)*MS-ack_age*ARM_TICK
            tail=bounds(mid,MS+(probe+2)*ARM_TICK,MS)
            if row.get('last_kind')==1 and row['E9_to_last_publish_ms']>0:
                tails.append(tail)
            if row['tick'] not in TICKS:continue
            key=row['tick']
            assert key not in out and row['last_kind']==1
            prev=ROW.unpack_from(data,16+(i-1)*ROW.size)
            assert i and 0<=(row['tick']-prev[0])*10<200
            prev_anchor=struct.unpack_from('<H',prev[-2],8)[0]
            ack_gap=((anchor-prev_anchor)&1023)*MS-(ack_age-prev[4])*ARM_TICK
            # Previous query sampled after the previous verified E0. Subtract
            # the in-frame E9 duration to unwrap relative to that earlier query.
            prev_ack_to_e9=(((anchor-prev_anchor)&1023)-((anchor-origin)&1023))*MS+prev[4]*ARM_TICK
            prev_ack_to_input=ack_gap-(input_age-ack_age)*ARM_TICK
            shape=[row[k] for k in FIELDS]
            assert shape==by_tick.setdefault(key,shape)
            out[key]=dict(generation=row['generation'],workload=dict(zip(FIELDS,shape)),
                          input_to_E9_ms=row['input_to_first_E9_ms_bounds'],
                          first_E9_to_last_OBJ_ms=row['E9_to_last_publish_ms'],
                          last_OBJ_to_ARM_ACK_ms_bounds=tail,
                          input_to_first_valid_ACK_ms=row['input_to_final_ACK_ms'],
                          previous_to_current_ARM_ACK_ms_bounds=bounds(ack_gap,MS+(probe+2)*ARM_TICK,
                                                                      MS+(prev[5]+2)*ARM_TICK),
                          previous_ACK_to_first_E9_ms=bounds(prev_ack_to_e9,MS,MS+(prev[5]+2)*ARM_TICK),
                          previous_ACK_to_input_ms=bounds(prev_ack_to_input,MS+(probe+2)*ARM_TICK,
                                                          MS+(prev[5]+2)*ARM_TICK),
                          DMA_start=None,DMA_last_byte=None,display_VBlank=None)
        assert set(out)==set(TICKS)
        output[edition]=dict(source_sha256=sha(path),frames=out,OBJ_rows=len(tails),
                             median_tail_bounds_ms=[round(median(x[i] for x in tails),3) for i in (0,1)])
    refs={}
    for ed,fn in ((901,read_trace),(903,tile903)):
        trace=folder/f'nes-frame-mmc{ed}.bin'
        rows=fn(trace)['rows']
        refs[ed]={}
        for tick,shape in by_tick.items():
            candidates=[r for r in rows if not r.get('invalid') and abs(r['tick']-tick)<=30 and
                        all(r[k]==v for k,v in zip(FIELDS[:3],shape[:3]))]
            refs[ed][tick]=min(candidates,key=lambda r:abs(r['tick']-tick)) if candidates else None
    return dict(runs=output,older_independent_runs=refs)


def linked_run(path,fw):
    j=json.loads((path/'joint.json').read_bytes())
    summary=json.loads((path/'verified905.json').read_bytes())
    assert j['firmware_SHA256']==fw and j['passed'] and j['last_status']==1 and j['commits']==summary['RGB']==8
    jobs=[json.loads(l) for l in (path/'producer.jsonl').read_text().splitlines()]
    events=json.loads((path/'events.json').read_bytes())
    packets=[bytes.fromhex(json.loads(l)[2]) for l in (path/'packets.jsonl').read_text().splitlines()]
    with (path/'window.csv').open() as stream:window=list(csv.DictReader(stream))
    frames={}
    for f in j['frames']:
        g=f['generation']
        if g==905:continue  # The PPU monitor arms its last-byte hook at the first reveal.
        obj=[r for r in jobs if r['generation']==g and r['kind']==1]
        if not obj:continue
        w=[r for r in window if int(r['g'])==g and r['op']=='3']
        seal,=[r for r in w if r['event']=='load']
        dma=[r for r in w if r['event']=='ppu_dma']
        end=[r for r in w if r['event']=='ppu_last']
        show,=[r for r in w if r['event']=='reveal']
        ack,=[r for r in w if r['event']=='ack']
        assert len(dma)==len(end) and f['ACK_masterclock']==int(ack['clock'])
        cmd,=[p for p in packets if p[0]==3 and int.from_bytes(p[8:10],'little')==g]
        identity=(bytes([1,3])+cmd[2:10]+bytes([0x65,0x9a])).hex()
        valid=next(e for e in events if e['generation']==g and e.get('opcode')=='0xe0'
                   and e['clock']>=int(ack['clock']) and e.get('reply','')[14:38]==identity)
        rx=bytes.fromhex(valid['reply'])
        crc=0
        for byte in rx[1:19]:
            crc^=byte
            for _ in range(8):crc=((crc<<1)^7 if crc&128 else crc<<1)&255
        assert rx[1]==0xf7 and rx[2] in (2,10) and rx[3:5]==rx[5:7] and crc==rx[19]
        assert all(int(a['clock'])<=int(b['clock']) for a,b in zip(dma,end))
        times=dict(last_OBJ=obj[-1]['producer'],SEAL=int(seal['clock']),DMA_start=int(dma[0]['clock']),
                   DMA_end=int(end[-1]['clock']),show=int(show['clock']),ACK=int(ack['clock']),
                   E0_response=round(valid['clock']))
        assert list(times.values())==sorted(times.values())
        writes=[r for r in packets if int.from_bytes(r[8:10],'little')==g and r[1]==5 and r[0] in (2,4,5)]
        section=bytearray(3418)
        coverage=bytearray(3418)
        for packet in writes:
            at=int.from_bytes(packet[10:12],'little')
            data=packet[16:]
            if packet[0] in (4,5):
                size=int.from_bytes(packet[14:16],'little')
                assert len(data)==2 and size%2==0
                data=data*(size//2)
            assert at+len(data)<=len(section)
            section[at:at+len(data)]=data
            coverage[at:at+len(data)]=b'\x01'*len(data)
        wait=next((r for r in w if r['event']=='wait169' and times['SEAL']<=int(r['clock'])<times['DMA_start']),None)
        frames[g]=dict(masterclocks=times,VBlank=[int(r['frame']) for r in (seal,dma[0],end[-1],show,ack)],
                       scanlines=[int(r['line']) for r in (seal,dma[0],end[-1],show,ack)],
                       VBlank_wait_start=int(wait['clock']) if wait else None,
                       DMA_bytes_after_SEAL=sum(int(r['value']) for r in dma),
                       section5_hash=sha256(section+coverage).hexdigest(),section5_heads=len(writes))
    return dict(firmware=fw,client=j['client_SHA256'],parameters=j['parameters'],
                RGB=summary['RGB'],intervals=summary['intervals'][1],
                final_ACK=summary['final_ACK'][1],ARM_instructions=j['ARM_instructions'],frames=frames,
                clocks_per_second=MASTER,wire=j['wire_B'])


def scan_check(folder):
    # Invoke both linked Cortex-M4 routines on recorded output payloads and
    # deliberate runs crossing the 64-byte, 240-byte and 4 KiB boundaries.
    sims=[Machine(w/'link/src',bytes(2048)) for w in (BASE,WORK)]
    encoded=[bytes.fromhex(json.loads(l)[2])[16:] for l in (folder/'packets.jsonl').read_text().splitlines()]
    observed=sorted(set(v for v in encoded if v))
    cases=[bytes((i*73+5)&255 for i in range(k))+b'AZ'*(r//2)+b'!'*(r%2)
           for k in (0,1,2,37,238,239,240,241) for r in (62,63,64,65,66,512,4096)]
    counts=[0,0]
    for i,payload in enumerate(observed+cases):
        answers=[]
        for j,m in enumerate(sims):
            ptr=0x20012000
            m.u.mem_write(ptr,payload)
            start=m.instructions
            answers.append(m.call('span_piece',[ptr,len(payload)]))
            if i<len(observed):counts[j]+=m.instructions-start
        assert answers[0]==answers[1],(i,answers)
    return dict(unique_recorded=len(observed),directed=len(cases),unweighted_recorded_instructions=counts)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('logs',type=Path)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    result=measurements(a.logs)
    result['guards']={}
    for name,w in [('linear',WORK),('early_E0',ACK_WORK),('three_fills',FILL_WORK)]:
        proof=w/'proof'
        fw=w/'link/src/obj-nes-100/firmware.stm'
        sram=json.loads((proof/'sram.json').read_bytes())['cases']
        assert len(sram['normal']['d0_sites'])==4 and sram['normal']['checked_retire'] and not sram['bad-crc']['checked_retire']
        for file,key in [('timer.json','firmware'),('loader.json','firmware'),('menu.json','firmware'),('base/result.json','firmware_sha256')]:
            assert json.loads((proof/file).read_bytes())[key]==sha(fw)
        assert json.loads((proof/'timer.json').read_bytes())['passed']
        assert json.loads((proof/'menu.json').read_bytes())['rows']['normal']['released']
        assert json.loads((proof/'base/result.json').read_bytes())['safe_return']
        result['guards'][name]=dict(firmware=sha(fw),flash_B=fw.stat().st_size,SRAM_D0=4,
                                     sram_test=sha(proof/'sram.json'),safe_return=True)
    result['linked']={}
    for phase in (1,2):
        for state in ('warm','cold'):
            prefix=f'nes-tile821-obj-jointmirror-p{phase}-'
            group={}
            for name,tag,w in [('reference','907',BASE),('linear','908-linear',WORK),('early_E0','908-ack',ACK_WORK),
                               ('three_fills','908-fill',FILL_WORK)]:
                path=a.temp/(prefix+f'{tag}-{state}-pair')
                group[name]=linked_run(path,sha(w/'link/src/obj-nes-100/firmware.stm'))
                if name!='reference':
                    assert group[name]['parameters']==group['reference']['parameters']
                    assert group[name]['client']==group['reference']['client']
                    for g in range(905,913):
                        ref=a.temp/(prefix+f'907-{state}-pair')
                        assert sha(path/f'frame-{g}.rgb')==sha(ref/f'frame-{g}.rgb')
                    for g,r in group[name]['frames'].items():
                        assert r['section5_hash']==group['reference']['frames'][g]['section5_hash']
            for r in group.values():
                # Full timelines remain in the run directory. Keep the focal
                # late replay frame and the sequence of render deadlines here.
                r['display_VBlanks']=[f['VBlank'][3] for f in r['frames'].values()]
                r['last_frame']=r.pop('frames')[912]
            result['linked'][f'p{phase}-{state}']=group
    result['span_piece']=scan_check(a.temp/'nes-tile821-obj-jointmirror-p1-907-warm-pair')
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
