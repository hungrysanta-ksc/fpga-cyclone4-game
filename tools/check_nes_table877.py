"""Compare full ARM links on identical inputs and check END against actual reveal."""
import argparse
import json
from pathlib import Path

from analyze_nes_credit876 import timeline, verified_commits
from analyze_nes_deadline875 import analyze, points
from analyze_nes_map830 import load, packets, window
from check_nes_strip869 import digest


def beam_marks(folder):
    return [(e['event'],e['clock']) for e in window(folder) if
            (e['g']==951 and e['event']=='reveal') or
            (e['g']==952 and (e['event']=='upload165_entry' or e['event']=='load' and e['op']==3))]


def beam_replay(temp,out):
    """Keep the original guard and report its operands on the same PUSH stream."""
    import subprocess
    from test_nes_word873_idle import run_consumer
    base=temp/'nes-tile821-demo-jointmirror-p1-877-sinterleave'
    ops=[]
    for line in (base/'packets.jsonl').read_text().splitlines():
        _,clock,payload,bulk=json.loads(line)
        ops.append((clock,'PUSH',payload,bulk))
        head=bytes.fromhex(payload)
        if head[0]==3 and int.from_bytes(head[8:10],'little')==952:
            break
    else:
        raise ValueError('missing SEAL')
    out.mkdir()
    def instrument(lua):
        expr='beam685 and beam685.line>=225 and beam685.line<=252 and beam685.frame==st.frameCount'
        assert lua.count('assert('+expr+')')==1
        return lua.replace('assert('+expr+')',"""assert("""+expr+""",string.format('beam g=%d read=%s:%s h=%s now=%d:%d clock=%d bytes=%d',word(0x1226),tostring(beam685 and beam685.frame),tostring(beam685 and beam685.line),tostring(beam685 and beam685.h),st.frameCount,st['ppu.scanline'],st.masterClock,n))""")
    try:
        run_consumer(temp,base,out,ops,48,instrument)
    except subprocess.CalledProcessError:
        message=(out/'map-error.txt').read_text()
        assert 'beam g=' in message,message
        assert beam_marks(out)==beam_marks(base) and len(beam_marks(out))==3
        return dict(guard=message,original=(base/'map-error.txt').read_text(),matching_marks=beam_marks(out))
    return dict(guard=None)


def partial(temp,work,tag):
    from analyze_nes_deadline875 import STRIDE,metrics
    result={'passed':False,'scenes':{},'command_guard':load(work/'command-guard.json'),
            'flash_B':(work/'link-credit/src/obj-nes-100/firmware.stm').stat().st_size}
    for clip in ('opening','transition','demo'):
        for ph in (1,2):
            prefix=f'nes-tile821-{clip}-jointmirror-p{ph}-'
            path=temp/(prefix+tag)
            control=temp/(prefix+'872-final')
            files=sorted(path.glob('frame-*.rgb'))
            for pic in files:
                assert pic.read_bytes()[7*STRIDE:231*STRIDE]==(control/pic.name).read_bytes()[7*STRIDE:231*STRIDE]
                name=pic.name.replace('frame-','map-').replace('.rgb','.bin')
                assert (path/name).read_bytes()==(control/name).read_bytes()
            actual=table_packets(path)
            assert actual==table_packets(temp/(prefix+'876-retry'))[:len(actual)]
            if (path/'joint.json').exists():
                joint=load(path/'joint.json')
                assert joint['passed'] and joint['firmware_SHA256']==result['command_guard']['firmware']
                m=metrics(path)
                row={k:m[k] for k in ('pictures','after_two_VBlanks','last_ACK','opening_marks','held_blank_VBlanks')}
                row['commits']=verified_commits(path)
            else:
                message=(path/'map-error.txt').read_text()
                import re
                line=int(re.search(r'capture\.lua:(\d+):',message)[1])
                row={'error':message,'check':(path/'capture.lua').read_text().splitlines()[line-1].strip(),
                     'last_events':window(path)[-5:],'last_ACK':None}
            row['verified_pictures']=len(files)
            result['scenes'][f'{clip}-{ph}']=row
    for name in ('begin','guards','input-guards','scrollguard','menu869'):
        result[name]=load(work/(name+'.json'))
    return result


def timings(folder,edge,work=None,phase=None):
    row=timeline(folder,edge)
    trace=window(folder)
    show=next(e for e in trace if e['g']==950 and e['event']=='reveal')
    row['show950']=show
    spi=[e for e in load(folder/'events.json') if e['event']=='SPI']
    input_ops=[e for e in spi if e.get('input_generation')==951]
    reads=[e for e in input_ops if e['opcode']=='0xd1']
    pops=[e for e in input_ops if e['opcode']=='0xd2']
    row['input_service']=[]
    for read,pop in zip(reads,pops,strict=True):
        assert read['clock']<=pop['start']
        row['input_service'].append(dict(wire_B=read['bytes'],D1_end=round(read['clock']),
                                         D2_start=round(pop['start']),D2_end=round(pop['clock'])))
    heads=[(i,b,e) for i,(b,e) in enumerate(zip(packets(folder),[e for e in spi if e['opcode']=='0xe1'],strict=True),1)
           if int.from_bytes(b[8:10],'little')==950]
    row['tail_heads']=[dict(op=b[0],section=b[1],offset=int.from_bytes(b[10:12],'little'),
                            start=round(e['start']),end=round(e['clock']))
                       for i,b,e in heads if b[0] in (3,7,9) or b[1]==5]
    obj=next(i for i,b,e in reversed(heads) if b[:2]==bytes((7,1)))
    row['last_OBJ_return']=next(e['clock'] for e in trace if e['index']==obj and e['event']=='ack')
    e=next(e for i,b,e in reversed(heads) if b[1]==5)
    row['last_table_start']=round(e['start'])
    # Clip complete transactions to this interval; elapsed includes calibrated
    # SPI/driver service. The uncovered time is not assumed to be reclaimable.
    start,stop=max(row['last_OBJ_return'],row['capture951_ready']),show['clock']
    by_opcode={}
    for e in spi:
        duration=min(stop,e['clock'])-max(start,e['start'])
        if duration>0:
            by_opcode[e['opcode']]=by_opcode.get(e['opcode'],0)+duration
    row['OBJ_to_reveal']={'clocks':stop-start,'transactions':{k:round(v) for k,v in by_opcode.items()},
                          'outside_transactions':round(stop-start-sum(by_opcode.values()))}
    if work:
        polls=load(work/f'poll951-p{phase}.json')
        end=next(r for r in polls if r['state']==2)
        # COMPLETE is observable only after the poll verified END and its
        # D2 retirement. Time the return before the D3 that authorizes COMMIT.
        assert row['last_data_D2']<end['end']<row['D3']
        row['validated_END']=end['end']
        row['END_minus_reveal']=end['end']-show['clock']
    return row


def table_packets(folder):
    # Sequence numbers may change as validated palette/OAM heads move.
    # Keep section-5 data in order and require byte-exact SEALs for all frames.
    return [b[:2]+b[4:] for b in packets(folder) if b[1]==5 or b[0]==3]


def check(temp,policies):
    root=Path(__file__).resolve().parents[2]
    report={'variants':{},'dense':{}}
    sender=load(temp/'nes-ack861/sender-demo/sender.json')['951']
    wire=bytes.fromhex(sender[-3]['wire'])
    widths=(2,1,7,4,7,1,2,8)
    at=0
    tags=[]
    while at<len(wire):
        tag=int.from_bytes(wire[at:at+2],'big')
        assert int.from_bytes(wire[at+2:at+4],'big')==951
        tags.append(tag)
        at+=4+(8 if tag>>13==0 and tag&4096 else widths[tag>>13])
    assert at==len(wire)==117 and tags[-1]==0xe004
    report['input_before_END']={'payload_B':len(wire),'D1_wire_B':len(wire)+3,'tags':[hex(t) for t in tags],
                                'incremental_raster_lengths':[(t&255)+1 for t in tags if t&0xff00==0xfc00]}
    for ph in (1,2):
        def folder(tag):
            return temp/f'nes-tile821-demo-jointmirror-p{ph}-{tag}'
        edge=points(folder('874-drain'))['previous_capture_edge']
        control=root/'probes/nes-table877-scontrol'
        report['dense'][ph]={tag:timings(folder(tag),edge) for tag in ('872-final','874-drain','876-retry')}
        report['dense'][ph]['control']=timings(folder('877-scontrol'),edge,control,ph)
    for policy in policies:
        work=root/f'probes/nes-table877-s{policy}'
        tag=f'877-s{policy}'
        if any((temp/f'nes-tile821-{clip}-jointmirror-p{ph}-{tag}'/'map-error.txt').exists()
               for clip in ('opening','transition','demo') for ph in (1,2)):
            result=partial(temp,work,tag)
            report['variants'][policy]=result
            for name in ('beam','reuse-guard'):
                if (work/(name+'.json')).exists():
                    result[name]=load(work/(name+'.json'))
            if policy=='interleave':
                offline=temp/'nes-table877-beam2'
                assert 'beam g=952 ' in result['beam']['guard']
                actual=beam_marks(temp/f'nes-tile821-demo-jointmirror-p1-{tag}')
                assert len(actual)==3 and actual==beam_marks(offline)
                result['beam']['matching_marks']=actual
            for ph in (1,2):
                path=temp/f'nes-tile821-demo-jointmirror-p{ph}-{tag}'
                if (path/'joint.json').exists():
                    ref=report['dense'][ph]['874-drain']
                    report['dense'][ph][policy]=timings(path,ref['commit_D2']-ref['commit_minus_874_edge'],work,ph)
            continue
        result=analyze(temp,root,work,tag)
        assert result['guards']['source_tag']==tag
        result['command_guard']=load(work/'command-guard.json')
        if policy=='fifo':
            guard=load(work/'reuse-guard.json')
            assert guard['queued_SEAL'] and guard['status']==0xe0 and guard['commits']==guard['generation']-905
            result['reuse-guard']=guard
        assert result['command_guard']['firmware']==result['ARM']
        result['commits']={}
        for clip in ('opening','transition','demo'):
            for ph in (1,2):
                prefix=f'nes-tile821-{clip}-jointmirror-p{ph}-'
                path=temp/(prefix+tag)
                assert table_packets(path)==table_packets(temp/(prefix+'876-retry'))
                result['commits'][f'{clip}-{ph}']=verified_commits(path)
                if clip!='demo':
                    continue
                data=report['dense'][ph]
                edge=data['874-drain']['commit_D2']-data['874-drain']['commit_minus_874_edge']
                t=timings(path,edge,work,ph)
                data[policy]=t
                for key in ('last_table_start','last_table950_end','second_D1_end'):
                    result['gates'][f'{ph}_{key}_earlier']=t[key]<min(data['874-drain'][key],data['876-retry'][key])
                result['gates'][f'{ph}_END_before_reveal']=t['END_minus_reveal']<0
                result['gates'][f'{ph}_950_on_time']=t['show950']['frame']<=data['874-drain']['show950']['frame']
                result['gates'][f'{ph}_capture']=t['commit_D2']<edge and t['source952_ready']<data['874-drain']['source952_ready']
                result['gates'][f'{ph}_936']=t['gap936']<=data['872-final']['gap936']
        result['passed']=all(result['gates'].values())
        report['variants'][policy]=result
    return report


def command_guard(work):
    from guard_nes_progress870 import Machine, crc
    src=work/'link-credit/src'
    cpu=Machine(src,bytes(128))
    count=0
    addr=cpu.lut
    for cmd in (0xd2,0xd3,0,0xff,0x50):
        for offset in (0,1,255,256,0xffff,0x10000,0x5aff90,0xffffff):
            for arg in (0,1,255):
                head=bytes([cmd])+offset.to_bytes(3,'big')+bytes([arg,arg^255])
                cpu.u.mem_write(addr,b'\x55'*10)
                cpu.call('nes_rom_spi_frame',[addr+1,cmd,offset,arg])
                assert bytes(cpu.u.mem_read(addr,10))==b'\x55'+head+bytes([crc(head,8,7,0),0xa5,0x55])
                count+=1
    return dict(cases=count,firmware=digest(src/'obj-nes-100/firmware.stm'))


def reuse_guard(temp,work):
    from guard_nes_output852 import run
    from nes_raw506 import once
    folder=temp/'nes-tile821-demo-jointmirror-p1-877-sfifo'
    data=packets(folder)
    reuse,seal=next((a,b) for a,b in zip(data,data[1:]) if a[:2]==bytes((9,4)) and
                    b[0]==3 and b[38] and int.from_bytes(b[8:10],'little')>906)
    gen=int.from_bytes(seal[8:10],'little')
    damaged=bytearray(reuse)
    damaged[-4]^=1  # wrong target-bank ACK serial; keep all pixel bytes
    def edit(b,g,case):
        return b,b==seal
    def same_queue(s,labels):
        s=once(s,'local function nextCommand()', 'local reuseClock877\nlocal function nextCommand()')
        marker=" args={cmds:read('*l'),cmds:read('*l')}"
        s=once(s,marker,marker+f"""
 if args[1]=='{reuse.hex()}' then args[1]='{damaged.hex()}';reuseClock877=target end
 if args[1]=='{seal.hex()}' then target=assert(reuseClock877) end""")
        return once(s,'  assert(captured==commits)',
                    f'  assert(sealIndex[{gen}-905]==sent and retired<sent)\n  assert(captured==commits)')
    result=run(temp,folder,'reuse-serial',column_client=work/'client02',edit_seal=edit,
               adapt_lua=same_queue,column_op=10)
    return dict(generation=gen,queued_SEAL=True,**result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('report','commands','reuse','beam'))
    p.add_argument('directory',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('policies',nargs='*')
    a=p.parse_args()
    if a.mode=='commands':
        result=command_guard(a.directory)
    elif a.mode=='beam':
        result=beam_replay(a.directory,a.directory/'nes-table877-beam2')
    elif a.mode=='reuse':
        result=reuse_guard(a.directory,Path(__file__).resolve().parents[2]/'probes/nes-table877-sfifo')
    else:
        result=check(a.directory,a.policies)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
