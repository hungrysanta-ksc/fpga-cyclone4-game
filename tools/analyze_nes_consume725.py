"""Same723 ARM and work,725 real65816 consumer; modeled SPI/IRQ/ROM calendar."""
import argparse,bisect,csv,inspect,json,math
from pathlib import Path
from unittest.mock import patch
import analyze_nes_output664 as output
import analyze_nes_fence714 as whole
from analyze_nes_output615 import read,sha,ms,csv_groups,packets
from analyze_nes_rows713 import resources,map_image
from analyze_nes_bg674 import tile_image
from test_nes_service509_schedule import Calendar
from nes_raw506 import once

def trace725(folder,reference):
    # New prefix VRAM transfers occur while the already-validated bulk head
    # is held. Count them, without classifying bulk WRAM reception as VRAM.
    owners=list(csv.DictReader((folder/'owner725.csv').open()))
    intervals={};active={}
    for row in owners:
        key=(int(row['generation']),int(row['sequence']))
        if row['event']=='enter':assert key not in active;active[key]=int(row['clock'])
        else:intervals[key]=(active.pop(key),int(row['clock']))
    assert not active
    for g,rows in csv_groups(folder/'window.csv').items():
        for row in rows:
            if row['event']=='ppu_dma' and row['op']==7:
                assert any(gen==g and lo<=row['clock']<=hi for (gen,seq),(lo,hi) in intervals.items()),row
    source=once(inspect.getsource(output.trace),"r['event']=='ppu_dma' and r['op']==-1", "r['event']=='ppu_dma' and r['op'] in (-1,7)")
    ns=dict(vars(output));exec(compile(source,'consume725-accounting','exec'),ns)
    return ns['trace'](folder,reference)

def opportunities(folder,report):
    cpu=csv_groups(folder/'window.csv');commands=packets(folder)
    owner=list(csv.DictReader((folder/'owner725.csv').open()));result={}
    for g in range(952,958):
        cmd=report['details'][g]['packets'];rows=cpu[g];retired=[]
        for i,row in enumerate(rows):
            if row['event']!='idle524' or row['value']<65536:continue
            dma=next(r for r in rows[i+1:] if r['event']=='ppu_dma')
            last=next(r for r in rows[i+1:] if r['event']=='ppu_last')
            retired.append((last['clock'],row['value']-65536,dma['value']))
        stages=[r for r in owner if int(r['generation'])==g];pairs={}
        for row in stages:pairs.setdefault(int(row['sequence']),{})[row['event']]=int(row['clock'])
        details=[]
        for seq,st in pairs.items():
            enter=st['enter'];leave=st.get('leave',st.get('payload'));accepted=set();used=set()
            for p in cmd:
                if p['section']==2 and p['ack']<=enter:accepted.update(range(p['offset'],p['offset']+p['expanded_B']))
            for clock,off,n in retired:
                if clock<=enter:used.update(range(off,off+n))
            assert used<=accepted,(g,seq,'unaccepted map retirement')
            h,bulk,_=commands[g][seq];assert h[0]==7 and int.from_bytes(h[2:4],'little')==seq
            p=cmd[seq]
            details.append(dict(sequence=seq,section=h[1],bulk_B=len(bulk),enter=enter,leave=leave,
                map_accepted_remaining_B=len(accepted-used),load_line=p['load_line'],
                ACK_line=next(r['line'] for r in rows if r['event']=='ack' and r['clock']==p['ack']),
                owner_duration_ms=ms(leave-enter),new_map_DMA_B=sum(n for clock,off,n in retired if enter<=clock<=leave)))
        result[g]=details
    return result

def run(a):
    cal=Calendar(a.temp/'nes-service509-rom03');windows=[t for i,t in enumerate(cal.starts) if (t-cal.starts[i-1])%cal.period>cal.period//16];assert len(windows)==8
    def window(t):
        cycle,offset=divmod(math.ceil(t),cal.period);return cycle*8+bisect.bisect_right(windows,offset)-1
    arms={name:resources(a.probe.parent/'nes-supply723'/path/'src') for name,path in [('normal','normal03'),('long','arm03')]}
    client_path=a.probe/('client04' if a.variant=='B' else 'client02')
    client=read(client_path/'build.json');phases={}
    for ph in (1,2):
        old,new=[a.temp/f'{prefix}{ph}' for prefix in ('nes-supply723-c','nes-consume725-f' if a.variant=='B' else 'nes-consume725-b')]
        oj,nj=[read(p/'joint.json') for p in (old,new)]
        assert nj['passed'] and nj['commits']==53 and nj['parameters']==oj['parameters']
        assert nj['firmware_SHA256']==oj['firmware_SHA256']==arms['long']['firmware']
        assert nj['client_SHA256']==sha(client_path/'sink165.sfc')
        assert map_image(old)==map_image(new) and tile_image(old)==tile_image(new)
        def plans(p):return [(e['generation'],e['plan']) for e in read(p/'events.json') if e['event']=='call673' and e['name']=='nes_plan200_emit']
        assert plans(old)==plans(new)
        pixels={p.name:sha(p) for p in new.glob('frame-*.rgb')};assert len(pixels)==53
        assert all(sha(old/n)==v for n,v in pixels.items())
        ref=a.temp/f'nes-front638-both{ph}h'
        b=whole.report(old,ref,cal)
        with patch.object(whole,'trace',trace725):c=whole.report(new,ref,cal)
        cpu=csv_groups(new/'window.csv');oldcpu=csv_groups(old/'window.csv')
        def reveal(rows,g):return next(r for r in rows[g] if r['op']==3 and r['event']=='reveal')
        c['protected']['deadline911'] &= reveal(cpu,911)['frame']-reveal(cpu,910)['frame']<=2
        c['protected']['public951'] &= c['intervals'][951]['VBlank']<=b['intervals'][951]['VBlank']
        c['protected']['716B_gains']=all(reveal(cpu,g)['frame']-reveal(cpu,g-1)['frame']<=reveal(oldcpu,g)['frame']-reveal(oldcpu,g-1)['frame'] for g in (908,934,940,943))
        c['protected']['map_DMA_719']=all(c['details'][g]['early_DMA']['map']>=b['details'][g]['early_DMA']['map'] for g in (952,956,957))
        bg={}
        for label,row in [('base',b['details'][953]),('candidate',c['details'][953])]:
            first=row['previous_reveal']+row['relative_ms']['first_BG_ROM']/ms(1);last=row['previous_reveal']+row['relative_ms']['last_BG_ROM']/ms(1)
            bg[label]=dict(first_window=window(first),last_window=window(last),span=window(last)-window(first))
        c['protected']['BG953_window723']=bg['candidate']['span']<=bg['base']['span']
        delta=dict(dense_ms=c['dense_ms']-b['dense_ms'],last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),after951_VBlank=c['after951_VBlank']-b['after951_VBlank'],after951_mean_ms=c['after951_mean_ms']-b['after951_mean_ms'])
        owned={g:[r for r in rows if r['event']=='ppu_dma' and r['op']==7] for g,rows in cpu.items()}
        scopes=opportunities(new,c)
        boot_shift=dict(first_packet_poll_ms=ms(nj['first_packet_poll_masterclock']-oj['first_packet_poll_masterclock']),
            first_frame_ACK_ms=ms(nj['frames'][0]['ACK_masterclock']-oj['frames'][0]['ACK_masterclock']))
        for row in (b,c):
            for d in row['details'].values():d.pop('BG_plans',None);d.pop('fences',None)
        phases[ph]=dict(base=b,candidate=c,delta=delta,BG_windows=bg,owned_prefix_DMA=owned,bulk_opportunities=scopes,boot_shift=boot_shift,
            protected=all(c['protected'].values()),same_map_tile_plans_pixels=True,pixels=pixels,
            timing_gate=all(c['protected'].values()) and all(v<0 for v in delta.values()))
    guards={}
    suffixes=[('owner','owner11'),('packets','packets03'),('STOP','stop03'),('exit','exit03'),('boot','boot03')] if a.variant=='B' else [('owner','owner06'),('packets','packets01'),('STOP','stop01'),('exit','exit01'),('boot','boot01')]
    for name,suffix in suffixes:
        path=a.temp/f'nes-consume725-{suffix}'/'result.json';value=read(path)
        if isinstance(value,dict):assert value['passed']
        guards[name]=dict(SHA256=sha(path),result=value)
    result=dict(stage=725,variant=a.variant,scope=__doc__,selected=False,timing_pass=all(p['timing_gate'] for p in phases.values()),
        complete_CPU_frames=106,client=client,client_SHA256=sha(client_path/'sink165.sfc'),
        ARM=arms,resource_gate=client['physical_free_B']>=0 and all(r['Flash_B']<=212992 for r in arms.values()),
        phases=phases,guards=guards,new_RTL=False,new_ROM_contents=True,new_FIT_STA=False,
        inherited_ARM_guards='analysis/supply723-verification.json: identical normal/long ELF and firmware; no ARM rebuild',
        inherited_board='analysis/bg707-verification.json: unchanged RTL/SDC only; new ROM contents not synthesized',
        physical_FPS=False,new_installer=False,tools={p.name:sha(p) for p in Path('tools').glob('*725*.py')})
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(resource_gate=result['resource_gate'],timing_pass=result['timing_pass'],phases={p:dict(delta=r['delta'],protected=r['candidate']['protected'],owned_DMA=sum(len(v) for v in r['owned_prefix_DMA'].values())) for p,r in phases.items()})))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--variant',choices=['A','B'],default='A')
    for n in ('probe','temp','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
