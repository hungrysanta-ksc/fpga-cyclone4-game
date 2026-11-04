"""Execute pinned 594 on the dual-clock FPGA SPI pins and a leased query fixture."""
import argparse,json,os,shutil,socket,subprocess,tempfile,zipfile
from pathlib import Path
from check_nes_receiver593 import Receiver
from check_nes_ack593 import Display
from check_nes_game478 import encode,sha
from analyze_nes_boundary592 import required
import struct
from nes_boundary165 import mailbox

ROOT=Path(__file__).resolve().parents[1]
Q=Path('C:/altera_standard/25.1std/questa_fse/win64')
RTL=('nes_region595.sv','nes_spi595.sv')
def sources(d):
    # Reproduce the mailbox used by the 589 reference from the public source.
    name='nes_native_mailbox165.sv'
    body=mailbox((ROOT/'src/nes/diagnostic'/name).read_text())
    for signal in ('src_ready','dst_valid'):
        body=body.replace('assign '+signal+'=!reset&&','assign '+signal+'=')
    (d/name).write_bytes(body.encode('ascii'))
    assert sha(d/name)=='3f2d2c4c979e1bdab9f640c6be4049a46ee7537fc670347b832bc039f16c53be'
    for f in RTL:shutil.copyfile(ROOT/'rtl'/f,d/f)

def mapping(out, build_sources=sources):
    # Reference and target use the same unconstrained region pins/device/clock boundary.
    with tempfile.TemporaryDirectory(prefix='nes595map-') as tmp:
        d=Path(tmp)
        build_sources(d)
        qsf=['set_global_assignment -name FAMILY "Cyclone IV E"',
             'set_global_assignment -name DEVICE EP4CE15F17C8',
             'set_global_assignment -name TOP_LEVEL_ENTITY nes_region595',
             'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files']
        qsf += ['set_global_assignment -name SYSTEMVERILOG_FILE '+f.name for f in d.glob('*.sv')]
        (d/'region.qsf').write_text('\n'.join(qsf)+'\n')
        (d/'region.qpf').write_text('PROJECT_REVISION = "region"\n')
        with (out/'map.log').open('wb') as log:
            subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','region'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=900,check=True)
        for name in ('region.map.rpt','region.map.summary'):shutil.copy(d/'output_files'/name,out/name)
        shutil.copy(d/'region.qsf',out/'region.qsf')
        print((out/'region.map.summary').read_text())

class Link:
    def __init__(self,io):
        self.io=io
        self.ops=[]
    def request(self,line):
        self.io.write((line+'\n').encode());self.io.flush()
        try:response=self.io.readline().strip().decode()
        except TimeoutError as error:raise TimeoutError('RTL response timeout on '+line[:32]) from error
        if not response:raise RuntimeError('RTL disconnected: '+line[:50])
        return response
    def spi(self,tx):
        answer=self.request('spi '+tx.hex())
        rx=bytes.fromhex(answer)
        assert len(rx)==len(tx),(answer,len(tx))
        self.ops.append([tx[0],len(tx),tx[18] if tx[0]==0xd4 else None])
        return rx
    def stats(self):
        return list(map(int,self.request('stats').split()))

class Input(Receiver):
    def exchange(self,tx):return self.link.spi(tx)
    def collect(self,arrays):
        start=len(self.link.ops)
        for _ in range(1000):
            if self.state_value()==4:break
            if self.state_value()==2:ok=self.call('nes_native165_prepare',[self.state,1,self.spi|1,0])
            else:ok=self.call('nes_native165_poll',[self.state,self.spi|1,0])
            assert ok,('input',self.state_value(),self.get('error'),self.link.stats(),self.link.ops[-2:])
        else:raise AssertionError('input watchdog')
        for key,values,w in zip(('maps','rows','objects','exceptions','raster','palette','raw_pixels'),arrays,(2,1,8,4,8,1,1)):
            assert bytes(self.u.mem_read(self.state+self.layout['nes_native165'][key],len(values)*w))==b''.join(v.to_bytes(w,'little') for v in values),key
        addr=self.state+self.layout['nes_native165']['tiles']
        tags=[struct.unpack('<HB',bytes(self.u.mem_read(addr+4*i,3))) for i in range(self.get('ntiles',2))]
        assert tags==required(arrays) and self.get('r_base')
        self.call('nes_native165_consumed',[self.state])
        ops=self.link.ops[start:]
        return dict(calls=len(ops),wire_B=sum(o[1] for o in ops),packets=sum(o[0]==0xd1 for o in ops),actions=[o[2] for o in ops if o[0]==0xd4])

class Runtime(Display):
    def input_exchange(self,tx):return self.link.spi(tx)

def exercise(d,a,link,normal_only=False):
    with zipfile.ZipFile(a.archive) as z:
        pins=json.loads((ROOT/'analysis/body581-verification.json').read_text())['inputs']
        import hashlib
        samples={}
        for g in range(905,a.last+1):
            geom,raw=[z.read(f'data/frame{g}.{ext}') for ext in ('geometry','raw')]
            for ext,v in [('geometry',geom),('raw',raw)]:assert hashlib.sha256(v).hexdigest()==pins[f'frame{g}.{ext}']
            arrays=encode(geom,raw,g)[2]+[list(raw)]
            samples[g]=(geom,raw,arrays)
            lines=[]
            for k,vals in enumerate(arrays):
                if vals:lines += [f'@{(7 if k==6 else k)*2048:x}']+[f'{v:016x}' for v in vals]
            (d/f'frame{g}.values').write_text('\n'.join(lines)+'\n')
            (d/f'frame{g}.counts').write_text(' '.join(map(str,[*map(len,arrays[:6]),len(raw)//256])))
    def begin(g,corrupt=False):assert link.request(f'frame {g} {int(corrupt)}')=='OK'
    def fresh():
        assert link.request('reset')=='OK'
        m=Input(a.arm);m.link=link
        return m
    m=fresh();frames=[]
    for g,(_,_,arrays) in samples.items():
        begin(g);r=m.collect(arrays)
        assert r['actions']==([0,4] if g==905 else [1,2,4]) and link.stats()[:2]==[0,0]
        frames.append(dict(generation=g,**r))
        print('normal',g,r,flush=True)
        with (a.out/'frames.jsonl').open('a',encoding='ascii') as journal:
            journal.write(json.dumps(frames[-1])+'\n')
    if normal_only:
        return dict(frames=frames,ELF=sha(a.arm/'obj-nes-100/sd2snes.elf'),RTL={n:sha(d/n) for n in RTL})
    m=fresh();begin(905,True)
    before=link.stats()
    repair=m.collect(samples[905][2])
    after=link.stats()
    assert repair['actions']==[0,3,4] and after[2]-before[2]==len(samples[905][2][0])//33
    # Warm lease was committed. Interrupt a real D1 after three bytes and
    # attempt POP. Both the frozen token and lack of release must survive.
    begin(906)
    assert m.call('nes_native165_poll',[m.state,m.spi|1,0])
    from check_nes_game478 import crc
    def control(cmd,token):
        h=bytes([cmd,0,token>>8,token&255,0,255])
        return h+bytes([crc(h,8,7,0),165])
    for _ in range(300):
        st=link.spi(control(0xd0,0))
        if st[2]&1:break
    else:raise AssertionError('warm header not available')
    tok=int.from_bytes(st[3:5],'big')
    assert link.stats()[6]==1
    link.spi(bytes([0xd1,0,0]));link.spi(control(0xd2,tok))
    broken=link.stats()
    assert broken[1]==1 and broken[6]==1 and broken[-1]==tok
    # Reset both real endpoints; verify a fresh cold full-map and full geometry.
    assert link.request('reset')=='OK'
    m.call('nes_native165_reset',[m.state]);m.set('r_epoch',1,4)
    begin(905);cold=m.collect(samples[905][2])
    assert cold['actions']==[0,4] and link.stats()[:2]==[0,0]
    display=[]
    for mode in ('normal','wrong_final_ACK','STOP_at_EA'):
        assert link.request('reset')=='OK'
        rt=Runtime(a.arm,False,400);rt.link=link;rt.ep.generation=905
        rt.saw_seal=rt.saw_ea=False;rt.guard_mode=mode;begin(905)
        for _ in range(1000):
            ok=rt.call('nes_runtime165_step',[rt.rt])
            if not ok or rt.saw_ea:break
        else:raise AssertionError('display watchdog')
        assert rt.saw_seal and bool(ok)==(mode=='normal') and rt.saw_ea==(mode!='wrong_final_ACK')
        assert rt.state_value()==(0 if ok else 4)
        counted=rt.get(rt.rt,'nes_native_runtime165','frames',4)
        assert counted==int(mode!='wrong_final_ACK')
        display.append(dict(mode=mode,EA=rt.saw_ea,displayed=counted,state=rt.state_value()))
    return dict(frames=frames,repair=repair,repair_rows=after[2]-before[2],partial_D1_token=tok,
                cold_recovery=cold,display=display,ELF=sha(a.arm/'obj-nes-100/sd2snes.elf'),
                RTL={n:sha(d/n) for n in RTL},scope='Actual ARM and SPI pin RTL, immutable query fixture; display peer and ROM service modeled.')

def simulate(a, build_sources=sources, instrument=None, runner=exercise, link_type=Link):
    expected=json.loads((ROOT/'analysis/report594-verification.json').read_text())
    assert sha(a.arm/'obj-nes-100/sd2snes.elf')==expected['input_test']['pins']['sd2snes.elf']
    with tempfile.TemporaryDirectory(prefix='nes595sim-') as tmp, socket.socket() as listener:
        d=Path(tmp);build_sources(d)
        for n in ('nes_region595_tb.sv','nes_region595_rpc.tcl'):shutil.copy(ROOT/'tools'/n,d/n)
        if instrument:instrument(d,a.out)
        def run(exe,args,log):
            with (a.out/log).open('wb') as f:subprocess.run([str(Q/exe),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=120,check=True)
        run('vlib.exe',['work'],'vlib.log')
        run('vlog.exe',['-sv',*[p.name for p in d.glob('*.sv')]],'vlog.log')
        listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(60)
        env=dict(os.environ,NES595_PORT=str(listener.getsockname()[1]))
        with (a.out/'vsim.log').open('wb') as f:
            proc=subprocess.Popen([str(Q/'vsim.exe'),'-c','-voptargs=+acc','work.region595_tb','-do','do nes_region595_rpc.tcl'],cwd=d,stdout=f,stderr=subprocess.STDOUT,env=env)
            try:
                with listener.accept()[0] as sock,sock.makefile('rwb') as io:
                    sock.settimeout(120);sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                    assert io.readline().strip()==b'READY'
                    link=link_type(io);result=runner(d,a,link)
                    assert link.request('quit')=='BYE'
                assert proc.wait(timeout=30)==0
            finally:
                if proc.poll() is None:proc.kill();proc.wait()
        (a.out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
        print('PASS',len(result['frames']),result.get('repair'),result.get('display'),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('map','sim'))
    for key in ('arm','archive','out'):p.add_argument('--'+key,type=Path,required=key=='out')
    p.add_argument('--last',type=int,choices=range(906,958),default=957);a=p.parse_args()
    if a.mode=='sim' and (a.arm is None or a.archive is None):p.error('sim requires --arm and --archive')
    a.out.mkdir(parents=True,exist_ok=False)
    if a.mode=='map':mapping(a.out)
    else:simulate(a)
