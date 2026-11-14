# SPDX-License-Identifier: MIT
"""Share repeated byte pairs across both immutable NES post-session report formats."""
import ast
import re
from collections import Counter
from prepare_nes_report594 import literal
from nes_raw506 import once

OLD = re.compile(r'(nes_report594\([^;\n]*?\(const unsigned char \*\))("(?:(?:\\.)|[^"\\])*")')
APPEND = re.compile(r'(nes_report623\(text,size,(?:0|n),)("(?:\\.|[^"\\])*")')


def pack_reports(read,write):
    budget="nes_budget210.c"
    source=read(budget)
    words=ast.literal_eval(re.search(r'static const char words\[\] = (".*");',source)[1]).encode("latin1").split(b"\0")
    files={name:read(name) for name in (budget,"nes_cost471.c","nes_menu_diagnostic.c")}
    records=[]
    for name,s in files.items():
        for regex in (OLD,APPEND):
            for m in regex.finditer(s):
                data=ast.literal_eval(m[2]).encode("latin1")
                plain=b"".join(words[c-128] if c>=128 else bytes([c]) for c in data) if regex is OLD else data
                assert 0 not in plain and max(plain)<128
                records.append((name,m.start(2),m.end(2),plain))
    assert len(records)>=16
    encoded=[r[3] for r in records]
    dictionary=[]
    while len(dictionary)<128:
        counts=Counter(a[i:i+2] for a in encoded for i in range(len(a)-1))
        pair=next((p for p,n in counts.most_common() if n>2 and sum(a.count(p) for a in encoded)>2),None)
        if pair is None:break
        symbol=bytes([128+len(dictionary)])
        encoded=[a.replace(pair,symbol) for a in encoded]
        dictionary.append(pair)
    expansions=[bytes([c]) for c in range(128)]
    for a,b in dictionary:
        expansions.append(expansions[a]+expansions[b])
    for (name,begin,end,plain),data in sorted(zip(records,encoded),key=lambda row:-row[0][1]):
        assert b"".join(expansions[c] for c in data)==plain
        files[name]=files[name][:begin]+literal(data)+files[name][end:]
    cap=max(len(r[3]) for r in records)+1
    # One multiline plain-ASCII format is passed through the same decoder.
    # Prove that all remaining call sites contain bounded literal formats.
    for name,source in files.items():
        pattern=r'nes_report623\(text,size,(?:0|n),\s*((?:"(?:\\.|[^"\\])*"\s*)+)[,)]'
        literals=list(re.finditer(pattern,source))
        assert len(literals)==source.count("nes_report623(")-source.count("int nes_report623(")
        for m in literals:
            chunks=re.findall(r'"(?:\\.|[^"\\])*"',m[1])
            data=b"".join(ast.literal_eval(c).encode("latin1") for c in chunks)
            assert b"\0" not in data and sum(len(expansions[c]) for c in data)<cap
    helper=f"""static const unsigned char pairs782[] = {literal(b''.join(dictionary))};
static char *expand782(char *out,unsigned c){{
 while(c>=128){{
  const unsigned char *pair=pairs782+2*(c-128);
  out=expand782(out,pair[0]);c=pair[1];
 }}
 *out++=(char)c;return out;
}}
int format782(char *text,size_t cap,const unsigned char *p,va_list args){{
 char format[{cap}],*next=format;
 while(*p)next=expand782(next,*p++);
 *next=0;return vsnprintf(text,cap,format,args);
}}
"""
    s=files[budget]
    start=s.index("int nes_report594(char *text")
    files[budget]=s[:start]+helper+"""int nes_report594(char *text,size_t cap,const unsigned char *p,...){
 va_list args;va_start(args,p);int n=format782(text,cap,p,args);va_end(args);return n;
}
"""
    n="nes_cost471.c"
    files[n]=once(files[n],"int nes_report623(char *text", "int format782(char *,size_t,const unsigned char *,va_list);\nint nes_report623(char *text")
    files[n]=once(files[n],"vsnprintf(text+at,size-(unsigned)at,format,args)","format782(text+at,size-(unsigned)at,(const unsigned char *)format,args)")
    header="nes_cost471.h"
    decl=once(read(header),"nes_report623(char *,unsigned,int,const char *,...) __attribute__((format(printf,4,5)))",
              "nes_report_packed782(char *,unsigned,int,const char *,...)")
    write(header,decl)
    for n in files:
        files[n]=files[n].replace("nes_report623(","nes_report_packed782(")
    for n,s in files.items():
        write(n,s)
