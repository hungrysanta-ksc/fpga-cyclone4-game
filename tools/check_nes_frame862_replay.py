"""Exercise both final links on the same scene and feed the observed PPU events to the ARM trace reader."""
import argparse
import csv
import json
import struct
import sys
from pathlib import Path
from unittest.mock import patch
from replay_nes_column853 import joint,MirrorLink,gates,main,monitor,sha
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
from analyze_nes_map830 import window
from prepare_nes_ack861 import seed_slots
from prepare_nes_frame862 import PARENTS,WORK,PROBES
from read_nes_frame862 import decode


def run(temp,edition,phase,control):
    scene=temp/'nes-ack861'
    arm=WORK/f'delivery/build{edition}/src'
    client=PROBES/('nes-column854/client-e' if edition==862 else 'nes-seal858/client-e')
    tag=f'frame{edition}-delivery'+('-control' if control else '')
    out=temp/f'nes-tile821-demo-jointmirror-p{phase}-{tag}'
    sender={k:v for k,v in json.loads((scene/'sender-demo/sender.json').read_bytes()).items() if int(k)<=915}
    original=joint.Runtime.__init__
    joint_run=joint.run
    rows=[]
    def init(cpu,args,link):
        original(cpu,args,link)
        cpu.u.mem_write(cpu.data_symbols['control862'],bytes([control]))
        seed_slots(cpu,json.loads((scene/'high-keys.json').read_bytes()))
        def hook(name,fn):
            pc=cpu.syms[name]
            cpu.u.hook_add(UC_HOOK_CODE,fn,begin=pc,end=pc)
        def frame(u,*_):
            if cpu.generation>=907:u.reg_write(UC_ARM_REG_R0,3500+cpu.generation-907)
        hook('nes_budget210_frame',frame)
        def bulk(u,*_):
            tx=u.reg_read(UC_ARM_REG_R1)
            if u.mem_read(tx,1)[0]!=0x78:return
            assert u.reg_read(UC_ARM_REG_R3)==44
            g=cpu.generation
            events=[r for r in window(out) if r['g']==g and r['op']==3]
            log=[r for r in csv.DictReader((out/'seal528.csv').read_text().splitlines()) if int(r['g'])==g and r['event']=='dma']
            begins=[r for r in events if r['event']=='ppu_dma']
            ends=[r for r in events if r['event']=='ppu_last']
            assert len(log)==len(begins)==len(ends)>0
            e0=next(r for r in reversed(cpu.events) if r.get('opcode')=='0xe0')
            assert bytes.fromhex(e0['reply'])[7:9]==bytes((1,3))
            times=[next(r['clock'] for r in events if r['event']==e) for e in ('load','reveal','ack')]+[e0['clock']]+[0]*12
            mask=gaps=0;last=None;boundary=bytes(5)
            def tick(clk):return int(clk*84000000/joint.MASTER/256)&65535
            for s,b,end in zip(log,begins,ends,strict=True):
                src=int(s['src'])&32767;port=int(s['port'])
                kind=4 if port==34 else 5 if port==4 else 0 if src<0x4000 else 1 if src<0x5000 else 2 if src<0x6000 else 3
                if not mask&(1<<kind):times[4+2*kind]=b['clock'];mask|=1<<kind
                times[5+2*kind]=end['clock']
                if last and last[0]!=b['frame']:
                    if not gaps:boundary=struct.pack('<HHB',tick(last[1]),tick(b['clock']),last[2]*8+kind)
                    gaps+=1
                last=(end['frame'],end['clock'],kind)
            response=bytes([0,0x86,0x21,15,mask+(min(gaps,3)<<6)])+struct.pack('<H16H',g,*map(tick,times))+boundary
            u.mem_write(u.reg_read(UC_ARM_REG_R2),response)
            # Use byte rate plus fixed driver cost from the matching calibration.
            cpu.clock+=44*8*joint.MASTER/2625000+cpu.driver_extra.get(0xe0,0)
            u.reg_write(UC_ARM_REG_R0,1);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
        hook('nes_native165_bulk',bulk)
        def collect(u,*_):
            pointer=int.from_bytes(u.mem_read(cpu.data_symbols['row862'],4),'little')
            # display() cleared the pointer. The menu scratch stores completed rows in order.
            if not pointer:
                n=int.from_bytes(u.mem_read(cpu.data_symbols['count862'],2),'little')
                if n>len(rows):rows.append(bytes(u.mem_read(cpu.data_symbols['ptrcache']+(n-1)*72,72)))
        hook('nes_plan200_retire',collect)
    def bounded(args):
        args.generations=list(map(int,sender));args.frames=len(sender)
        args.next_generation=dict(zip(args.generations,args.generations[1:]))
        joint_run(args)
    argv=['replay','','','','','',tag,str(Path.home()/'Downloads/nes-budget-mmc855.txt')]
    with patch.object(sys,'argv',argv),patch.object(MirrorLink,'lookup_file',scene/'hits-demo/hits.json'),gates(sender,True),patch.object(joint.Runtime,'__init__',init),patch.object(joint,'run',bounded):
        main(scene/'high','demo','jointmirror',phase,temp,arm=arm,client=client,client_hash=sha(client/'sink165.sfc'),
             link_class=MirrorLink,packet_source=sender,adapt_template=lambda s:monitor(s,'demo').replace(
             'local n=pb(0)==2 and pw(12) or pw(14)','local n=pb(0)==9 and 1472 or pb(0)==2 and pw(12) or pw(14)'))
    raw=out/'records.bin'
    raw.write_bytes(struct.pack('<4H',0x8621,edition|(0x8000 if control else 0),len(rows),0)+b''.join(rows))
    result=decode(raw);assert len(rows)==9 and not any('invalid' in r for r in result['rows']),result
    j=json.loads((out/'joint.json').read_bytes());assert j['passed'] and j['commits']==11
    baseline=temp/f'nes-tile821-demo-jointmirror-p{phase}-861-{PARENTS[edition]}-128-high'
    for g in range(905,916):
        assert (out/f'frame-{g}.rgb').read_bytes()==(baseline/f'frame-{g}.rgb').read_bytes()
    (out/'checked.json').write_text(json.dumps(dict(verified_RGB=11,rows=9,firmware=j['firmware_SHA256'],
                              client=j['client_SHA256'],model='PPU events to monitor ABI; physical bus tested separately')))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('temp',type=Path);p.add_argument('edition',type=int)
    p.add_argument('phase',type=int);p.add_argument('--control',action='store_true');a=p.parse_args();run(a.temp,a.edition,a.phase,a.control)
