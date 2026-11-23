"""Keep confirmed immutable OBJ plane pairs in the existing E9 M9K across leases."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch
from contextlib import nullcontext

from nes_raw506 import once, sha
from prepare_nes_frame900 import fit, QUARTUS
from prepare_nes_trial950 import RELEASE, ROM, PlanTrace, nes_chain935


def board(temp,variant):
    src = temp/'nes-board950/board950'
    dst = (temp if variant=='retain' else temp/f'nes-951{variant}')/'nes-trial816-board951'
    assert sha(src/'sink-program.hex') == sha(ROM/'sink-program.hex')
    dst.mkdir(parents=True)
    for sub in ('rtl','sys'):
        shutil.copytree(src/sub,dst/sub)
    for p in src.iterdir():
        if p.suffix in ('.sv','.v','.vhd','.qsf','.qpf','.sdc','.tcl','.hex'):
            shutil.copyfile(p,dst/p.name)
    path=dst/'nes_e9_rows914.sv'
    if variant in ('neighbor','coldneighbor'):
        s=once(path.read_text(),"?8'hff:mask;row_no<=0;", "?8'hff:(mask==8'h01 ? 8'h03 : mask);row_no<=0;")
        if variant=='coldneighbor':
            s=once(s,'reset, invalidate, hint','reset, invalidate, empty_capture, hint')
            s=once(s,"mask==8'h01 ?", "empty_capture && mask==8'h01 ?")
            source=dst/'nes_source_tile192.sv'
            v=once(source.read_text(),' nes_e9_rows914 #',''' reg writing_bank951;
 reg [1:0] has_samples951;
 always @(posedge clk)begin
  if(reset||stop)begin writing_bank951<=0;has_samples951<=0;end
  else begin
   if(cap_start&&cap_ready)begin
    writing_bank951<=cap_generation[0];has_samples951[cap_generation[0]]<=0;
   end
   if(cap_sample&&cap_sample_ready)has_samples951[writing_bank951]<=1;
  end
 end
 nes_e9_rows914 #''')
            source.write_text(once(v,'.invalidate(invalidate),','.invalidate(invalidate),.empty_capture(!has_samples951[frame_generation[0]]),'),newline='\n')
        path.write_text(s,newline='\n')
        return
    s=once(path.read_text(),'input wire clk, reset, invalidate, hint','input wire clk, reset, flush_rom, invalidate, hint')
    s=once(s,'[6:0] cache_index','[7:0] cache_index')
    s=once(s,"a[7:4]^(CHECK_HINT?a[8:5]:a[14:11])","a[8:4]^a[15:11]")
    s=once(s,'LOW=COMPACT?4:0','LOW=COMPACT?5:0')
    s=s.replace('rows[0:127]','rows[0:255]').replace('reg [7:0] scrub','reg [8:0] scrub')
    s=s.replace('scrub[7]','scrub[8]').replace('scrub[6:0]','scrub[7:0]').replace('[6:0] index','[7:0] index')
    s=once(s,'if(reset||invalidate) scrub','if(reset||flush_rom) scrub')
    s=once(s,'!invalidate&&!reset&&scrub','!invalidate&&!reset&&!flush_rom&&scrub')
    s=once(s,'(COMPACT||!discarded)','!discarded')
    s=once(s,'(COMPACT?(pair&&!reply_address[3]):demand_pair)','(demand_pair&&!reply_address[3])')
    if variant=='empty':
        s=s.replace('[7:0] cache_index','[6:0] cache_index').replace('a[8:4]^a[15:11]','a[7:4]^a[8:5]')
        s=s.replace('LOW=COMPACT?5:0','LOW=COMPACT?4:0').replace('rows[0:255]','rows[0:127]')
        s=s.replace('reg [8:0] scrub','reg [7:0] scrub').replace('scrub[7:0]','scrub[6:0]').replace('scrub[8]','scrub[7]')
        s=s.replace('wire [7:0] index','wire [6:0] index')
    if variant=='banked':
        # Keep adjacent tile tags adjacent. One upper page bit selects the half
        # of the existing M9K. Stored high bits and the index recover every tag.
        s=once(s,'a[8:4]^a[15:11]',"{a[8]^a[12],a[7:4]}")
        s=s.replace('tag[12:4], tag[3:0]','tag[12:5], tag[4:0]')
        s=once(s,'reset, flush_rom, invalidate, hint','reset, flush_rom, invalidate, empty_capture, hint')
        s=once(s,"?8'hff:mask;row_no<=0;", "?8'hff:((empty_capture && mask==1)?8'h03:mask);row_no<=0;")
    path.write_text(s,newline='\n')
    path=dst/'nes_source_tile192.sv'
    s=once(path.read_text(),'.invalidate(invalidate),','.invalidate(invalidate),\n  .flush_rom(stop||!source_ready||source_writing||!source_is_rom||fault),')
    if variant in ('empty','banked'):
        s=once(s,' nes_e9_rows914 #',''' // A nonempty outgoing capture returns to the ordinary per-lease row policy.
 reg capture_bank951;
 reg [1:0] sampled951;
 always @(posedge clk)begin
  if(reset||stop)begin sampled951<=0;capture_bank951<=0;end
  else begin
   if(cap_start&&cap_ready) begin
    capture_bank951<=cap_generation[0];sampled951[cap_generation[0]]<=0;
   end
   if(cap_sample&&cap_sample_ready)sampled951[capture_bank951]<=1;
  end
 end
 wire flush_capture951=cap_release&&sampled951[cap_release_generation[0]];
 nes_e9_rows914 #''')
        s=once(s,'.flush_rom(stop||','.flush_rom(flush_capture951||stop||')
    if variant=='banked':
        s=once(s,'.invalidate(invalidate),','.invalidate(invalidate),.empty_capture(!sampled951[frame_generation[0]]),')
    path.write_text(s,newline='\n')


class RowStore(dict):
    """One completed pair per physical M9K address. Distinguish all 13 tag bits."""
    def __init__(self):
        super().__init__()
        self.keys_by_index={}

    def index(self,address):
        return (((address>>4)^(address>>11))&31,address&7)

    def __setitem__(self,address,value):
        index=self.index(address)
        old=self.keys_by_index.get(index)
        if old is not None and old!=address:
            del self[old]
        self.keys_by_index[index]=address
        super().__setitem__(address,value)


class FrameRows(RowStore):
    def index(self,address):
        return (((address>>4)^(address>>5))&15,address&7)


class WireTrace(PlanTrace):
    def accept(self,tx,t):
        if tx[0]==0xe9:
            suffix='' if self.generation==912 else f'-{self.generation}'
            with (self.a.out/f'e9wire914{suffix}.jsonl').open('a') as out:
                print(json.dumps([t,tx.hex()]),file=out)
        return super().accept(tx,t)


class Retain(WireTrace):
    table=RowStore
    def __init__(self,args):
        super().__init__(args)
        self.store=self.table()

    def begin(self):
        super().begin()
        self.ready_rows=self.store

    def cancel_supply(self):
        super().cancel_supply()
        self.store=self.table()

    def next_rom(self,t):
        kind,addr=self.pending[0]
        start=len(self.grants)
        result=super().next_rom(t)
        if kind==1 and not addr&8 and len(self.grants)>start:
            self.store[addr]=(result,self.chr[addr],self.chr[addr+8])
        return result

class Empty(Retain):
    table=FrameRows

    def begin(self):
        if self.owner is not None and self.owner!=self.generation and self.cache[str(self.owner)]:
            self.store=self.table()
        super().begin()


def replay(temp,phase,cache,variant):
    from replay_nes_strip869 import dense
    from test_nes_receive649 import admission
    runtime=dense.joint.Runtime
    import replay_nes_rows911
    lanes=replay_nes_rows911.lanes
    def neighbor(record):
        yield from lanes(record)
        if record[6]==1 and record[7]==1:
            yield 2,16*int.from_bytes(record[4:6],'little')+1
    class ColdPolicy:
        def pump(self,now):
            if self.cache.get(str(self.generation)):
                return super().pump(now)
            with patch.object(replay_nes_rows911,'lanes',neighbor):
                return super().pump(now)
    class ColdNeighbor(ColdPolicy,WireTrace):
        pass
    class PagedRows(RowStore):
        def index(self,address):
            tag=address>>4
            return ((tag^((tag>>4)&16))&31,address&7)
    class Banked(ColdPolicy,Empty):
        table=PagedRows
    class IdlePage(Banked):
        """Sensitivity only: one page cursor, charged single-port probes, no live eviction."""
        def __init__(self,args):
            super().__init__(args)
            self.page_key=None
            self.page_cursor=0
            self.page_after=0
            self.idle_reads=[]
        def cancel_supply(self):
            super().cancel_supply()
            self.page_key=None
        def open_page(self,address,reply):
            key=address&~255
            if self.page_key!=key:
                self.page_key=key
                self.page_cursor=0
                self.page_after=reply+1
        def next_rom(self,now):
            kind,addr=self.pending[0]
            n=len(self.grants)
            end=super().next_rom(now)
            if kind==1 and not addr&8 and len(self.grants)>n:
                self.open_page(addr,self.grants[-1][-1])
            return end
        def pump(self,now):
            n=len(self.spec)
            super().pump(now)
            if self.stopped or not self.active or self.cache.get(str(self.owner)):
                return
            for _,addr,_,reply in self.spec[n:]:
                self.open_page(addr,reply)
            while self.page_key is not None and self.page_cursor<128:
                at=max(self.page_after,self.free)+2
                if at>=now:return
                i=self.page_cursor
                addr=self.page_key+16*(i//8)+i%8
                if self.store.index(addr) in self.store.keys_by_index:
                    self.page_after=at
                else:
                    grant,reply=self.original_select(at)
                    if grant>=now:return
                    self.free=self.page_after=reply+1
                    self.store[addr]=(reply,self.chr[addr],self.chr[addr+8])
                    self.idle_reads.append((self.owner,addr,grant,reply))
                self.page_cursor+=1
        def exchange(self,seq,t,op,args):
            result=super().exchange(seq,t,op,args)
            if op=='FINISH':
                grants=[r[3] for r in self.grants]+[r[2] for r in self.spec+self.idle_reads]
                assert len(grants)==len(set(grants))
                (self.a.out/'idle951.json').write_text(json.dumps(self.idle_reads))
            return result
    optional=patch.object(replay_nes_rows911,'lanes',neighbor) if variant=='neighbor' else nullcontext()
    suppliers={'retain':Retain,'empty':Empty,'neighbor':WireTrace,'coldneighbor':ColdNeighbor,'banked':Banked,'idle':IdlePage}
    with optional,patch.object(runtime,'offer_input',admission(runtime.offer_input)),patch.object(nes_chain935,'output',lambda _:ROM):
        nes_chain935.replay(temp,'final',phase,cache,'bounded',work_arm=RELEASE,
                            tag='951'+variant,edition=950,supplier=suppliers[variant])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('board','fit','replay','fixture'))
    p.add_argument('temp',type=Path)
    p.add_argument('phase',nargs='?',type=int,choices=(1,2))
    p.add_argument('cache',nargs='?',choices=('cold','warm'))
    p.add_argument('--variant',choices=('retain','empty','neighbor','coldneighbor','banked','idle'),default='retain')
    a=p.parse_args()
    if a.variant=='idle' and a.action!='replay':
        p.error('The single page cursor is a scheduling sensitivity only.')
    if a.action=='board':
        board(a.temp,a.variant)
    elif a.action=='fit':
        fit(a.temp if a.variant=='retain' else a.temp/f'nes-951{a.variant}',951,QUARTUS)
    elif a.action=='fixture':
        from fixture_nes_port914 import fixture
        for cache in ('cold','warm'):
            for phase in (1,2):
                for generation in range(905,913):
                    fixture(a.temp,phase,cache=='cold',generation,'951'+a.variant,include_bg=True)
    else:
        if a.phase is None or a.cache is None:
            p.error('replay requires a phase and cache condition')
        replay(a.temp,a.phase,a.cache,a.variant)
