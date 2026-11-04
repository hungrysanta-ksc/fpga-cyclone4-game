"""Pack only literal format strings used by the post-session NES report."""
import argparse
import ast
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from check_nes_game478 import sha

ROOT = Path(__file__).resolve().parents[1]
FILES = ("nes_budget210.c", "nes_cost471.c", "nes_menu_diagnostic.c")
# Restrict matches to these literal snprintf calls and preserve their arguments.
CALL = re.compile(r'\bsnprintf\(([^,\n]+),([^,\n]+),\s*((?:"(?:\\.|[^"\\])*"\s*)+)')
LITERAL = re.compile(r'"(?:\\.|[^"\\])*"')


def pack(strings):
    """One-level dictionary. Charge a NUL and a 16-bit offset per entry."""
    current = list(strings)
    dictionary = []
    while len(dictionary) < 128:
        freq = Counter()
        for data in current:
            for run in re.findall(rb'[\x20-\x7e\n]+', data):
                for size in range(3, min(40, len(run))+1):
                    freq.update(run[i:i+size] for i in range(len(run)-size+1))
        candidates = [(n*(len(k)-1)-len(k)-3, k) for k,n in freq.items()
                      if n*(len(k)-1) > len(k)+3]
        best, word = 0, b''
        for bound,k in sorted(candidates,reverse=True):
            if bound <= best:
                break
            gain = sum(d.count(k) for d in current)*(len(k)-1)-len(k)-3
            if gain > best:
                best, word = gain, k
        if not best:
            break
        symbol = bytes([128+len(dictionary)])
        current = [d.replace(word,symbol) for d in current]
        dictionary.append(word)
    return dictionary,current


def literal(data):
    # Fixed-length octal escapes cannot absorb the following byte.
    return '"' + ''.join(chr(b) if 32<=b<127 and b not in (34,92,63)
                         else '\\%03o'%b for b in data) + '"'


def unpack_format(match):
    return ''.join(ast.literal_eval(s) for s in LITERAL.findall(match[3])).encode('ascii')


def prepare(base,out):
    expected=json.loads((ROOT/'analysis/receiver593-verification.json').read_text())
    assert sha(base/'src/obj-nes-100/sd2snes.elf')==expected['pins']['sd2snes.elf']
    manifest=json.loads((ROOT/'analysis/whole580-manifest.json').read_text())
    sources={}
    spans={}
    formats=[]
    for name in FILES:
        p=base/'src'/name
        assert sha(p)==manifest['ARM_project_files']['src/'+name]['sha256']
        sources[name]=p.read_text(encoding='utf8')
        # save_report and formatters run after the input/display session.
        start=sources[name].index({'nes_menu_diagnostic.c':'static int pad165_format',
                                   'nes_budget210.c':'int nes_budget210_format',
                                   'nes_cost471.c':'int nes_cost471_append'}[name])
        end=sources[name].find('bool nes_cost474_pause',start) if name=='nes_cost471.c' else len(sources[name])
        spans[name]=[]
        for m in CALL.finditer(sources[name],start,end):
            data=unpack_format(m)
            if len(data)<32:
                continue
            spans[name].append((m,len(formats)))
            formats.append(data)
    dictionary,packed=pack(formats)
    for plain,data in zip(formats,packed):
        assert b''.join(dictionary[b-128] if b>=128 else bytes([b]) for b in data)==plain
    words=b''.join(word+b'\0' for word in dictionary)
    offsets=[]
    pos=0
    for word in dictionary:
        offsets.append(pos)
        pos+=len(word)+1
    assert len(words)<65536
    out.mkdir(parents=True,exist_ok=False)
    for name in ('src','utils','verilog'):
        shutil.copytree(base/name,out/name,ignore=shutil.ignore_patterns('obj-nes-100','.dep-nes-100'))
    decl='int nes_report594(char *, size_t, const unsigned char *, ...);\n'
    for name,s in sources.items():
        for m,i in reversed(spans[name]):
            s=s[:m.start()]+'nes_report594('+m[1]+','+m[2]+',(const unsigned char *)'+literal(packed[i])+s[m.end():]
        s='#include <stddef.h>\n'+decl+s
        if name=='nes_budget210.c':
            code=(ROOT/'tools/nes_report594.inc').read_text()
            s+='\n'+code.replace('WORDS594',literal(words)).replace('OFFSETS594',','.join(map(str,offsets))).replace('CAP594',str(max(map(len,formats))+1))
        (out/'src'/name).write_bytes(s.encode())
    report=dict(files=list(FILES),formats=len(formats),max_format_B=max(map(len,formats))+1,
                tokens=len(dictionary),plain_B=sum(map(len,formats)),encoded_B=sum(map(len,packed)),
                dictionary_B=len(words)+2*len(offsets),baseline_ELF=expected['pins']['sd2snes.elf'],
                sources={name:sha(out/'src'/name) for name in FILES})
    (out/'packing.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    (out/'NOT-FOR-INSTALL.txt').write_text('ARM-only receiver experiment.\n')
    print(report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    prepare(a.base,a.out)
