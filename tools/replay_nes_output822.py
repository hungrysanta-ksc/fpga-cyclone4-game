"""Two independent factors, same linked 65816, no screen or generation triggers."""
from collections import Counter
from pathlib import Path
import sys
import json
from replay_nes_tile821 import GameLink, main, WORK


class WordLink(GameLink):
    peer=None

    def next_rom(self,t):
        kind,addr=self.pending[0]
        preceding=self.peer
        self.peer=None
        if kind==1:
            counts=self.__dict__.setdefault("word_counts",{}).setdefault(self.generation,Counter())
            tag,lane=divmod(addr,16)
            line=self.cache[str(self.generation)].get(str(tag%128))
            hit=line and line[0]==tag and str(lane) in line[1]
            counts["primary_hit" if hit else "primary_miss"]+=1
            if preceding==(self.generation,addr):
                self.pending.popleft()
                counts["paired"]+=1
                counts["saved_grant"]+=int(not hit)
                return t+1
            if not hit and lane<8:
                # All decoded tile records in this replay have the short, identity-row ABI.
                self.peer=(self.generation,addr+8)
        return super().next_rom(t)

    def exchange(self,seq,t,op,args):
        if op=="FINISH":
            (self.a.out/"paired.json").write_text(json.dumps(self.word_counts))
        return super().exchange(seq,t,op,args)


class MirrorLink(GameLink):
    lookup_file=WORK.parent/"nes-output822/hits.json"
    def __init__(self,a):
        self.lookups=json.loads(self.lookup_file.read_text())[a.data.name]
        super().__init__(a)

    def next_rom(self,t):
        kind,addr=self.pending[0]
        if kind==1:
            path=self.lookups[str(self.generation)][str(addr)]
            if path==1:
                self.pending.popleft()
                return t+10
            if path==2:t+=2
        return super().next_rom(t)

if __name__=="__main__":
    source,group,mode,phase,temp=sys.argv[1:6]
    assert mode in ("ordinary","word","both","mirror","jointmirror")
    arm=(Path(sys.argv[8]).resolve() if len(sys.argv)>8 else WORK.parent/"nes-output822/link/src") if mode in ("ordinary","both","jointmirror") else None
    main(Path(source).resolve(),group,mode,int(phase),Path(temp).resolve(),
         arm=arm,link_class=WordLink if mode in ("word","both") else MirrorLink if mode in ("mirror","jointmirror") else GameLink)
