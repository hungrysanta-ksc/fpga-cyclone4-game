"""Read companion CHR rows on unused grants using the installed 951 RAM ports."""
import argparse
import json
import shutil
from contextlib import nullcontext
from unittest.mock import patch
from pathlib import Path

from fixture_nes_port914 import fixture
from nes_chr951 import RowStore, replay
from nes_raw506 import once, sha
from prepare_nes_frame900 import fit, QUARTUS
from prepare_nes_trial950 import ROM


def companion(tag, mask, halves):
    # A sparse upper pair in a 16-tile page predicts a pair in the lower half.
    if (tag & 14) == 14 and (mask & 0xf) == 0 and mask.bit_count() >= 2:
        return (tag & ~15) + 4, 16
    if halves and (tag & 8) == 0 and mask == 255:
        return (tag & ~15) + 8, 64
    return None


class Rows952(RowStore):
    def index(self,address):
        tag=address>>4
        return (((tag>>10&1)<<4) | ((tag&15)^((tag>>8&1)<<1)),address&7)


def supply(base, variant, snapshots=None, *, redirect=None):
    halves=variant!='pair'
    checked=variant=='checked'
    class Companion(base):
        table=Rows952

        def __init__(self,args):
            super().__init__(args)
            self.ahead_log=[]
            self.checkpoints=[]
            self.start=None

        def begin(self):
            previous=self.owner
            if previous!=self.generation:
                self.start=None
            super().begin()
            if snapshots is not None and previous is not None and previous!=self.owner:
                image=(snapshots/f'gen{previous}'/'rows-out951.hex')
                words=[int(s,16) for s in image.read_text().splitlines() if s.strip() and not s.startswith('//')]
                assert len(words)==256
                actual=self.table()
                for i,word in enumerate(words):
                    if word>>25!=1:
                        continue
                    upper=(word>>16)&511
                    tag=(upper<<4)|((i>>3&15)^((upper>>4&1)<<1))
                    addr=16*tag+(i&7)
                    assert actual.index(addr)==(i>>3,i&7)
                    lo,hi=word&255,(word>>8)&255
                    assert (lo,hi)==(self.chr[addr],self.chr[addr+8])
                    actual[addr]=(0,lo,hi)
                self.checkpoints.append(dict(g=self.owner,file=sha(image),
                    newly_present=sorted(actual.keys()-self.store.keys()),absent=sorted(self.store.keys()-actual.keys())))
                self.ready_rows=self.store=actual

        def cancel_supply(self):
            super().cancel_supply()
            self.start=None

        def pump(self,now):
            self.begin()
            before=self.next_batch
            super().pump(now)
            if self.stopped or not self.active or self.cache[str(self.owner)]:
                return
            batches=self.phases.get(self.owner,{}).get('banks557',[])
            for b in batches[before:self.next_batch]:
                if self.start is not None and redirect is None:
                    break
                for r in self.plansets[self.owner][b['first']:b['first']+b['count']]:
                    if r[6]!=1:
                        continue
                    tag=int.from_bytes(r[4:6],'little')
                    span=redirect(tag,r[7]) if redirect else None
                    if not span and self.start is None:
                        span=companion(tag,r[7],halves)
                    if self.start is not None and span==(self.start,self.count):
                        continue
                    if span:
                        self.start,self.count=span
                        self.cursor=0
                        self.opened=self.scan_start(b)+20*b['count']
                        if redirect is None:
                            break
            if self.start is None or self.queue:
                return
            while self.cursor < self.count:
                # Do not reserve a future grant. Core, demand and E9 rows win ties.
                addr=16*(self.start+self.cursor//8)+self.cursor%8
                at=max(self.opened,self.free)+(2 if checked else 1)
                if checked and addr in self.store and self.store[addr][0]<at:
                    if at>=now:
                        break
                    self.opened=at
                    self.cursor+=1
                    continue
                grant,reply=self.original_select(at)
                if grant>=now:
                    break
                self.free=reply+1
                self.store[addr]=(reply,self.chr[addr],self.chr[addr+8])
                self.ahead_log.append((self.owner,addr,grant,reply))
                self.cursor+=1

        def exchange(self,seq,t,op,args):
            result=super().exchange(seq,t,op,args)
            if op=='FINISH':
                grants=[v[3] for v in self.grants]+[v[2] for v in self.spec+self.ahead_log]
                assert len(grants)==len(set(grants))
                (self.a.out/'companion952.json').write_text(json.dumps(self.ahead_log))
                if snapshots is not None:
                    (self.a.out/'checkpoints952.json').write_text(json.dumps(self.checkpoints))
            return result
    return Companion


def project(temp,variant):
    return temp/f'nes-952{variant}'/'nes-trial816-board952'


def board(temp,variant):
    parent=temp/'nes-951banked/nes-trial816-board951'
    target=project(temp,variant)
    assert sha(parent/'sink-program.hex')==sha(ROM/'sink-program.hex')
    target.mkdir(parents=True)
    for sub in ('rtl','sys'):
        shutil.copytree(parent/sub,target/sub)
    for p in parent.iterdir():
        if p.suffix in ('.sv','.v','.vhd','.qsf','.qpf','.sdc','.tcl','.hex'):
            shutil.copyfile(p,target/p.name)
    path=target/'nes_e9_rows914.sv'
    s=once(path.read_text(),"{{a[8]^a[12],a[7:4]},a[2:0]}","{a[14],a[7:6],a[5]^a[12],a[4],a[2:0]}")
    s=s.replace("tag[12:5], tag[4:0]", "tag[12:4], tag[3:0]")
    s=once(s,"LOW=COMPACT?5:0","LOW=COMPACT?4:0")
    block=""" // One bounded companion run per immutable, empty capture. Its data only
 // becomes visible through the ordinary tagged physical reply/write port.
 reg selected952, pending952;
 reg [8:0] page952;
 reg [6:0] cursor952;
 wire upper_pair952=tag[3:1]==7 && mask[3:0]==0 &&
    ((mask[7] && |mask[6:4]) || (mask[6] && |mask[5:4]) || (&mask[5:4]));
 wire full_half952=HALVES && !tag[3] && (&mask);
 wire take_hint952=hint && hint_ready && empty_capture && !selected952 &&
                   (upper_pair952 || full_half952);
 wire aux952=live && armed && pending952 && todo==0 && !hint &&
             !demand && !hit_reply && !spec_owner && !reply;
 wire [21:0] address952={5'h10,page952,cursor952[6:3],1'b0,cursor952[2:0]};
 always @(posedge clk)begin
  if(!live) begin selected952<=0;pending952<=0; end
  else if(take_hint952)begin
   selected952<=1;pending952<=1;page952<=tag[12:4];
   cursor952<=upper_pair952?7'd32:7'd64;
  end else if(aux952&&grant_ready)begin
   cursor952<=cursor952+1'b1;
   if(cursor952==47 || (&cursor952))pending952<=0;
  end
 end
"""
    s=once(s,' assign request=foreground||spec;',block.replace('HALVES',"1'b1" if variant!='pair' else "1'b0")+' assign request=foreground||spec||aux952;')
    s=once(s,'assign physical_address=spec?hint_address:address;', 'assign physical_address=aux952?address952:(spec?hint_address:address);')
    s=once(s,'spec_owner<=spec;demand_pair<=!spec&&candidate;', 'spec_owner<=spec||aux952;demand_pair<=foreground&&candidate;')
    if variant=='checked':
        s=once(s,' wire aux952=live',' reg checked952;\n wire aux_slot952=live')
        s=once(s,' wire [21:0] address952=',""" wire resident952=lookup[WIDTH-1] && lookup[WIDTH-2:16]==page952;
 wire skip952=aux_slot952 && checked952 && resident952;
 wire aux952=aux_slot952 && checked952 && !resident952;
 wire probe952=aux_slot952 && !checked952;
 always @(posedge clk)checked952<=aux_slot952 && !skip952 && !(aux952&&grant_ready);
 wire [21:0] address952=""")
        s=once(s,'else if(aux952&&grant_ready)begin','else if(skip952||(aux952&&grant_ready))begin')
        s=once(s,' wire lookup_demand='," wire [21:0] ahead952=todo==0?address952:hint_address;\n wire lookup_demand=")
        s=s.replace('cache_index(hint_address)','cache_index(ahead952)')
        s=s.replace('if(lookup_demand||lookup_hint)','if(lookup_demand||lookup_hint||probe952)')
        s=s.replace('else if(lookup_hint)lookup','else if(lookup_hint||probe952)lookup')
    path.write_text(s,newline='\n')


def complete_row_set():
    import replay_nes_rows911
    original_lanes=replay_nes_rows911.lanes
    def complete_lanes(record):
        if record[6]==1 and (record[7] & 15)==15:
            record=record[:7]+bytes([255])+record[8:]
        yield from original_lanes(record)
    return patch.object(replay_nes_rows911,'lanes',complete_lanes)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('board','fit','replay','fixture'))
    p.add_argument('temp',type=Path)
    p.add_argument('variant',choices=('pair','halves','checked','baseline'))
    p.add_argument('phase',type=int,nargs='?',choices=(1,2))
    p.add_argument('cache',nargs='?',choices=('warm','cold'))
    p.add_argument('--snapshots',action='store_true',help='apply independently verified RTL row contents at each cold lease boundary')
    p.add_argument('--rtl-rows',action='store_true',help='price COMPLETE_ROW_SET as executed by the compact E9 reader')
    a=p.parse_args()
    tag='952'+a.variant+('snap' if a.snapshots else '')+('rows' if a.rtl_rows else '')
    if a.variant=='baseline':
        if a.action!='replay' or not a.phase or not a.cache or a.snapshots:
            p.error('baseline requires replay, phase and cache')
        with complete_row_set() if a.rtl_rows else nullcontext():
            replay(a.temp,a.phase,a.cache,'banked',tag='951banked'+('rows' if a.rtl_rows else ''))
    elif a.action=='board':
        board(a.temp,a.variant)
    elif a.action=='fit':
        fit(project(a.temp,a.variant).parent,952,QUARTUS)
    elif a.action=='fixture':
        for phase in (1,2):
            for cache in (('cold',) if a.snapshots else ('warm','cold')):
                for g in range(905,913):
                    fixture(a.temp,phase,cache=='cold',g,tag,include_bg=True)
    elif a.phase and a.cache:
        saved=None
        if a.snapshots and a.cache=='cold':
            from analyze_nes_deadline947 import directory
            saved=directory(a.temp,a.phase,'952'+a.variant,a.cache)
        scope=complete_row_set() if a.rtl_rows else nullcontext()
        with scope:
            replay(a.temp,a.phase,a.cache,'banked',wrap=lambda b:supply(b,a.variant,saved),tag=tag)
    else:
        p.error('replay requires phase and cache')
