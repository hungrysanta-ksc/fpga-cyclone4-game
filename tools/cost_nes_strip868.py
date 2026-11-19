"""Audit the producer and replay-time budget for the fixed 23-row receiver."""
import argparse
import csv
import hashlib
import json
import statistics
import struct
import sys
from collections import defaultdict
from pathlib import Path

from probe_nes_map868 import CLOCK, SPAN, phase_cases

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'.tools/arm259-python'))
from probe_nes_supply671 import GCC, KernelARM, run
from elftools.elf.elffile import ELFFile


def producer(work, cases, folder):
    work.mkdir(parents=True,exist_ok=False)
    (work/'layout.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) } }')
    run([GCC/'arm-none-eabi-gcc.exe','-mcpu=cortex-m4','-mthumb','-Os','-nostdlib',
         '-fstack-usage','-Wall','-Werror','-Wl,-T,layout.ld',ROOT/'tools/nes_strip868.c',
         '-o','producer.elf'],work,'build')
    with (work/'producer.elf').open('rb') as f:
        symbols=ELFFile(f).get_section_by_name('.symtab')
        size={name:symbols.get_symbol_by_name(name)[0]['st_size']
              for name in ('pack_strip868','pack_published868')}
    cpu=KernelARM(work/'producer.elf')
    def measure(case, compact, extra=None):
        addr=[0x20001000,0x20002000,0x20003000,0x20004000]
        for at,key in zip(addr,('old','peer','goal')):
            values=bytearray.fromhex(case[key])
            if extra is not None and key=='goal':
                values[extra]^=1
            cpu.uc.mem_write(at,bytes(values))
        cpu.uc.mem_write(0x20000100,struct.pack('<IIIIIH',*addr,case['g']-2,case['page']))
        if compact:
            g=case['g']
            hist=pack_history([(folder/f'map-{j}.bin').read_bytes() for j in (g-2,g-1)])
            assert hist is not None
            cpu.uc.mem_write(0x20005000,hist)
        before=cpu.instructions
        length=cpu.call('pack_published868' if compact else 'pack_strip868',[0x20000100,0x20005000])
        if extra is None:
            assert length==len(case['data'])//2
            assert cpu.uc.mem_read(addr[-1],length).hex()==case['data']
        else:
            assert length==0
        return cpu.instructions-before
    times={name:[measure(c,compact) for c in cases] for compact,name in ((False,'raw'),(True,'packed'))}
    for compact in (False,True):
        assert measure(cases[0],compact,SPAN-2)>0
    return size,times


def calibrated_wire(events):
    groups=defaultdict(list)
    for e in events:
        if e.get('opcode')=='0xe1':
            groups[e['bytes']].append(e['clock']-e['start'])
    x1,x2=min(groups),max(groups)
    m1,m2=statistics.median(groups[x1]),statistics.median(groups[x2])
    slope=(m2-m1)/(x2-x1)
    intercept=m1-x1*slope
    error=max(abs(t-(intercept+n*slope)) for n,times in groups.items() for t in times)
    return slope,intercept,error


def issue_deadlines(folder, events, records, instructions, slope, fixed):
    """Latest producer start that could still return the old group's last credit.

    Give the new packet uncontested SPI and immediate CPU service. Record when
    the original first and last map transfers started, without assuming the
    full page was stable at the first start.
    """
    spi=[e for e in events if e.get('opcode')=='0xe1']
    spans=defaultdict(list)
    with (folder/'window.csv').open() as f:
        ack={int(r['index']):int(r['clock']) for r in csv.DictReader(f) if r['event']=='ack'}
    for i,(line,e) in enumerate(zip((folder/'packets.jsonl').read_text().splitlines(),spi,strict=True),1):
        raw=bytes.fromhex(json.loads(line)[2])
        if raw[0] not in (2,4) or raw[1]!=2:
            continue
        at=int.from_bytes(raw[10:12],'little')
        size=len(raw)-16 if raw[0]==2 else int.from_bytes(raw[14:16],'little')
        spans[int.from_bytes(raw[8:10],'little')].append((at,size,e['start'],ack[i]))
    result=[]
    for r,count in zip(records,instructions,strict=True):
        group=[p for p in spans[r['g']] if p[0]>=r['page'] and p[0]+p[1]<=r['page']+SPAN]
        assert len(group)==r['old_packets']
        latest=max(p[3] for p in group)-r['new_service']-slope*r['new_wire']-fixed-count*2*CLOCK/84000000
        result.append(dict(g=r['g'],first_issue_slack_ms=round((latest-min(p[2] for p in group))*1000/CLOCK,4),
                           last_issue_slack_ms=round((latest-max(p[2] for p in group))*1000/CLOCK,4)))
    return result


def pack_history(maps, capacity=1368):
    # Two physical banks, two 23-row pages each. The six-byte header stores
    # the palette count, column count and a 23-bit mask of repeated rows.
    columns=[tuple(m[i:i+2] for i in range(page+col,page+col+SPAN,64))
             for m in maps for page in (0,2048) for col in range(0,64,2)]
    repeated=sum(1<<i for i in range(1,23) if all(c[i]==c[i-1] for c in columns))
    reduced=[tuple(w for i,w in enumerate(c) if not repeated>>i&1) for c in columns]
    dictionary=list(dict.fromkeys(reduced))
    palette=list(dict.fromkeys(w for c in dictionary for w in c))
    if len(palette)>255 or len(dictionary)>255:
        return None
    data=(struct.pack('<BBI',len(palette),len(dictionary),repeated)+b''.join(palette)
          + bytes(dictionary.index(c) for c in reduced)
          + bytes(palette.index(w) for c in dictionary for w in c))
    return data if len(data)<=capacity else None


def verify_history(folder):
    sizes=[]
    for g in range(906,967):
        maps=[(folder/f'map-{j}.bin').read_bytes() for j in (g-1,g)]
        data=pack_history(maps)
        assert data is not None
        colors,n,mask=struct.unpack_from('<BBI',data)
        lut=6+2*colors
        width=23-mask.bit_count()
        assert len(data)==lut+128+n*width
        for idx in range(128):
            item=data[lut+idx]
            assert item<n
            for row in range(23):
                entry=row-(mask & ((1<<(row+1))-1)).bit_count()
                color=data[lut+128+item*width+entry]
                offset=(idx//32%2)*2048+row*64+2*(idx%32)
                assert color<colors and data[6+2*color:8+2*color]==maps[idx//64][offset:offset+2]
        assert pack_history(maps,len(data)-1) is None
        sizes.append(len(data))
    return dict(pairs=len(sizes),minimum=min(sizes),maximum=max(sizes),capacity=1368)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('temp','work','measure','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    measured=json.loads(a.measure.read_bytes())
    cases,_=phase_cases(a.temp/'nes-tile821-demo-jointmirror-p1-866-on',True)
    size,counts=producer(a.work,cases,a.temp/'nes-tile821-demo-jointmirror-p1-866-on')
    instructions=counts['packed']
    output=dict(ARM_text=size,producer_guard='nonadjacent change in last row falls back',ARM_instructions=counts,phases=[])
    for n,phase in enumerate(measured['phases'],1):
        folder=a.temp/f'nes-tile821-demo-jointmirror-p{n}-866-on'
        events=json.loads((folder/'events.json').read_bytes())
        m,b,error=calibrated_wire(events)
        assert error<2
        inputs=phase['frames']
        assert [r['g'] for r in inputs]==[c['g'] for c in cases]
        wire_saved=[(r['old_wire']-r['new_wire'])*m+(r['old_packets']-1)*b for r in inputs]
        service_extra=[r['new_service']-r['old_service'] for r in inputs]
        deadlines=issue_deadlines(folder,events,inputs,instructions,m,b)
        pins={name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
              for name in ('joint.json','window.csv','events.json','packets.jsonl')}
        output['phases'].append(dict(phase=n,E1_masterclocks_per_byte=m,E1_fixed_masterclocks=b,
            E1_max_residual_clocks=error,eligible=len(inputs),
            SHA256=pins, deadlines=deadlines,
            packed_history=verify_history(folder),
            wire_saving_ms=sum(wire_saved)*1000/CLOCK,
            receiver_extra_ms=sum(service_extra)*1000/CLOCK,
            serial_components_net_ms=sum((w-s)*1000/CLOCK-i*2/84000
                                         for w,s,i in zip(wire_saved,service_extra,instructions))))
    a.out.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
