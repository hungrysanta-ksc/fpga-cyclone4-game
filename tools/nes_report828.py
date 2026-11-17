"""Use the existing post-STOP report decoder for the budget and cost formats too."""
import ast
import re
from prepare_nes_report594 import literal, pack
from nes_raw506 import once


def reports(arm, target):
    names = ("nes_budget210.c","nes_cost471.c")
    data = {name:(arm/name).read_text() for name in names}
    budget,cost = (data[n] for n in names)
    old = re.search(r'static const char words\[\] = (".*?");',budget)
    words = ast.literal_eval(old[1]).encode("latin1").split(b"\0")[:-1]
    pattern = re.compile(r'(nes_report623\(text,\s*size,\s*(?:0|n),\s*)((?:"(?:[^"\\]|\\.)*"\s*)+)')
    spans = [(name,m) for name in names for m in pattern.finditer(data[name])]
    plain = [b"".join(ast.literal_eval(token).encode("ascii") for token in re.findall(r'"(?:[^"\\]|\\.)*"',m[2])) for _,m in spans]
    assert len(plain)>=10 and max(map(len,plain))<720
    encoded = list(plain)
    for i,w in enumerate(words):
        encoded=[s.replace(w,bytes([128+i])) for s in encoded]
    extra,unused = pack(encoded)
    for w in extra[:128-len(words)]:
        i=len(words);words.append(w)
        encoded=[s.replace(w,bytes([128+i])) for s in encoded]
    for (name,m),s,raw in reversed(list(zip(spans,encoded,plain))):
        assert b"".join(words[b-128] if b>=128 else bytes([b]) for b in s)==raw
        data[name]=data[name][:m.start()]+m[1].replace("nes_report623","REPORT828")+m[2]+","+literal(s)+data[name][m.end(2):]
    budget,cost=(data[n] for n in names)
    budget=once(budget,old[0],"static const char words[] = "+literal(b"\0".join(words)+b"\0")+";")
    offsets=[];offset=0
    for w in words:
        offsets.append(offset);offset+=len(w)+1
    budget=re.sub(r'static const uint8_t offsets\[\] = \{[^}]+\};',
                  "static const uint16_t offsets[] = {"+",".join(map(str,offsets))+"};",budget,count=1)
    budget=once(budget,"words + (symbol-128) + offsets","words + offsets")
    signature="int nes_report594(char *text, size_t capacity, const unsigned char *encoded, ...) {"
    budget=once(budget,signature,"int nes_vreport828(char *text, size_t capacity, const unsigned char *encoded, va_list args) {")
    entry=" va_list args;\n va_start(args, encoded);\n int used = vsnprintf(text, capacity, format, args);"
    budget=once(budget,entry," return vsnprintf(text, capacity, format, args);\n}\n"+signature+"\n va_list args;\n va_start(args, encoded);\n int used=nes_vreport828(text,capacity,encoded,args);")
    cost=once(cost,'int nes_report623(char *text,unsigned size,int at,const char *format,...){',
              'extern int nes_vreport828(char *,size_t,const unsigned char *,va_list);\nint nes_report623(char *text,unsigned size,int at,const char *format,...){')
    cost=once(cost,'vsnprintf(text+at,size-(unsigned)at,format,args)','nes_vreport828(text+at,size-(unsigned)at,(const unsigned char *)format,args)')
    cost=cost.replace("int nes_report623(char *text","int nes_packed828(char *text")
    header = (arm/"nes_cost471.h").read_text()
    decl = "int nes_report623(char *,unsigned,int,const char *,...) __attribute__((format(printf,4,5)));"
    header = once(header,decl,decl+"\nint nes_packed828(char *,unsigned,int,const char *,...);\n"
        "#define REPORT828(t,z,n,plain,encoded,...) "
        "(0 ? nes_report623(t,z,n,plain, ##__VA_ARGS__) : nes_packed828(t,z,n,encoded, ##__VA_ARGS__))")
    (target/"nes_cost471.h").write_text(header)
    for name,s in zip(names,(budget,cost)):
        (target/name).write_text(s)
