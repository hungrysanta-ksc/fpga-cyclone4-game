"""Compare DQ4 primary OAM, PPU high-plane fetches and stored native OBJ rows."""
from collections import defaultdict
from pathlib import Path
from prepare_cart_debug1060 import OUT


def compare(path):
    oam=defaultdict(dict)
    fetch=defaultdict(dict)
    compact=defaultdict(dict)
    valid={}
    for line in path.read_text(errors="replace").splitlines():
        fields=line.split()
        if fields[:2]==["#","OAM"]:
            field,i,value=map(int,fields[2:])
            oam[field][i]=value
        elif fields[:2]==["#","FETCH"]:
            field,y,rank,x,attr,tile,fine,mask=map(int,fields[2:])
            assert mask&16
            fetch[field][y,rank]=(x,attr,tile,fine)
        elif fields[:2]==["#","FIELD"]:
            field,ok,faults=fields[2:]
            valid[int(field)]=(int(ok),int(faults,16))
        elif fields[:2]==["#","FRAGMENT"]:
            field=int(fields[2])
            d=int(fields[3],16)
            attr=(d>>30)&255
            x=(d>>22)&255
            top=(d>>13)&511
            if top>=256:top-=512
            tile=(d&8191)|((d>>49&1)<<13)
            rank=(d>>46)&7
            for fine in range(8):
                if d>>(38+fine)&1:
                    y=top+(7-fine if attr&128 else fine)
                    assert (y,rank) not in compact[field]
                    compact[field][y,rank]=(x,attr,tile,fine)
    assert len(oam[-1])==256
    for field in range(1,4):
        assert len(oam[field])==256 and oam[field]!=oam[-1]
        expected={}
        for line in range(7,231):
            rank=0
            for i in range(0,256,4):
                top,tile,attr,x=[oam[field][i+j] for j in range(4)]
                if top<=line<top+8:
                    fine=line-top
                    expected[line-7,rank]=(x,attr,tile,7-fine if attr&128 else fine)
                    rank+=1
                    if rank==8:break
        diff=lambda other:sum(expected.get(k)!=other.get(k) for k in expected.keys()|other.keys())
        print(field,"OAM rows",len(expected),"fetches",len(fetch[field]),"fetch differences",diff(fetch[field]),
              "compact rows",len(compact[field]),"compact differences",diff(compact[field]),"geometry",valid.get(field))
        if expected!=fetch[field]:
            print("first divergence",next((k,expected.get(k),fetch[field].get(k)) for k in sorted(expected.keys()|fetch[field].keys()) if expected.get(k)!=fetch[field].get(k)))
        assert valid[field]==(1,0) and fetch[field]==compact[field] and expected==fetch[field]


if __name__=="__main__":
    compare(OUT/"resume-5-vsim.log")
