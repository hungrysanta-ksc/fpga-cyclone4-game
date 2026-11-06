# SPDX-License-Identifier: MIT
"""Recover Flash for reuse635 through the verified post-session format dictionary."""
import argparse
import json
import shutil
from pathlib import Path
from prepare_nes_report594 import ROOT, FILES, CALL, pack, literal, unpack_format, sha


def prepare(base,out,*,keep_alias_bug=False):
    expected=json.loads((ROOT/'analysis/reuse635-verification.json').read_text())['ARM']['firmware']
    assert sha(base/'src/obj-nes-100/firmware.stm')==expected
    sources={}
    matches={}
    formats=[]
    for name in FILES:
        source=(base/'src'/name).read_text()
        start=source.index({'nes_menu_diagnostic.c':'static int pad165_format',
                            'nes_budget210.c':'int nes_budget210_format',
                            'nes_cost471.c':'int nes_cost471_append'}[name])
        end=source.find('bool nes_cost474_pause',start) if name=='nes_cost471.c' else len(source)
        matches[name]=[]
        for match in CALL.finditer(source,start,end):
            text=unpack_format(match)
            if len(text)<32:
                continue
            matches[name].append((match,len(formats)))
            formats.append(text)
        sources[name]=source
    dictionary,encoded=pack(formats)
    for original,compressed in zip(formats,encoded):
        assert b''.join(dictionary[x-128] if x>=128 else bytes((x,)) for x in compressed)==original
    words=b''.join(x+b'\0' for x in dictionary)
    offsets=[]
    offset=0
    for word in dictionary:
        offsets.append(offset)
        offset+=len(word)+1
    assert offset<65536
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    for name,source in sources.items():
        for match,index in reversed(matches[name]):
            source=source[:match.start()]+'nes_report594('+match[1]+','+match[2]+',(const unsigned char *)'+literal(encoded[index])+source[match.end():]
        source='#include <stddef.h>\nint nes_report594(char *,size_t,const unsigned char *,...);\n'+source
        if name=='nes_budget210.c':
            decoder=(ROOT/'tools/nes_report594.inc').read_text()
            source+='\n'+decoder.replace('WORDS594',literal(words)).replace('OFFSETS594',','.join(map(str,offsets))).replace('CAP594',str(max(map(len,formats))+1))
        (out/'src'/name).write_text(source,newline='\n')
    if not keep_alias_bug:
        # E1 uses io(tx,tx): the response overwrites the request header.
        p=out/'src/nes_native_runtime165.c'
        s=p.read_text()
        from nes_raw506 import once
        s=once(s,'bool ok=s->transfer(s->ctx,tx,rx,n);',
               'bool seal=opcode==0xe1&&n>=2&&tx[1]==3;\n bool ok=s->transfer(s->ctx,tx,rx,n);')
        s=once(s,'if(ok&&opcode==0xe1&&n>=2&&tx[1]==3)','if(ok&&seal)')
        p.write_text(s,newline='\n')
    result=dict(keep_alias_bug=keep_alias_bug,formats=len(formats),max_format_B=max(map(len,formats))+1,
                tokens=len(dictionary),plain_B=sum(map(len,formats)),encoded_B=sum(map(len,encoded)),
                dictionary_B=len(words)+2*len(offsets),baseline_firmware=expected,
                sources={name:sha(out/'src'/name) for name in FILES})
    (out/'packing.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','out'):p.add_argument(name,type=Path)
    p.add_argument('--keep-alias-bug',action='store_true',help='Reproduce the pre-fix control')
    a=p.parse_args();prepare(a.base,a.out,keep_alias_bug=a.keep_alias_bug)
