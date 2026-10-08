# SPDX-License-Identifier: MIT
"""ASM/CPF from the exact frozen087 fit; outputs are private, not installable."""
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import put,run,sha
PIN='2b13e7bf14b1ed1e0d5c4230f6ee9ed8600fb73f1ed82aa96b73a748ba604d76'

def encode(raw):
    out=bytearray();i=0
    while i<len(raw):
        value=raw[i];count=1
        while i+count<len(raw) and raw[i+count]==value and count<65535:count+=1
        if count>=4:
            out.extend([0x77,value,count&255,count>>8] if count>255 else [0x5b,value,count])
        else:
            for _ in range(count):
                if value in (0x9b,0x5b,0x77):out.append(0x9b)
                out.append(value)
        i+=count
    out.append(255) # report_decode080 terminal marker, not configuration data
    return bytes(out)

def decode(data):
    out=bytearray();i=0;assert data[-1]==255
    while i<len(data)-1:
        token=data[i];i+=1;value=token;count=1
        if token in (0x9b,0x5b,0x77):
            value=data[i];i+=1
            if token!=0x9b:
                count=data[i];i+=1
                if token==0x77:count|=data[i]<<8;i+=1
        out.extend(bytes([value])*count)
    assert i==len(data)-1
    return bytes(out)

def main():
    p=argparse.ArgumentParser()
    for n in ['evidence087','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();e=a.evidence087.resolve();o=a.out.resolve()
    assert sha(e/'manifest.json')==PIN and str(o).isascii() and not o.exists() and not o.is_relative_to(e)
    m=json.loads((e/'manifest.json').read_bytes())['files'];inputs={}
    for n,h in m.items():
        if n.startswith('fit01/'):
            assert sha(e/n)==h,n;inputs[n[6:]]=h
    assert any(n.startswith('db/') for n in inputs)
    for n in inputs:
        dest=o/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/'fit01'/n,dest)
    shutil.copy2(__file__,o/'executed-assemble089.py')
    for label,args in [('asm',['quartus_asm.exe','board']),('cpf',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
        log=run([a.quartus_bin/args[0],*args[1:]],o,label,300)
        assert 'successful. 0 errors, 0 warnings' in log and '25.1std.0 Build 1129' in log,log[-1500:]
    for n,h in inputs.items():
        assert sha(e/'fit01'/n)==h,n
        if n.endswith(('.sv','.sdc','.qsf','.qpf','.fit.rpt','.fit.summary','.sta.rpt','.sta.summary')):assert sha(o/n)==h,n
    raw=(o/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
    (o/'clock087.rle').write_bytes(packed)
    import zlib
    header='#include <stdint.h>\n#define CLOCK089_RAW_SIZE '+str(len(raw))+'u\n#define CLOCK089_CRC 0x%08xu\n'%zlib.crc32(raw)
    header+='static const uint8_t clock089_rle[]={\n'+''.join(','.join('0x%02x'%b for b in packed[i:i+24])+',\n' for i in range(0,len(packed),24))+'};\n'
    put(o/'clock089_payload.h',header)
    result=dict(candidate='NES-CLOCK-CONFIG-089',fit087_manifest=PIN,inputs=inputs,rbf_bytes=len(raw),rbf_sha256=sha(o/'output_files/board.rbf'),rle_bytes=len(packed),rle_sha256=sha(o/'clock087.rle'),payload_header_sha256=sha(o/'clock089_payload.h'),crc32='%08x'%zlib.crc32(raw),new_map_fit_sta=False,installable=False,physical=False)
    put(o/'result089.json',json.dumps(result,indent=2)+'\n');print('PASS ASM089 RBF=%d RLE=%d'%(len(raw),len(packed)),flush=True)

if __name__=='__main__':main()
