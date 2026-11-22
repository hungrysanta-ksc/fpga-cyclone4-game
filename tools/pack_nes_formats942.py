"""Re-encode immutable diagnostic formats without changing their expansion."""
import ast
from collections import Counter
import re

from prepare_nes_report594 import literal


def compact(src):
    names=('nes_budget210.c','nes_cost471.c','nes_menu_diagnostic.c')
    files={n:(src/n).read_text() for n in names}
    match=re.search(r'static const char words\[\] = (".*?");',files[names[0]])
    words=ast.literal_eval(match[1]).encode('latin1').split(b'\0')[:-1]
    def expand(s):
        return b''.join(bytes([b]) if b<128 else words[b-128] for b in s)
    quoted=r'"(?:[^"\\]|\\.)*"'
    tokens=[]
    for n,code in files.items():
        for call in re.finditer(r'(?:nes_packed828|REPORT828|nes_report594)\(text,[^;]*?;',code):
            for m in re.finditer(quoted,call[0]):
                raw=ast.literal_eval(m[0]).encode('latin1')
                if any(b>=128 for b in raw):
                    tokens.append((n,call.start()+m.start(),call.start()+m.end(),raw))
    streams=[s for _,_,_,s in tokens]
    originals=list(map(expand,streams))
    while len(words)<128:
        counts=Counter(s[i:i+n] for s in streams for n in range(2,15) for i in range(len(s)-n+1))
        best=(0,b'')
        for key,freq in counts.items():
            if freq<2:continue
            cost=len(expand(key))+1
            if freq*(len(key)-1)-cost<=best[0]:continue
            gain=sum(s.count(key) for s in streams)*(len(key)-1)-cost
            if gain>best[0]:best=(gain,key)
        gain,key=best
        if not gain:break
        encoded=bytes([128+len(words)])
        words.append(expand(key))
        streams=[s.replace(key,encoded) for s in streams]
    assert list(map(expand,streams))==originals
    for (name,a,b,_),stream in reversed(list(zip(tokens,streams))):
        files[name]=files[name][:a]+literal(stream)+files[name][b:]
    decl='static const char words[] = '+literal(b'\0'.join(words)+b'\0')+';'
    files[names[0]]=files[names[0]].replace(match[0],decl)
    for n,code in files.items():
        (src/n).write_text(code,newline='\n')
