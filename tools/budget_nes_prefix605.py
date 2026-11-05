"""Execute a causal ARM selector, replay immutable CHR reads and charge the shared bus."""
import argparse
import binascii
import json
import os
from pathlib import Path
import struct
import subprocess

from check_nes_game478 import (ELFFile, Uc, UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB,
    UC_HOOK_CODE, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_SP)
from analyze_nes_wire600 import MASTER, ms
from check_nes_wire600 import ROOT, pin, read
from test_nes_service509_schedule import Calendar


class Selector:
    def __init__(self,src,out):
        gcc=next((ROOT.parent/'.tools').glob('arm-gnu-toolchain*/*/bin/arm-none-eabi-gcc.exe'))
        elf=out/'selector.elf'
        subprocess.run([gcc,'-mcpu=cortex-m4','-mthumb','-Os','-ffreestanding','-fstack-usage',
                        '-nostdlib','-Wl,-Ttext=0x08000000,-e,init605','-I',src,'-o',elf,
                        ROOT/'tools/nes_prefix605.c'],cwd=out,check=True,
                       env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ['PATH']))
        self.cpu=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS)
        self.cpu.mem_map(0x08000000,65536);self.cpu.mem_map(0x20000000,65536)
        with elf.open('rb') as f:
            e=ELFFile(f);code=e.get_section_by_name('.text');self.size=code['sh_size']
            self.cpu.mem_write(code['sh_addr'],code.data())
            self.sym={s.name:s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols()}
        self.cpu.hook_add(UC_HOOK_CODE,self.step)

    def step(self,*_):self.ins+=1

    def run(self,name,*args):
        u=self.cpu;self.ins=0;ret=0x0800fff0
        for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):
            u.reg_write(reg,value)
        u.reg_write(UC_ARM_REG_SP,0x2000fff0);u.reg_write(UC_ARM_REG_LR,ret|1)
        u.emu_start(self.sym[name]|1,ret,count=200000)
        assert u.reg_read(UC_ARM_REG_PC)==ret
        return u.reg_read(UC_ARM_REG_R0)

    def select(self,resident,geom,row):
        s,r,m,w=0x20000000,0x20001000,0x20006000,0x20007000
        u=self.cpu;u.mem_write(r,bytes(len(resident)))
        assert not self.run('init605',s,r,row['generation'])  # cold: no history
        u.mem_write(r,resident)
        assert self.run('init605',s,r,row['generation'])==1
        ins=self.ins
        for block in row['prefix']:
            end=block['at'][0]
            # Make only the accepted prefix available to this call.
            u.mem_write(m,geom[:end*2])
            done=self.run('offer605',s,m,end,w)
            ins+=self.ins
            if done:break
        assert done and bytes(u.mem_read(r,len(resident)))==resident
        return bytes(u.mem_read(w,17)),ins,block


class Lease:
    """Reference model. One in-flight byte, a stopped lease must drain before restart."""
    def __init__(self):
        self.pending=None;self.stop()

    def stop(self):
        self.identity=None;self.tags=();self.data={}

    def accept(self,packet,identity):
        if self.identity or self.pending is not None or len(packet)!=17:return False
        if packet[:2]!=bytes([0x61,3]) or packet[-1]!=165:return False
        if binascii.crc_hqx(packet[:14],65535)!=int.from_bytes(packet[14:16],'big'):return False
        epoch,g,*tags=struct.unpack_from('<IH3H',packet,2)
        if (epoch,g)!=identity or max(tags)>=8192 or len(set(tags))!=3:return False
        self.identity=identity;self.tags=tags;return True

    def issue(self,addr):
        assert self.identity and addr//16 in self.tags and self.pending is None
        self.pending=(self.identity,addr)

    def response(self,value):
        identity,addr=self.pending;self.pending=None
        if self.identity==identity:self.data[addr]=value

    def lookup(self,identity,addr,committed):
        if committed and self.identity==identity and all(16*(addr//16)+i in self.data for i in range(16)):
            return self.data.get(addr)
        return None


def guards(packet,identity):
    lease=Lease()
    for n in range(len(packet)):assert not lease.accept(packet[:n],identity)
    for i in range(17):
        bad=bytearray(packet);bad[i]^=1;assert not lease.accept(bad,identity)
    assert not lease.accept(packet,(identity[0]+1,identity[1]))
    assert lease.accept(packet,identity)
    addr=16*lease.tags[0]
    for i in range(15):lease.issue(addr+i);lease.response(i)
    assert lease.lookup(identity,addr,True) is None
    lease.issue(addr+15);lease.stop();assert not lease.accept(packet,identity)
    lease.response(15);assert not lease.data and lease.accept(packet,identity)
    for i in range(16):lease.issue(addr+i);lease.response(i)
    assert lease.lookup(identity,addr,False) is None and lease.lookup((identity[0],identity[1]+1),addr,True) is None
    assert lease.lookup(identity,addr,True)==0
    lease.stop();assert lease.lookup(identity,addr,True) is None
    return ['truncated','single_bit_corruption_each_byte','epoch_generation','STOP_inflight_drain',
            'no_partial_line','no_precommit_use','STOP_invalidates_full_line']


def demands(path):
    pin(path,read(ROOT/'analysis/snoop601-verification.json')['fixture_sha256'])
    result={952:[],954:[]};g=904
    with path.open() as f:
        for line in f:
            op,k,addr,val,_=line.split()
            if op=='0':g+=1
            if op=='2' and g in result:result[g].append((int(addr,16),int(val,16)))
    return result


def main(a):
    hw=read(ROOT/'analysis/whole580-verification.json')
    cadence=read(ROOT/'analysis/wire600-verification.json')['phases']
    trace=read(ROOT/'analysis/prefix605-trace.json')
    a.out.mkdir(parents=True,exist_ok=False)
    arm=Selector(a.src.resolve(),a.out.resolve())
    pin(a.rom,read(ROOT/'analysis/trial577-package.json')['required_ROM']['sha256'])
    rom=a.rom.read_bytes();chr_rom=rom[16+16384*rom[4]:];assert len(chr_rom)==131072
    demand=demands(a.stim);cal=Calendar(a.calendar)
    rows=[]
    for row in trace['frames']:
        g=row['generation'];gf=a.data/f'frame{g}.geometry'
        pin(gf,read(ROOT/'analysis/body581-verification.json')['inputs'][gf.name])
        packet,ins,block=arm.select((a.warm/f'{g}-resident.bin').read_bytes(),gf.read_bytes(),row)
        # Optimistic wider-cache bound: all later demanded addresses are known,
        # but cannot issue before this capture supplied the tag in map or OBJ.
        geom=gf.read_bytes()
        tag_release={}
        for b in row['prefix']:
            for width,end,offset,fmt in ((2,b['at'][0],0,'H'),(8,b['at'][2],2336,'Q')):
                for word in struct.unpack_from('<'+str(end)+fmt,geom,offset):
                    tag_release.setdefault(word&8191,b['confirmed_ms'])
        assert len({addr for addr,_ in demand[g]})==len(demand[g])
        releases=sorted(tag_release[addr//16] for addr,_ in demand[g])
        identity=(1,g);lease=Lease();assert lease.accept(packet,identity)
        for tag in lease.tags:
            for addr in range(16*tag,16*tag+16):lease.issue(addr);lease.response(chr_rom[addr])
        hit=[]
        for addr,val in demand[g]:
            assert chr_rom[addr]==val
            got=lease.lookup(identity,addr,True);hit.append(got is not None)
            if got is not None:assert got==val
        first=[e['tag'] for e in row['actual_first_plans'] if e['kind']==0]
        assert len(demand[g]) in (208,272) and [addr//16 for addr,_ in demand[g][:48]]==[t for t in first for _ in range(16)]
        for ph in hw['phases']:
            phase=ph['phase'];p=ph['parameters'];assert p['CPI']==2 and p['ROM_calendar']==cal.summary
            folder=a.traces/f'nes-close561-run{phase}'
            for f in ('events.json','obj-phases.json'):pin(folder/f,ph['evidence'][f])
            origin=next(e['clock'] for e in read(folder/'events.json') if e['generation']==g and e['event']=='source_begin')
            marks=read(folder/'obj-phases.json')[str(g)]
            decode=marks['first_BG561']-marks['banks557'][0]['seal']
            overhead=ins*2/84000+ms(len(packet))+p['driver_extra_us']['0xe9']/1000
            shift=p['ROM_phase'];per_ms=MASTER/1000
            def read_bytes(start,n):
                for _ in range(n):start=cal.select(start-shift)[1]+shift
                return start
            def elapsed(t):return (t-origin)/per_ms
            baseline=next(v for v in cadence if (v['phase'],v['generation'])==(phase,g))
            deadline=baseline['relaxed_calendar']['previous_reveal']+MASTER/60
            oracle=origin;available=0
            for t in releases:
                oracle=read_bytes(max(oracle,origin+t*per_ms),1)
                available+=oracle<=deadline
            fill=read_bytes(origin+(block['confirmed_ms']+overhead)*per_ms+decode,48)
            base=origin+row['first_E9']['end_ns']*MASTER/1e9+decode
            delayed=base+overhead*per_ms
            assert fill<delayed
            first_base=read_bytes(base,48)
            first_new=read_bytes(delayed,48-sum(hit[:48]))
            last_base=read_bytes(base,len(hit));last_new=read_bytes(delayed,len(hit)-sum(hit))
            rows.append(dict(generation=g,phase=phase,tags=lease.tags,actual_first_tags=first,
                     ARM_instructions=ins,selected_at_token=block['token'],hint_complete_ms=block['confirmed_ms']+overhead,
                     added_ARM_SPI_ms=overhead,wire_B=len(packet),fill_done_ms=elapsed(fill),useful_B=sum(hit),
                     first_useful_B=sum(hit[:48]),first_batch_control_ms=elapsed(first_base),
                     first_batch_candidate_ms=elapsed(first_new),all_reads_control_ms=elapsed(last_base),
                     all_reads_candidate_ms=elapsed(last_new),model_guards=guards(packet,identity)))
            rows[-1].update(total_demand_B=len(hit),oracle_B_by_60Hz_deadline=available,
                            required_from_other_source_B=len(hit)-available,
                            previous_reveal_plus_60Hz_ms=elapsed(deadline),
                            input_commit_retire_late_ms=row['prefix'][-1]['confirmed_ms']-elapsed(deadline),
                            E9_release_late_ms=row['first_E9']['end_ns']/1e6-elapsed(deadline))
    result=dict(stage=605,phases=rows,selector_text_B=arm.size,whole_FIT=None,new_final_ACK=None,
                scope='Executable selector; separate candidate SPI/lease and ideal serial ROM calendar replay. No new hardware FPS.')
    a.report.write_bytes((json.dumps(result,indent=2)+'\n').encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('src','out','report','data','warm','calendar','rom','stim','traces'):
        p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
