"""Model fixed-row ROM hints from CRC-accepted input blocks in the prior display lease."""
import json
from collections import deque
from nes_companion952 import Rows952
from nes_tail961 import next_pair

WIDTH=(2,1,7,4,7,1,2,8)


def obj_rows(block, generation, companion=False):
    """Map runs occupy the remaining packet. Object records carry physical CHR tags."""
    pos=0
    while pos<len(block):
        assert pos+4<=len(block)
        tag=int.from_bytes(block[pos:pos+2],"big")
        assert int.from_bytes(block[pos+2:pos+4],"big")==generation
        if tag==65535:return
        kind,index=divmod(tag,8192)
        width=8 if kind==0 and index&4096 else WIDTH[kind]
        pos+=4
        assert pos+width<=len(block)
        v=int.from_bytes(block[pos:pos+width],"big")
        pos+=width
        if kind==2 or (kind==7 and index&0x1f00==0xa00):
            physical_tag=v&8191
            for row in range(8):
                if v>>(38+row)&1:
                    yield 16*physical_tag+row
            span=next_pair(physical_tag,(v>>38)&255) if companion else None
            if span:
                first,count=span
                for i in range(count):
                    yield (first+i//8)*16+i%8


def hint(parent, companion=False):
    class Early(parent):
        def __init__(self,args):
            super().__init__(args)
            self.lease998=None
            self.todo998=deque()
            self.blocks998=0
            self.rows998=[]
            self.known998={}
            self.cursor998=0
            self.closed998=False

        def cancel_supply(self):
            self.closed998=True
            self.todo998.clear()
            self.lease998=None
            super().cancel_supply()

        def begin(self):
            # The previous capture normally flushes the whole store. If its
            # reads have retired, retain only the new input lease's store.
            keep=self.store if self.lease998==self.generation==907 and self.owner==906 else None
            super().begin()
            if keep is not None:
                self.store=self.ready_rows=keep

        def accept(self,tx,now):
            result=super().accept(tx,now)
            if self.generation==906 and tx[:2]==bytes((0xe1,3)) and not self.stopped:
                self.lease998=907
                self.store=self.ready_rows=Rows952()
                self.cursor998=result
            if self.generation==907 and tx[0]==0xe9:
                self.closed998=True
                self.todo998.clear()
            return result

        def rpc(self, now, operation="SYNC", *args):
            end=super().rpc(now,operation,*args)
            cpu=getattr(self,"cpu",None)
            if self.stopped or self.closed998 or self.lease998!=907 or not cpu or cpu.input_generation!=907:
                return end
            # index advances only after a checked D2. Do not inspect queued
            # bytes from the next D1, or book a grant beyond the current time.
            while self.blocks998 < cpu.index:
                self.blocks998+=1
                block=cpu.packets[self.blocks998-1]
                for addr in obj_rows(block,907,companion):
                    if addr not in self.known998:
                        self.known998[addr]=[self.blocks998,end]
                        self.todo998.append((addr,end))
            while self.todo998:
                addr,known=self.todo998[0]
                grant,reply=self.original_select(max(known,self.cursor998,self.free)+2)
                if reply>=end:break
                self.todo998.popleft()
                self.free=self.cursor998=reply+1
                self.store[addr]=(reply,self.chr[addr],self.chr[addr+8])
                self.rows998.append([addr,grant,reply])
            return end

        def exchange(self,seq,t,op,args):
            answer=super().exchange(seq,t,op,args)
            if op=="FINISH":
                allocated=[v[3] for v in self.grants]+[v[2] for v in self.spec+self.ahead_log+getattr(self,"fills",[])]
                early=[r[1] for r in self.rows998]
                assert len(set(early+allocated))==len(early)+len(allocated)
                (self.a.out/"hint998.json").write_text(json.dumps(dict(rows=self.rows998,known=self.known998)))
            return answer
    return Early
