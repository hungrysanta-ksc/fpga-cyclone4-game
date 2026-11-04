"""Run the linked ARM on sealed typed input and compare against pinned MMC577."""
import argparse
import json
import struct
import zipfile
from pathlib import Path
from statistics import mean
from analyze_nes_boundary592 import blocks, required
from unicorn import UC_HOOK_MEM_READ
from check_nes_roles591 import Probe, ROOT
from check_nes_game478 import Machine, sha
from analyze_nes_transport584 import elf_cost


class Receiver(Probe):
    def setup(self,*args,**kwargs):
        super().setup(*args,**kwargs)
        typed = blocks(self.arrays,self.meta,self.rawrec)
        self.meta = [b for b in typed if b[0]&7 != 6]
        self.rawrec = [b for b in typed if b[0]&7 == 6]
        if self.fault == 'bad_kind':
            self.meta[0] = bytes([0])+self.meta[0][1:]
        if self.fault == 'short_body':
            self.meta = [self.meta[0][:-1]]
        if self.fault == 'raw_missing':
            self.rawrec = self.rawrec[:-1]

    def summaries(self):
        super().summaries()
        if self.fault=='empty_BEGIN':
            self.packets[0]=bytes([0,0])

    def hook(self,u,at,size,user):
        # Only the endpoint callback is replaced. Charge all other ARM instructions.
        if at == self.spi:
            return super().hook(u,at,size,user)
        return Machine.hook(self,u,at,size,user)

    def exchange(self,tx):
        if self.fault == 'commit_confirm' and tx[0] == 0xd2 and self.ready() and self.packets[self.index][0] == 4:
            assert self.state_value()==3 and not self.get('r_base')
            self.fault='D2_confirm'
        return super().exchange(tx)

    def checked_frame(self):
        result=self.run_frame()
        if result['ok']:
            num=self.get('ntiles',2)
            start=self.state+self.layout['nes_native165']['tiles']
            tags=[struct.unpack('<HB',bytes(self.u.mem_read(start+4*i,3))) for i in range(num)]
            assert tags==required(self.arrays)
        return result


def check(arm,archive,out):
    prior=json.loads((ROOT/'analysis/roles591-verification.json').read_text())
    assert sha(archive)==prior['pins']['archive_sha256']
    out.mkdir(parents=True,exist_ok=False)
    frames=[]
    guards=[]
    with zipfile.ZipFile(archive) as z:
        def data(g):
            return [z.read(f'data/frame{g}.{ext}') for ext in ('geometry','raw')]
        m=Receiver(arm)
        map_reads=[]
        start=m.state+m.layout['nes_native165']['maps']
        def trace_map(cpu,access,address,size,value,user):
            map_reads.extend(range(address-start,address-start+size))
        watch=m.u.hook_add(UC_HOOK_MEM_READ,trace_map,begin=start,end=start+2111)
        for g in range(905,958):
            m.setup(*data(g),g)
            row=m.checked_frame()
            assert row['ok'],(g,row,m.index,m.packets[m.index][:5])
            frames.append(row)
            if g==905:
                m.u.hook_del(watch)
                assert map_reads==list(range(2*len(m.arrays[0])))
                print('cold',row,'map bytes read',len(map_reads),flush=True)
        geometry,raw=data(905)
        for fault in ('repair_once','repair_twice','wire_crc','request_ack','D2_confirm','commit_confirm',
                      'bad_value','bad_index','duplicate_row','missing_row','meta_crc','end_crc',
                      'bad_kind','short_body','raw_missing'):
            m=Receiver(arm)
            m.setup(geometry,raw,905,fault)
            row=m.checked_frame()
            assert row['ok']==(fault=='repair_once'),(fault,row)
            if fault=='repair_once': assert row['repairs']==1
            else: assert not m.get('r_base') and m.state_value()==5
            guards.append(dict(fault=fault,**row))
        for phase in (0,1,2,3,4):
            m=Receiver(arm)
            m.setup(geometry,raw,905)
            for step in range(64):
                if step and m.get('r_phase')==phase: break
                if phase==0 and not step: break
                assert m.call('nes_native165_poll',[m.state,m.spi|1,0])
            else: raise AssertionError(phase)
            if phase==1: assert m.call('nes_native165_poll',[m.state,m.spi|1,0]) and m.get('r_seen',4)
            assert not m.get('r_base')
            m.call('nes_native165_reset',[m.state])
            assert not m.get('r_base') and not m.get('r_seen',4)
            m.set('r_epoch',1,4)
            m.toggle=0
            m.token=0
            m.serial=0
            m.previous=None
            m.setup(geometry,raw,905,cold=True)
            row=m.checked_frame()
            assert row['ok'] and m.cold
            guards.append(dict(fault=f'STOP_reset_phase{phase}',**row))
        m=Receiver(arm)
        m.setup(geometry,raw,905)
        assert m.checked_frame()['ok'] and m.get('r_base')
        m.setup(*data(906),906,'empty_BEGIN')
        row=m.run_frame()
        assert not row['ok'] and not m.get('r_base') and m.state_value()==5
        guards.append(dict(fault='empty_BEGIN_after_valid_base',**row))

        # STOP after a previous COMMIT and during a warm receive. The reset and
        # cold HELLO must discard modified RAM and tentative required-tag state.
        for target in (1,2,3):
            m=Receiver(arm)
            m.setup(geometry,raw,905)
            assert m.checked_frame()['ok'] and m.get('r_base')
            m.setup(*data(906),906)
            for _ in range(64):
                assert m.call('nes_native165_poll',[m.state,m.spi|1,0])
                if m.get('r_phase')==target: break
            else: raise AssertionError(target)
            assert not m.get('r_base')
            m.call('nes_native165_reset',[m.state])
            m.set('r_epoch',1,4)
            m.toggle=m.token=m.serial=0
            m.previous=None
            m.setup(*data(907),907,cold=True)
            row=m.checked_frame()
            assert row['ok'] and m.get('r_seen',4)==(1<<(len(m.arrays[0])//33))-1
            guards.append(dict(fault=f'warm_partial_STOP_phase{target}_full_cold',**row))
        for fault in ('false_summary','retained_RAM_corruption','right_shift'):
            m=Receiver(arm)
            m.setup(geometry,raw,905)
            assert m.checked_frame()['ok']
            changed=bytearray(geometry)
            if fault=='false_summary': changed[0]^=1
            elif fault=='right_shift': changed[:66]=struct.pack('<33H',99,*struct.unpack('<33H',geometry[:66])[:-1])
            else:
                at=m.state+m.layout['nes_native165']['maps']
                m.u.mem_write(at,bytes([m.u.mem_read(at,1)[0]^1]))
            m.setup(bytes(changed),raw,906,fault)
            row=m.checked_frame()
            assert row['ok'] and row['repairs']==int(fault=='false_summary')
            guards.append(dict(fault=fault,**row))

    driver=json.loads((ROOT/'analysis/whole580-verification.json').read_text())['phases'][0]['parameters']['driver_extra_us']
    for row in frames:
        n,k=row['packets'],row['D4']
        d0=row['calls']-2*n-k-1
        io=row['wire_B']*8/2625000*1000+(d0*driver['0xd0']+n*(driver['0xd1']+driver['0xd2'])+(1+k)*driver['0xd3'])/1000
        row.update(IO_ms=io,CPI1_input_ms=io+row['instructions']/84000,CPI2_input_ms=io+2*row['instructions']/84000)
    obj=arm/'obj-nes-100'
    groups={}
    for name,lo,hi in [('cold905',905,905),('warm907_957',907,957),('dense951_955',951,955)]:
        selected=[r for r in frames if lo<=r['generation']<=hi]
        groups[name]={k:mean(r[k] for r in selected) for k in ('wire_B','instructions','IO_ms','CPI1_input_ms','CPI2_input_ms')}
    fw=(obj/'firmware.stm').stat().st_size
    cold_pass=all(groups['cold905'][k]<=prior['groups']['cold905']['577'][k] for k in ('CPI1_input_ms','CPI2_input_ms'))
    result=dict(stage=593,cold905_ordered_map_bytes_read=len(map_reads),frames=frames,guards=guards,groups=groups,firmware_B=fw,Flash_pass=fw<=212992,cold_pass=cold_pass,
                joint_pass=fw<=212992 and cold_pass,cost=elf_cost(obj/'sd2snes.elf'),
                pins={str(p.name):sha(p) for p in (obj/'sd2snes.elf',obj/'firmware.stm',arm/'nes_native165.c',archive,Path(__file__))},
                scope='Actual ARM instructions, modeled SPI endpoint and driver costs. STOP uses receiver reset. Display ACK/EA ownership preserved by runtime, no new SNES or board timing.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(fw,cold_pass,groups,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('arm','archive','out'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args()
    check(a.arm,a.archive,a.out)
