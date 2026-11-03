# SPDX-License-Identifier: MIT
"""R2 reference wire budget, not product ABI or a cycle simulation.

Compare common section blocks with/without exact map+row base reuse and a
bank-stale 8B map mask. Charge identities, CRC, manifest and query scenarios.
"""
import argparse,binascii,hashlib,json,math,struct
from pathlib import Path
from check_nes_game478 import encode as arrays_from_geometry, next_y
from analyze_nes_body581 import output_decode

ROOT=Path(__file__).resolve().parents[1]
WIDTH=[2,1,7,4,7,1,1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def crc(b):return binascii.crc_hqx(b,65535)
def canonical(arrays):return b''.join(v.to_bytes(w,'little') for a,w in zip(arrays,WIDTH) for v in a)

def block(k,mode,at,values,base):
    n=len(values);w=WIDTH[k]
    if mode==0:body=b''.join(x.to_bytes(w,'little') for x in values)
    elif mode in (1,2):body=values[0].to_bytes(w,'little')
    elif mode==3:
        mask=sum((at+i>=len(base) or x!=base[at+i])<<i for i,x in enumerate(values))
        body=mask.to_bytes((n+7)//8,'little')+b''.join(x.to_bytes(w,'little') for i,x in enumerate(values) if mask>>i&1)
    else:raise AssertionError(mode)
    return struct.pack('<BBHH',k,mode,at,n)+body

def input_blocks(arrays,base):
    blocks=[]
    for k,a in enumerate(arrays):
        at=0
        while at<len(a):
            # map/row share fixed32-unit block semantics; remaining sections
            # retain repeated/raster runs and bounded full literal fallback.
            cap=min(32 if k in (0,1) else 224//WIDTH[k],len(a)-at)
            n=cap;mode=0
            if k in (0,1) and base is not None:
                literal=block(k,0,at,a[at:at+n],[])
                delta=block(k,3,at,a[at:at+n],base[k])
                blocks.append(delta if len(delta)<len(literal) else literal)
                at+=n;continue
            if k not in (0,1):
                repeat=1
                while repeat<min(256,len(a)-at) and a[at+repeat]==a[at]:repeat+=1
                raster=1
                if k==4:
                    while raster<min(256,len(a)-at) and a[at+raster]==next_y(a[at+raster-1]):raster+=1
                if max(repeat,raster)>=2:mode=1 if repeat>=raster else 2;n=max(repeat,raster)
                else:
                    n=1
                    while n<cap:
                        if at+n+1<len(a) and (a[at+n]==a[at+n+1] or (k==4 and a[at+n+1]==next_y(a[at+n]))):break
                        n+=1
            blocks.append(block(k,mode,at,a[at:at+n],[]));at+=n
    return blocks

def restore(blocks,counts,base):
    out=[[] for _ in counts]
    for b in blocks:
        k,mode,at,n=struct.unpack_from('<BBHH',b);assert k<7 and n and at==len(out[k]) and at+n<=counts[k]
        w=WIDTH[k];body=b[6:]
        if mode==0:
            assert len(body)==n*w;v=[int.from_bytes(body[i:i+w],'little') for i in range(0,len(body),w)]
        elif mode in (1,2):
            assert len(body)==w and (mode==1 or k==4);v=[int.from_bytes(body,'little')]
            for _ in range(n-1):v.append(v[0] if mode==1 else next_y(v[-1]))
        else:
            assert mode==3 and k in (0,1) and base is not None
            size=(n+7)//8;mask=int.from_bytes(body[:size],'little');assert mask>>n==0
            assert len(body)==size+mask.bit_count()*w;pos=size;v=[]
            for i in range(n):
                if mask>>i&1:v.append(int.from_bytes(body[pos:pos+w],'little'));pos+=w
                else:assert at+i<len(base[k]);v.append(base[k][at+i])
        out[k]+=v
    assert list(map(len,out))==counts
    return out

def input_packets(arrays,blocks,serial,base_serial):
    # 32B BEGIN: magic/ver/flags,epoch/serial/base,gen,6 counts,patches,reserved.
    begin=struct.pack('<HBBIIIH6HBB',0x582,1,int(base_serial!=0),1,serial,base_serial,904+serial,*map(len,arrays[:6]),len(arrays[6])//256,0)
    assert len(begin)==32
    geometry=canonical(arrays[:6]);full=canonical(arrays)
    meta=struct.pack('<HHHH',0xf004,len(geometry),sum(map(len,arrays[:6])),crc(geometry))
    end=struct.pack('<HHHH',0xf001,len(full),sum(map(len,arrays)),crc(full))
    commit=struct.pack('<HHI',0xf003,904+serial,serial)
    packets=[];p=bytearray(begin)
    for raw_part in (False,True):
        for b in blocks:
            if (b[0]==6)!=raw_part:continue
            if len(p)+len(b)>256:packets.append(bytes(p));p.clear()
            p+=b
        tail=end if raw_part else meta
        if len(p)+8>256:packets.append(bytes(p));p.clear()
        p+=tail;packets.append(bytes(p));p.clear()
    packets.append(commit)
    return packets

def map_records(current,previous,stale,cold):
    dirty={i for i in range(512) if current[i*8:i*8+8]!=previous[i*8:i*8+8]}
    for s in stale:s.update(dirty)
    groups=set(range(512)) if cold else stale[0] # caller puts target at index0
    masks=bytes(sum((row*8+i in groups)<<i for i in range(8)) for row in range(64))
    records=[bytes([row,mask])+b''.join(current[(row*8+i)*8:(row*8+i+1)*8] for i in range(8) if mask>>i&1) for row,mask in enumerate(masks) if mask]
    runs=sum(sum((mask>>i&1) and (i==0 or not(mask>>(i-1)&1)) for i in range(8)) for mask in masks)
    return records,masks,runs

def map_restore(old,records,masks,digest):
    out=bytearray(old);seen=set()
    assert len(masks)==64 and crc(b''.join(records))==digest
    for b in records:
        row,mask=b[:2];assert row<64 and row not in seen and mask and masks[row]==mask
        seen.add(row);assert len(b)==2+8*mask.bit_count();pos=2
        for i in range(8):
            if mask>>i&1:out[row*64+i*8:row*64+i*8+8]=b[pos:pos+8];pos+=8
    assert seen=={i for i,m in enumerate(masks) if m}
    return bytes(out)

def pack_records(records):
    packets=[];p=bytearray()
    for r in records:
        if len(p)+len(r)>240:packets.append(bytes(p));p.clear()
        p+=r
    if p:packets.append(bytes(p))
    return packets

def reuse_ranges(trace,expected_hash):
    assert sha(trace)==expected_hash
    histories=[{},{}];layouts=[None,None];frames={};group={}
    for line in trace.read_text().splitlines():
        _,_,h,_=json.loads(line);b=bytes.fromhex(h);g=int.from_bytes(b[8:10],'little');group.setdefault(g,[]).append(b)
    for g,packets in group.items():
        bank=int.from_bytes(packets[0][18:20],'little');layout=int.from_bytes(packets[-1][38:40],'little')
        if layouts[bank]!=layout:histories[bank][5]={}
        memory=histories[bank];omitted=[];saved=0;count=0
        for b in packets:
            if b[0] not in (2,4,5,8) or b[1]<3:continue
            k=b[1];at=int.from_bytes(b[10:12],'little');value=output_decode(b);m=memory.setdefault(k,{})
            if all(m.get(at+i)==x for i,x in enumerate(value)):
                saved+=len(b)+3;count+=1;omitted.append((k,at,value))
            for i,x in enumerate(value):m[at+i]=x
        ranges=[]
        for k,at,value in sorted(omitted):
            if ranges and ranges[-1][0]==k and ranges[-1][1]+len(ranges[-1][2])==at:
                old=ranges.pop();ranges.append((k,old[1],old[2]+value))
            else:ranges.append((k,at,value))
        #8B base serial/layout/count header +7B(section,start,len,CRC) each.
        #CRC lookup/checking of inherited ranges remains an unpriced gate.
        payload=8+7*len(ranges);assert payload<=240
        frames[g]=dict(omitted_packets=count,omitted_wire_B=saved,ranges=len(ranges),
            declaration_wire_B=payload+19 if ranges else 0,
            inherited_check_B=sum(len(v) for _,_,v in ranges))
        layouts[bank]=layout
    return frames

def main(a):
    a.out.mkdir(parents=True,exist_ok=False);prior=read(ROOT/'analysis/body581-verification.json')
    whole=read(ROOT/'analysis/whole580-verification.json')
    reuse={str(i):reuse_ranges(a.traces/f'nes-close561-run{i}/packets.jsonl',whole['phases'][i-1]['evidence']['packets.jsonl']) for i in (1,2)}
    events={}
    for i in (1,2):
        path=a.traces/f'nes-close561-run{i}/events.json'
        assert sha(path)==whole['phases'][i-1]['evidence']['events.json'];events[str(i)]=read(path)
    previous=None;last_map=bytes(4096);banks=[bytes(4096),bytes(4096)];stale=[set(range(512)),set(range(512))];frames=[]
    for serial,g in enumerate(range(905,958),1):
        gp=a.data/f'frame{g}.geometry';rp=a.data/f'frame{g}.raw'
        for p in (gp,rp):assert sha(p)==prior['inputs'][p.name]
        _,_,arrays=arrays_from_geometry(gp.read_bytes(),rp.read_bytes(),g);arrays+=[list(rp.read_bytes())]
        cases={}
        for label,base in [('full_blocks',None),('map_row_base',previous)]:
            blocks=input_blocks(arrays,base);assert restore(blocks,list(map(len,arrays)),base)==arrays
            packets=input_packets(arrays,blocks,serial,serial-1 if base is not None else 0)
            assert all(len(p)<=256 for p in packets)
            cases[label]=dict(body_B=sum(map(len,packets)),packets=len(packets),blocks=len(blocks),
                wire_with_one_D0_per_packet_B=sum(map(len,packets))+len(packets)*19+8,
                canonical_CRC_B=len(canonical(arrays)),mode_counts={str(mode):sum(b[1]==mode for b in blocks) for mode in range(4)})
        cases['map_row_base_reuse']=dict(cases['map_row_base'])
        mp=a.capture/f'frame{g}/expected-map.bin';assert sha(mp)==prior['inputs'][f'capture/frame{g}/{mp.name}']
        current=mp.read_bytes();bank=prior['frames'][str(g)]['phases']['1']['bank']
        rs,masks,runs=map_records(current,last_map,[stale[bank],stale[1-bank]],serial<=2)
        digest=crc(b''.join(rs));assert map_restore(banks[bank],rs,masks,digest)==current
        # 70B prelude: expected64 masks + actual-read CRC16 + previous bank serial.
        map_packets=pack_records(rs);map_wire=89+sum(len(p)+19 for p in map_packets)
        row=dict(generation=g,input=cases,map=dict(wire_B=map_wire,packets=1+len(map_packets),
            groups=sum(m.bit_count() for m in masks),rows=sum(bool(m) for m in masks),DMA_runs=runs,
            DMA_B=sum(m.bit_count()*8 for m in masks),manifest_B=70),phases={})
        for phase in ('1','2'):
            old=prior['frames'][str(g)]['phases'][phase];op=old['wire'];old_map=old['output']['map'];n_out=len(old['packets'])-old_map['packets']+row['map']['packets']
            row['phases'][phase]={}
            for label,c in cases.items():
                # Preserve nonmap output, E9/EA/observer and observed E8; no
                # free palette/raw reuse. E0 batching is only a sensitivity.
                base=sum(v for k,v in op.items() if k not in ('0xd0','0xd1','0xd2','0xd3','0xe0'))-old_map['wire_B']+map_wire+c['wire_with_one_D0_per_packet_B']
                out_count=n_out
                if label.endswith('_reuse'):
                    rr=reuse[phase][g];base+=rr['declaration_wire_B']-rr['omitted_wire_B']
                    out_count+=int(rr['ranges']>0)-rr['omitted_packets']
                lo=base+20*(math.ceil(out_count/4)+3);hi=base+op['0xe0']
                calls={'0xd0':c['packets'],'0xd1':c['packets'],'0xd2':c['packets'],'0xd3':1,
                    '0xe1':out_count,'0xe0':math.ceil(out_count/4)+3,'0xe8':op['0xe8']//20,
                    '0xe9':sum(e['generation']==g and e['event']=='SPI' and e['opcode']=='0xe9' for e in events[phase]),'0xea':1}
                extras=whole['phases'][int(phase)-1]['parameters']['driver_extra_us']
                driver_ms=sum(calls[k]*extras[k] for k in calls)/1000
                row['phases'][phase][label]=dict(E0_batched_scenario_B=lo,E0_observed_scenario_B=hi,
                    batched_wire_ms=lo*8/2625000*1000,observed_wire_ms=hi*8/2625000*1000,
                    batched_16ms_residual_ms=1000/60-lo*8/2625000*1000,
                    estimated_SPI_calls=sum(calls.values()),serial_driver_mean_ms=driver_ms,
                    serial_wire_plus_driver_mean_ms=lo*8/2625000*1000+driver_ms,
                    serial_IO_residual_ms=1000/60-lo*8/2625000*1000-driver_ms,
                    final_timing_ms=None,net_Flash_B=None,net_LE=None)
        row['reuse']={p:reuse[p][g] for p in ('1','2')}
        frames.append(row);previous=arrays;last_map=current;banks[bank]=current;stale[bank].clear()
    groups={}
    for name,items in [('cold_banks',frames[:2]),('initialized',frames[2:]),('dense',frames[46:51])]:
        groups[name]=dict(n=len(items),map={k:sum(f['map'][k] for f in items)/len(items) for k in ['wire_B','groups','rows','DMA_runs','DMA_B']},cases={})
        for label in cases:
            groups[name]['cases'][label]=dict(input_wire_B=sum(f['input'][label]['wire_with_one_D0_per_packet_B'] for f in items)/len(items),
                phases={p:{k:sum(f['phases'][p][label][k] for f in items)/len(items) for k in ['E0_batched_scenario_B','E0_observed_scenario_B','batched_wire_ms','observed_wire_ms','batched_16ms_residual_ms','estimated_SPI_calls','serial_driver_mean_ms','serial_wire_plus_driver_mean_ms','serial_IO_residual_ms']} for p in ('1','2')})
            for p in ('1','2'):
                values=[f['phases'][p][label] for f in items]
                groups[name]['cases'][label]['phases'][p].update(max_wire_ms=max(x['batched_wire_ms'] for x in values),
                    wire_over_12ms=sum(x['batched_wire_ms']>12 for x in values),
                    serial_IO_over_60Hz=sum(x['serial_wire_plus_driver_mean_ms']>1000/60 for x in values))
    result=dict(stage=582,passed=True,product_implemented=False,R3_selected=False,frames=frames,groups=groups,
        evidence=dict(body581_sha256=sha(ROOT/'analysis/body581-verification.json'),tool_sha256=sha(Path(__file__))),
        scope='Reference codecs and byte budget; full fallback/base/mask reconstruction only. No physical/ARM/RTL/65816 cycle or safety proof.',
        unpriced=['Actual ARM section restore/semantic checks/full canonical CRC and finer map planning',
            'NES base/scratch RAM arbitration and96-bit mailbox chunk control',
            '65816 mask/CRC/coverage checks, retained-base integrity, DMA setup, prelude readiness and VBlank',
            'Additional retry/IRQ/ROM/STOP service and IO gaps; E0 batching is hypothetical'])
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(groups,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('data','capture','traces','out'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
