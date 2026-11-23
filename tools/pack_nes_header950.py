"""Repack the same post-session report strings with a bounded two-byte dictionary."""
import ast
from collections import Counter
import re

from prepare_nes_report594 import literal

QUOTED = r'"(?:[^"\\]|\\.)*"'


def words948(code):
    decl = re.search(r'static const unsigned char words\[\] = ('+QUOTED+r');',code)
    words = []
    word = bytearray()
    for value in ast.literal_eval(decl[1]).encode('latin1'):
        if value & 127:
            word.append(value & 127)
        if value & 128:
            words.append(bytes(word))
            word.clear()
    assert not word
    return words

def reuse(src):
    """Encode only the two newly shared trace labels with the old decoder."""
    words=words948((src/'nes_budget210.c').read_text())
    f=src/'nes_sink_trace168.c'
    s=f.read_text()
    calls=list(re.finditer(r'nes_packed828\(text,capacity,(?:0|n),('+QUOTED+r')',s))
    assert len(calls)==2
    for m in reversed(calls):
        raw=ast.literal_eval(m[1]).encode('ascii')
        best=[b'']*(len(raw)+1)
        for i in reversed(range(len(raw))):
            options=[raw[i:i+1]+best[i+1]]
            options.extend(bytes([128+k])+best[i+len(w)] for k,w in enumerate(words)
                           if w and raw.startswith(w,i))
            best[i]=min(options,key=len)
        assert b''.join(words[x-128] if x>=128 else bytes([x]) for x in best[0])==raw
        s=s[:m.start(1)]+literal(best[0])+s[m.end(1):]
    f.write_text(s,newline='\n')


def pack(src):
    files = {p: p.read_text() for p in (src/'nes_budget210.c', src/'nes_cost471.c',
                                         src/'nes_menu_diagnostic.c', src/'nes_sink_trace168.c')}
    budget = src/'nes_budget210.c'
    words=words948(files[budget])
    spans = []
    for path, code in files.items():
        for call in re.finditer(r'(?:nes_packed828|REPORT828|nes_report594)\(text,[^;]*?;',code):
            for m in re.finditer(QUOTED,call[0]):
                old=ast.literal_eval(m[0]).encode('latin1')
                if any(x>=128 for x in old) or path.name=='nes_sink_trace168.c':
                    raw=b''.join(words[x-128] if x>=128 else bytes((x,)) for x in old)
                    spans.append((path,call.start()+m.start(),call.start()+m.end(),raw))
    streams=[r[3] for r in spans]
    dictionary=[]
    for code in range(128,256):
        count=Counter(s[i:i+2] for s in streams for i in range(len(s)-1))
        pair, hits=count.most_common(1)[0]
        if hits<=2:break
        dictionary.append(pair)
        streams=[s.replace(pair,bytes((code,))) for s in streams]
    expanded=[bytes((i,)) for i in range(128)]
    depth=[0]*128
    for a,b in dictionary:
        expanded.append(expanded[a]+expanded[b])
        depth.append(1+max(depth[a],depth[b]))
    assert max(depth)<16
    for (p,a,b,raw),stream in reversed(list(zip(spans,streams))):
        assert b''.join(expanded[x] for x in stream)==raw
        files[p]=files[p][:a]+literal(stream)+files[p][b:]
    # A sixteen-byte local stack covers the proven maximum nesting depth.
    s=files[budget]
    a=s.index('static const unsigned char words[] = ')
    b=s.index(' *next = 0;',a)
    files[budget]=s[:a]+'static const unsigned char pair[] = '+literal(b''.join(dictionary))+''';
 char format[720],*next=format;
 uint8_t pending[16];
 while(*encoded){
  unsigned c=*encoded++,n=0;
  for(;;){
   while(c>=128){
    unsigned i=(c-128)*2;
    pending[n++]=pair[i+1];c=pair[i];
   }
   *next++=(char)c;
   if(!n)break;
   c=pending[--n];
  }
 }
'''+s[b:]
    for p,code in files.items():
        p.write_text(code,newline='\n')
    return len(spans),max(depth)
