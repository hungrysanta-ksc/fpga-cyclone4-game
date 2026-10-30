# SPDX-License-Identifier: MIT
"""Reconcile actual-M4 serializer packets; compare bounded scan and codec model.

Raw-CHR six-plane packing below is a lossless design probe, not a deployed ABI.
Physical485 logs do not contain section data and cannot replay these snapshots.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import random
from check_nes_game478 import sha


def pack6(raw,count):
    assert len(raw)==2048 and 1<=count<=7
    result=bytearray()
    for tile in range(32):
        for plane in range(3):
            at=tile*64+plane*16
            assert raw[at+2*count:at+16]==bytes(16-2*count)
            result+=raw[at:at+2*count]
        assert raw[tile*64+48:tile*64+64]==b'\xff\0'*count+bytes(16-2*count)
    return bytes(result)


def unpack6(data,count):
    assert 1<=count<=7 and len(data)==192*count
    raw=bytearray(2048);offset=0
    for tile in range(32):
        for plane in range(3):
            at=tile*64+plane*16;raw[at:at+2*count]=data[offset:offset+2*count];offset+=2*count
        raw[tile*64+48:tile*64+48+2*count]=b'\xff\0'*count
    return bytes(raw)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['baseline','candidate','arm','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();base=json.loads((a.baseline/'result.json').read_text());new=json.loads((a.candidate/'result.json').read_text())
    assert base['passed'] and new['passed'] and base['inputs']==new['inputs'] and base['full_state_and_plans_match'] and new['full_state_and_plans_match']
    rows=[];prior=[{},{}];categories=[(0,1121,'scroll_and_pad'),(1121,3169,'raw_CHR'),(3169,3418,'mode_enable_lengths')]
    for x,y in zip(base['frames'],new['frames']):
        assert x['frame']==y['frame'] and x['payload_SHA256']==y['payload_SHA256']
        d=a.baseline/f"frame{x['frame']}";packets=[q.read_bytes() for q in sorted(d.glob('packet*.bin'))]
        assert len(packets)==x['packet_count'] and all(p==q.read_bytes() for p,q in zip(packets,sorted((a.candidate/d.name).glob('packet*.bin'))))
        image=bytearray(3418);subbody=Counter();subpackets=Counter()
        for packet in packets:
            op,k=packet[:2];body=packet[16:];offset,n=struct.unpack_from('<HxxH',packet,10)
            if op==3:descriptor=body;continue
            if k!=5:continue
            data=body if op==2 else body*(n//len(body));image[offset:offset+len(data)]=data
            for first,last,label in categories:
                if first<=offset<last:
                    assert offset+len(data)<=last
                    subbody[label]+=len(body);subpackets[label]+=1;break
        count=int.from_bytes(descriptor[22:24],'little');assert count
        raw=bytes(image[1121:3169]);compact=pack6(raw,count);assert unpack6(compact,count)==raw
        equal={label:prior[x['bank']].get(label)==bytes(image[first:last]) for first,last,label in categories}
        prior[x['bank']]={label:bytes(image[first:last]) for first,last,label in categories}
        # Projection uses existing240B literal packet limit/19B E1 framing.
        oldwire=subbody['raw_CHR']+19*subpackets['raw_CHR'];newwire=len(compact)+19*((len(compact)+239)//240)
        rows.append({'frame':x['frame'],'bank':x['bank'],'raw_rows':count,'HDMA_subsection_body_B':dict(subbody),
                     'HDMA_subsection_packets':dict(subpackets),'equal_to_prior_destination':equal,
                     'raw_compact_model_B':len(compact),'raw_wire_model_saved_B':oldwire-newwire,
                     'target_serializer_instructions_before':x['target_instructions'],'target_serializer_instructions_after':y['target_instructions']})
    assert len(rows)==len(base['frames'])==len(new['frames'])==71
    # Reject implicit-bit violations and malformed sizes; never silently truncate.
    negatives=0
    for mode in range(4):
        try:
            if mode==0:pack6(raw,8)
            elif mode==1:unpack6(compact[:-1],count)
            elif mode==2:
                bad=bytearray(raw);bad[48]^=1;pack6(bad,count)
            else:
                bad=bytearray(raw);bad[2*count]^=1;pack6(bad,count)
        except AssertionError:negatives+=1
    assert negatives==4
    rng=random.Random(487)
    for n in range(1,8):
        raw_test=bytearray(2048)
        for tile in range(32):
            for plane in range(3):
                at=tile*64+plane*16;raw_test[at:at+2*n]=bytes(rng.randrange(256) for _ in range(2*n))
            raw_test[tile*64+48:tile*64+48+2*n]=b'\xff\0'*n
        assert unpack6(pack6(raw_test,n),n)==raw_test
    guards=json.loads((a.arm.parent/'../guards01/result.json').resolve().read_text())
    assert guards['passed'] and guards['firmware_SHA256']==new['firmware_SHA256'] and len(guards['rows'])==12
    size_line=(a.arm.parent/'size.log').read_text().splitlines()[-1].split()
    text,data,bss=map(int,size_line[:3]);firmware=(a.arm/'obj-nes-100/firmware.stm').stat().st_size
    assert (text,data,bss)==(202729,10040,18572) and firmware==212772
    section_totals={key:dict(sum((Counter(x[key]) for x in base['frames']),Counter())) for key in ['section_packets','section_body_B','section_expanded_B']}
    before=sum(x['target_serializer_instructions_before'] for x in rows);after=sum(x['target_serializer_instructions_after'] for x in rows)
    result={'passed':True,'scope':__doc__,'merged_PR136':'2d4543ef2442bc798bcec128a4a108fdfc4d5287','branch':'codex/nes-output-budget-487',
            'baseline_firmware_SHA256':base['firmware_SHA256'],'candidate_firmware_SHA256':new['firmware_SHA256'],
            'candidate_ELF_SHA256':sha(a.arm/'obj-nes-100/sd2snes.elf'),'baseline_result_SHA256':sha(a.baseline/'result.json'),
            'candidate_result_SHA256':sha(a.candidate/'result.json'),'input_SHA256':base['inputs'],
            'actual_M4_state_plans_packets_equal_71':True,'independently_expanded_tables_equal':True,
            'sections':section_totals,'changed_map_granules':sum(x['changed_map_granules'] for x in base['frames']),
            'uploaded_map_granules':sum(x['upload_map_granules'] for x in base['frames']),
            'serializer_instructions':{'before':before,'after':after,'saved':before-after,'saved_fraction':1-after/before,'not_hardware_cycles':True},
            'ARM_candidate':{'text':text,'data':data,'BSS':bss,'firmware_B':firmware,'Flash_tail':212992-firmware,'new_state_B':0,'new_buffer_B':0},
            'ownership_guard_cases':guards['rows'],'guard_result_SHA256':sha((a.arm.parent/'../guards01/result.json').resolve()),
            'compact_raw_model':{'lossless_snapshots':len(rows),'synthetic_row_counts':list(range(1,8)),'rejected_malformed_cases':negatives,'ABI_implemented':False,
                                 'total_wire_saved_B':sum(x['raw_wire_model_saved_B'] for x in rows),'ARM_SNES_extra_cost':None,
                                 'independent_validation_and_STOP_implementation':False},
            'frames':rows,'FPGA_changed':False,'new_Quartus':False,'new_package':False,'hardware_time_FPS_improvement_proven':False,
            'limits':['Historical71 captures, not494 physical gameplay frames; no section-attribution from physical logs',
                      'ACK endpoint modeled; no window CRC/E0/IRQ/ROM or actual65816 timing in target serializer counts',
                      'Byte-equivalent scan candidate does not reduce wire volume; no counters-only hardware delivery',
                      'Reuse requires ownership/independent coverage changes; byte equality alone is not permission to omit data',
                      'Compact raw model needs real ARM/FPGA/SNES ABI, budget and STOP/finalACK validation before adoption']}
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'passed':True,'instructions':result['serializer_instructions'],'sections':section_totals['section_body_B'],'raw_model_saved_B':result['compact_raw_model']['total_wire_saved_B']}))
