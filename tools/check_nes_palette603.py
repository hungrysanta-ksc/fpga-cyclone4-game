"""Attribute matched 952/954 SPI bodies and test current-input CGRAM reconstruction before its consumer deadline."""
import argparse
import binascii
from collections import defaultdict
import json
import math
from nes_transfer512 import input_packets
from pathlib import Path
import re
import struct

from analyze_nes_body581 import output_decode
from analyze_nes_wire600 import MASTER, ms, first_visible_switch
from check_nes_wire600 import ROOT, pin, pin_packets, read, sha
from nes_palette603_cpu import simulate


def indices(blocks,g):
    colors=bytearray()
    final=None
    for i,b in enumerate(blocks):
        assert b[:3]==b'\x51'+g.to_bytes(2,'big')
        at=3
        while at<len(b):
            key=int.from_bytes(b[at:at+2],'big')
            kind,k=divmod(key,8192)
            n=8 if kind==0 and k&4096 else (2,1,7,4,7,1,2,8)[kind]
            data=b[at+2:at+2+n];assert len(data)==n
            if kind==5:
                assert k==len(colors)
                colors.extend(data);final=i
            elif kind==7 and k&0x1800==0x1800 and (k>>8)&7==5:
                length=(k&255)+1;assert length<=8
                colors.extend(data[-length:]);final=i
            at+=2+n
    assert len(colors) in (32,64) and max(colors)<64
    return bytes(colors),final


def row_candidate(blocks,g,rows):
    # Price one new kind-6 tag class of the same width; the outer version discriminates it.
    # All other records and the shared-generation seal thresholds are from 600.
    generation=g.to_bytes(2,'big')
    records=[];old_rows=bytearray();row_record_positions=[]
    for b in blocks:
        assert b[:3]==b'\x51'+generation
        at=3
        while at<len(b):
            key=int.from_bytes(b[at:at+2],'big')
            k,idx=divmod(key,8192)
            n=8 if k==0 and idx&4096 else (2,1,7,4,7,1,2,8)[k]
            rec=b[at:at+2+n];at+=len(rec)
            assert not(k==6 and idx&0x1f00==0x1e00)
            if k==7 and idx&0x1f00==0x1900:
                size=(idx&255)+1
                assert size<=8
                old_rows+=rec[-size:];row_record_positions.append(len(records))
            records.append(rec)
    assert bytes(old_rows)==rows
    assert row_record_positions==list(range(row_record_positions[0],row_record_positions[-1]+1))
    starts=[i for i,v in enumerate(rows) if i==0 or v!=rows[i-1]+1]
    runs=[struct.pack('>HH',0xde00+end-i-1,rows[i]) for i,end in zip(starts,starts[1:]+[len(rows)])]
    restored=bytearray()
    for r in runs:
        tag,first=struct.unpack('>HH',r)
        count=(tag&255)+1
        assert first+count<=256 and len(restored)+count<=len(rows)
        restored.extend(range(first,first+count))
    assert bytes(restored)==rows
    def sizes(rs):
        result=[];size=3
        for r in rs:
            tag=int.from_bytes(r[:2],'big')
            if tag in (0xe001,0xe002) and size>3:result.append(size);size=3
            size+=len(r)
            if size>246 or 0xe000<tag<0xe800:
                assert size<=256;result.append(size);size=3
        assert size==3
        return result
    old=sizes(records);assert old==list(map(len,blocks))
    a,b=row_record_positions[0],row_record_positions[-1]+1
    literal=sum(map(len,records[a:b]))
    new=sizes(records[:a]+(runs if len(runs)*4<literal else records[a:b])+records[b:])
    drop=len(old)-len(new)
    # Each removed block avoids its D1 command+CRC and the short POP and post-retire status.
    return dict(old_record_B=literal,run_B=len(runs)*4,old_blocks=len(old),new_blocks=len(new),
                projected_saved_B=sum(old)-sum(new)+drop*(3+4+8))


def recipe(colors,raw,lut,canonical):
    assert len(colors) in (32,64) and max(colors)<64
    assert len(colors)==32 or colors[0]==colors[32]
    words=struct.unpack('<64H',lut)
    target=[0]*256
    for e in range(len(colors)//32):
        for i in range(16):
            target[e*16+i]=words[colors[e*32+i]]
            target[128+64*e+16*(i//4)+i%4]=words[colors[e*32+16+i]]
    if raw:target[64:128]=words
    expanded=struct.pack('<256H',*target)
    assert canonical==expanded
    return bytes([(len(colors)==64)+2*bool(raw)])+struct.pack('<H',binascii.crc_hqx(canonical,65535))+colors


def main(a):
    a.out=a.out.resolve();a.out.mkdir(exist_ok=False,parents=True)
    def evidence(stem):return read(ROOT/'analysis'/(stem+'-verification.json'))
    body=evidence('body581');base=evidence('overlap602');old=evidence('wire600')
    phases=evidence('whole580')['phases']
    manifest=read(ROOT/'analysis/whole580-manifest.json')
    source=a.arm/'src/nes_palette165.inc'
    pin(source,manifest['ARM_project_files']['src/'+source.name]['sha256'])
    lut=struct.pack('<64H',*map(int,re.search(r'\{(.+?)\}',source.read_text())[1].split(',')))
    result=dict(stage=603,physical=False,new_final_ACK=None,LUT_sha256=sha(source),frames=[],phases=[],guards={})
    recipes={}
    for g in range(905,958):
        frame=body['frames'][str(g)]
        f=a.data/f'frame{g}.geometry';pin(f,body['inputs'][f.name])
        geom=f.read_bytes();n=struct.unpack_from('<H',geom,5738)[0]
        ids=geom[5664:5664+n]
        canonical=a.capture/f'frame{g}/expected-cgram.bin'
        pin(canonical,body['inputs'][f'capture/frame{g}/expected-cgram.bin'])
        raw=frame['phases']['1']['patch_count']
        r=recipe(ids,raw,lut,canonical.read_bytes())
        # Prospective row codec: no history, exact row start and number of successive values.
        values=geom[2112:2112+int.from_bytes(geom[5730:5732],'little')]
        starts=[i for i,v in enumerate(values) if i==0 or v!=values[i-1]+1]
        runs=[(values[i],end-i) for i,end in zip(starts,starts[1:]+[len(values)])]
        assert bytes(start+k for start,count in runs for k in range(count))==values
        result['frames'].append(dict(generation=g,colors=n,raw_slots=raw,recipe_B=len(r),row_unit_runs=len(runs)))
        rawfile=a.data/f'frame{g}.raw';pin(rawfile,body['inputs'][rawfile.name])
        blocks,_,_=input_packets(geom,rawfile.read_bytes(),g)
        result['frames'][-1]['row_candidate']=row_candidate(blocks,g,values)
        if g in (952,954):
            p=a.wire/'shared';pin(p/f'transactions-{g}.txt',old['receiver'][str(g)]['shared']['pins_sha256'])
            assert blocks==pin_packets(p,g)
            got,block=indices(blocks,g);assert got==ids
            recipes[g]=(r,canonical.read_bytes(),block)
    for phase in phases:
        i=phase['phase'];d=a.traces/f'nes-close561-run{i}'
        for filename in ('events.json','obj-phases.json','packets.jsonl'):
            pin(d/filename,phase['evidence'][filename])
        ev=read(d/'events.json');obj=read(d/'obj-phases.json')
        packets=defaultdict(list)
        for line in (d/'packets.jsonl').read_bytes().splitlines():
            _,_,h,_=json.loads(line);b=bytes.fromhex(h);packets[int.from_bytes(b[8:10],'little')].append(b)
        for g,(r,oracle,block) in recipes.items():
            f=body['frames'][str(g)]['phases'][str(i)]
            source=f['marks']['source_begin'];prev=obj[str(g-1)]['ea']
            assert prev==source
            events=[x for x in ev if x['generation']==g and x['event']=='SPI']
            d1=[x for x in events if x['opcode']=='0xd1']
            # Find the matching color record in the original per-record generation ABI.
            p=a.wire/'legacy';pin(p/f'transactions-{g}.txt',old['receiver'][str(g)]['legacy']['pins_sha256'])
            converted=[]
            for b in pin_packets(p,g):
                at=0;buf=bytearray(b'\x51'+g.to_bytes(2,'big'))
                while at<len(b):
                    key=int.from_bytes(b[at:at+2],'big');kind,k=divmod(key,8192)
                    n=8 if kind==0 and k&4096 else (2,1,7,4,7,1,2,8)[kind]
                    assert int.from_bytes(b[at+2:at+4],'big')==g
                    buf+=b[at:at+2]+b[at+4:at+4+n];at+=4+n
                converted.append(bytes(buf))
            ids,legacy_i=indices(converted,g);assert ids==r[3:] and len(d1)==len(converted)
            pstarts=[e for e in events if e['opcode']=='0xe1' ]
            pkts=packets[g];assert [e['bytes'] for e in pstarts]==[len(b)+3 for b in pkts]
            palette=[(b,e,t) for b,e,t in zip(pkts,pstarts,f['packets'],strict=True) if t['section']=='palette']
            data=bytearray()
            for b,e,t in palette:
                assert int.from_bytes(b[10:12],'little')==len(data)
                data+=output_decode(b)
            assert data==oracle
            start=palette[0][1]['start'];deadline=palette[-1][2]['SNES_ACK']
            # Begin at end of new wire, assuming first old CS can be reused and no queue delay.
            prior_wire=sum(e['bytes'] for _,e,_ in palette)
            wire_B=16+len(r)+3
            saved=prior_wire-wire_B
            arrival=math.ceil(start+ms(wire_B)*MASTER/1000)
            cpu=simulate(a.out/f'p{i}-{g}',a.mesen,lut,r,oracle,arrival)
            ref=next(row for row in base['phases'] if (row['phase'],row['generation'])==(i,g))
            bus=ref['optimistic_paired_bus_ms']-ms(saved)
            cal=next(row['relaxed_calendar'] for row in old['phases'] if (row['phase'],row['generation'])==(i,g))
            prev_reveal=cal['previous_reveal']
            e9=[x for x in events if x['opcode']=='0xe9']
            banks=obj[str(g)]['banks557']
            assert len(banks)==len(e9)
            assert all(abs(e['clock']-b['seal'])<1 and b['seal']<=b['first_check'] for e,b in zip(e9,banks))
            last_seal=f['marks']['SEAL_load']
            assert d1[legacy_i]['clock']<start<arrival<deadline<last_seal
            assert all(obj[str(g)]['ea']>x['clock']>prev for x in e9)
            result['phases'].append(dict(phase=i,generation=g,shared_D1_palette_last_block0=block,
                legacy_D1_color_end=d1[legacy_i]['clock'],previous_EA=prev,source_begin=source,
                pre_EA_shifted_B=0,baseline_D1_B=sum(x['bytes'] for x in d1),
                E1_section_B={k:v['wire_B'] for k,v in f['output'].items()},
                E9_issues=[dict(start=x['start'],end=x['clock'],wire_B=x['bytes'],plans=b['count'],first_check=b['first_check'],release=b['release']) for x,b in zip(e9,banks)],
                E9_body_B=sum(x['bytes']-8 for x in e9),first_tile_load=next(t['SNES_load'] for t in f['packets'] if t['op']==7),
                old_palette_B=prior_wire,new_palette_B=wire_B,saved_B=saved,wire_after_B=ref['wire_after_B']-saved,
                ppu_input_issue=start,optimistic_kernel_arrival=arrival,old_palette_ACK=deadline,old_SEAL_load=last_seal,
                old_final_ACK=f['marks']['final_ACK'],kernel=cpu,
                palette_ACK_overrun_ms=(cpu['verified']-deadline)*1000/MASTER,
                SEAL_load_overrun_ms=(cpu['verified']-last_seal)*1000/MASTER,
                wire_only_bus_ms=ref['wire_only_bus_ms']-ms(saved),paired_pre_display_bus_ms=bus,
                bus_only_VBlank_interval_ms=(first_visible_switch(prev_reveal+MASTER*bus/1000)-prev_reveal)*1000/MASTER))
    g=954;r,oracle,_=recipes[g]
    for fault in ('bad_length','reserved','bad_id','memory','stop'):
        payload=bytearray(r)
        if fault=='bad_length':payload.pop()
        if fault=='reserved':payload[0]|=4
        if fault=='bad_id':payload[3]=64
        result['guards'][fault]=simulate(a.out/fault,a.mesen,lut,payload,oracle,900000,fault)
    ids=bytes(range(32))+bytes([0])+bytes(range(33,64))
    # Independent layout oracle for two epochs with the raw window disabled.
    words=struct.unpack('<64H',lut);v=[0]*256
    for epoch in (0,1):
        base=32*epoch
        v[16*epoch:16*epoch+16]=[words[k] for k in ids[base:base+16]]
        for j in range(4):
            at=128+64*epoch+16*j
            v[at:at+4]=[words[k] for k in ids[base+16+j*4:base+20+j*4]]
    oracle=struct.pack('<256H',*v)
    r=recipe(ids,False,lut,oracle)
    result['two_epoch_no_raw']=simulate(a.out/'two-epoch',a.mesen,lut,r,oracle,900000)
    result['guards']['epoch_backdrop']=simulate(a.out/'backdrop',a.mesen,lut,r[:35]+bytes([1])+r[36:],oracle,900000,'backdrop')
    result['Mesen_sha256']=sha(a.mesen)
    a.report.write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print([(q['generation'],q['phase'],q['saved_B'],q['kernel']['total_clocks'],q['palette_ACK_overrun_ms']) for q in result['phases']])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('out','report','data','capture','traces','wire','arm','mesen'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
