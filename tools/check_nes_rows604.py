"""Run linked M4 through the actual exporter / CDC / sealed SPI. Output consumption is modeled."""
import argparse
from collections import Counter
import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess

from analyze_nes_wire600 import DisplayGate, MASTER, Receiver, display_guards, ms
from check_nes_game478 import crc
from check_nes_region595 import Link, Q
from check_nes_wire600 import ROOT, pin, read, sha
from nes_transfer512 import input_packets
from prepare_nes_rows604 import sources
from test_nes_service509_schedule import Calendar


def bench(d,a,candidate):
    sources(a.board,a.probe,d,candidate)
    name='nes_domain_reset124.sv'
    pin(a.board/name,read(ROOT/'analysis/whole580-manifest.json')['FPGA_inputs'][name]['sha256'])
    shutil.copyfile(a.board/name,d/name)
    s=(ROOT/'tools/nes_region595_tb.sv').read_text()
    start=s.index(' nes_region595 dut(');end=s.index(' always @(posedge clk)',start)
    s=s[:start]+(ROOT/'tools/nes_rows604_connection.svh').read_text()+'\n'+s[end:]
    p=s.index('    if(corrupt!=0');q=s.index('   end',p)
    s=s[:p]+"""    if(corrupt==1 && kind==1 && index==90)pending<=64'h100;
    if(corrupt==2 && kind==1 && index==90)enable<=0;
"""+s[q:]
    s=s.replace('owned=1;enable=1;', 'origin_ns=$rtoi($realtime);owned=1;enable=1;')
    s=s.replace('dut.base_valid||dut.spi.sealed||dut.spi.read_seen||dut.action_toggle||dut.spi.token','spi.sealed||spi.read_seen||spi.token||ack||seen_ack||valid')
    (d/'tb.sv').write_bytes(s.encode())
    t=(ROOT/'tools/nes_region595_rpc.tcl').read_text()
    t=t.replace(' if {$op eq "stats"}',' if {$op eq "waitns"} {run [lindex $line 1] ns; puts $io OK; continue}\n if {$op eq "stats"}')
    t=t.replace('source_fault host_fault repair_rows leases queries injected owned dut/state dut/phase dut/repaired dut/spi/token','source_fault host_fault first_ns row_queries spi/token spi/sealed owned')
    (d/'server.tcl').write_bytes(t.encode())


def fixture(data,d,g):
    pins=read(ROOT/'analysis/body581-verification.json')['inputs']
    paths=[data/f'frame{g}.{ext}' for ext in ('geometry','raw')]
    for f in paths:pin(f,pins[f.name])
    geom,raw=[f.read_bytes() for f in paths]
    _,counts,arrays=input_packets(geom,raw,g)
    text=[]
    for k,vals in [*enumerate(arrays),(7,raw)]:
        if vals:text.extend([f'@{k*2048:x}',*(f'{v:016x}' for v in vals)])
    (d/f'frame{g}.values').write_text('\n'.join(text)+'\n')
    (d/f'frame{g}.counts').write_text(' '.join(map(str,[*counts,len(raw)//256])))
    return geom,raw


class Runtime(DisplayGate):
    def start(self,link,g,warm,extra,mode):
        self.link=link;self.ep.generation=self.generation=g
        self.guard_mode=mode;self.saw_ea=self.saw_seal=False
        for key,typ in [('resident','nes_resident211'),('video','nes_native_video165')]:
            saved=(warm/f'{g}-{key}.bin').read_bytes()
            assert len(saved)==self.layout[typ]['size']
            self.u.mem_write(getattr(self,key),saved)
        self.put(self.s,'nes_native_sink165','serial',g-905,4)
        self.put(self.s,'nes_native_sink165','displayed',1,1)
        self.calls.clear()
        self.start_ins=self.instructions
        self.elapsed_ns=0
        self.rtl_ns=2000 # time already run by the frame RPC
        self.extra=extra;self.first_bg=None;self.blocks=[]
        assert link.request(f'frame {g} 0')=='OK'

    def stamp(self):
        return (self.instructions-self.start_ins)*2*1e9/84000000+self.elapsed_ns

    def input_exchange(self,tx):
        start=self.stamp()
        gap=round(start-self.rtl_ns)
        if gap>0:
            assert self.link.request('waitns '+str(gap))=='OK'
            self.rtl_ns+=gap
        rx=self.link.spi(tx)
        n=len(tx);op=tx[0]
        self.rtl_ns+=n*3048+9000
        self.elapsed_ns+=ms(n)*1e6+self.extra[hex(op)]*1000
        if op==0xd1:self.blocks.append(rx[1:-2])
        return rx

    def output_exchange(self,tx):
        if not hasattr(self,"elapsed_ns"):
            return super().output_exchange(tx)  # Initial window query precedes the capture.
        op=tx[0]
        self.elapsed_ns+=ms(len(tx))*1e6+self.extra[hex(op)]*1000
        if op==0xe9 and self.first_bg is None:
            assert tx[4]&3 in (0,2)  # BG or leading blank tile; actual bank checked against trace below
            self.first_bg=dict(end_ns=self.stamp(),wire_B=len(tx),tx_sha256=hashlib.sha256(tx).hexdigest())
        return super().output_exchange(tx)


def check_geometry(m,geom,raw):
    # Receiver struct is retained even after final display and nes_native165_consumed.
    offset=0
    for count,(key,size,cap) in zip(struct.unpack_from('<6H',geom,5728),
            [('maps',2,1056),('rows',1,224),('objects',8,128),('exceptions',4,128),('raster',8,224),('palette',1,64)]):
        pos=m.state+m.layout['nes_native165'][key]
        assert bytes(m.u.mem_read(pos,count*size))==geom[offset:offset+count*size]
        offset+=cap*size
    assert bytes(m.u.mem_read(m.state+m.layout['nes_native165']['raw_pixels'],len(raw)))==raw


def bad_rows(src,blocks,g):
    # Invoke the real packet parser at the next valid token after all prior map records.
    m=Receiver(src,bytes(128))
    found=None
    for i,b in enumerate(blocks):
        at=3
        while at<len(b):
            tag=int.from_bytes(b[at:at+2],'big');k,idx=divmod(tag,8192)
            if tag&0xff00==0xde00:found=(i,at);break
            at+=2+(8 if k==0 and idx&4096 else (2,1,7,4,7,1,2,8)[k])
        if found:break
    i,at=found
    for tag,v in ((0xdeff,0),(0xde00,256),(0xde01,231)):
        m.start(blocks)
        while m.index<i:assert m.pump()
        bad=blocks[i][:at]+struct.pack('>HH',tag,v)
        addr=0x20013000;m.u.mem_write(addr,bad)
        assert not m.call('nes_native165_packet',[m.state,(m.start_token+i)&65535,addr,len(bad)])
        assert m.state_value()==5
    return m.guards(blocks)+['row_count','row_width','row_last_map_group']


def exercise(d,src,a,link,candidate):
    frames=[]
    phases=read(ROOT/'analysis/whole580-verification.json')['phases']
    cal=Calendar(a.calendar)
    for phase in phases:
        p=phase['parameters'];assert cal.summary==p['ROM_calendar']
        for g in (952,954):
            geom,raw=fixture(a.data,d,g)
            m=Runtime(src,False,400)
            lut=struct.pack('<64H',*map(int,re.search(r'\{(.+?)\}',(src/'nes_palette165.inc').read_text())[1].split(',')))
            m.u.mem_write(m.lut,lut)
            assert link.request('reset')=='OK'
            m.start(link,g,a.warm,p['driver_extra_us'],'normal')
            for _ in range(512):
                ok=m.call('nes_runtime165_step',[m.rt])
                assert ok,(g,m.state_value(),m.get(m.rt,'nes_native_runtime165','result'),link.stats())
                if m.saw_ea:break
            assert m.first_bg and m.saw_seal and m.saw_ea and m.state_value()==0
            check_geometry(m,geom,raw)
            fault,spi_fault,seal,row_queries,token,sealed,owned=link.stats()
            assert fault==spi_fault==sealed==owned==0 and token==len(m.blocks)
            ops=Counter(c['op'] for c in m.calls)
            wire=Counter()
            for call in m.calls:wire[call['op']]+=call['bytes']
            trace=a.traces/f"nes-close561-run{phase['phase']}"
            for f in ('events.json','obj-phases.json'):pin(trace/f,phase['evidence'][f])
            marks=read(trace/'obj-phases.json')[str(g)]
            orig=next(e['clock'] for e in read(trace/'events.json') if e.get('event')=='source_begin' and e['generation']==g)
            bank=marks['banks557'][0]
            assert m.first_bg['wire_B']==next(e['bytes'] for e in read(trace/'events.json') if e.get('opcode')=='0xe9' and e['generation']==g)
            req=orig+m.first_bg['end_ns']*MASTER/1e9+(marks['first_BG561']-bank['seal'])
            shift=p['ROM_phase'];grant,rsp=cal.select(req-shift)
            frames.append(dict(phase=phase['phase'],generation=g,first_seal_ns=seal,first_BG=m.first_bg,
                row_queries=row_queries,wire=wire,calls=ops,blocks=token,first_ROM_grant_ms=(grant+shift-orig)*1000/MASTER,
                first_ROM_response_ms=(rsp+shift-orig)*1000/MASTER,ARM_instructions=m.instructions-m.start_ins,
                final_ACK_and_EA=True))
            if candidate and phase['phase']==1:
                frames[-1]['guards']=bad_rows(src,m.blocks,g)
                frames[-1]['display_guards']=display_guards(src,g,m.blocks)
    if candidate:
        # Deny lease with a partly accumulated row and verify no later COMMIT, then reset.
        for mode,reason in ((1,3),(2,1)):
            assert link.request('reset')=='OK'
            assert link.request(f'frame 952 {mode}')=='OK'
            for _ in range(1200):
                tx=bytearray(8);tx[0]=0xd0;tx[5]=255;tx[6]=crc(tx[:6],8,7,0);tx[7]=165
                r=link.spi(tx)
                if r[2]&1:
                    n=int.from_bytes(r[5:7],'big')
                    b=link.spi(bytes([0xd1])+bytes(n+2))[1:-2]
                    assert b[-10:-8]!=bytes.fromhex('e003')
                    if b[-10:-8]==bytes.fromhex('e002'):break
                    tx[0]=0xd2;tx[2:4]=r[3:5];tx[6]=crc(tx[:6],8,7,0);link.spi(tx)
            else:raise AssertionError('missing abort')
            assert link.stats()[0]==reason
        assert link.request('reset')=='OK' and link.stats()[4:]==[0,0,0]
    return frames


def simulate(a,name,src,candidate,exercise_frames=exercise):
    d=a.out/name;d.mkdir()
    bench(d,a,candidate)
    with socket.socket() as server:
        server.bind(('127.0.0.1',0));server.listen();server.settimeout(45)
        for prog,args in [('vlib',['work']),('vlog',['-sv',*[p.name for p in d.glob('*.sv')]])]:
            with (d/(prog+'.log')).open('wb') as log:
                subprocess.run([Q/(prog+'.exe'),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,check=True)
        with (d/'simulation.log').open('wb') as log:
            process=subprocess.Popen([Q/'vsim.exe','-c','-voptargs=+acc','region595_tb','-do','do server.tcl'],
                cwd=d,env=dict(os.environ,NES595_PORT=str(server.getsockname()[1])),stdout=log,stderr=subprocess.STDOUT)
            try:
                with server.accept()[0] as sock,sock.makefile('rwb') as io:
                    sock.settimeout(120);assert io.readline().strip()==b'READY'
                    link=Link(io);frames=exercise_frames(d,src,a,link,candidate)
                    assert link.request('quit')=='BYE'
                assert process.wait(timeout=20)==0
            finally:
                if process.poll() is None:process.kill();process.wait()
    result=dict(frames=frames,firmware_B=(src/'obj-nes-100/firmware.stm').stat().st_size,firmware_SHA256=sha(src/'obj-nes-100/firmware.stm'),
                RTL={f.name:sha(f) for f in d.glob('*.sv')})
    (d/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('board','probe','data','arm','warm','out','traces','calendar','report'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    ref=simulate(a,'shared',a.probe/'ARM/src',False)
    new=simulate(a,'rows',a.arm/'src',True)
    for x,y in zip(ref['frames'],new['frames'],strict=True):
        assert x['first_BG']['tx_sha256']==y['first_BG']['tx_sha256'] and abs(x['first_seal_ns']-y['first_seal_ns'])<=50
    a.report.write_bytes((json.dumps(dict(stage=604,shared=ref,rows=new,physical=False,whole_board_FIT=None,
           scope='Linked warm ARM and live input pins. Model output credit and ACK; phased ROM calendar diagnostic only.'),indent=2)+'\n').encode())
