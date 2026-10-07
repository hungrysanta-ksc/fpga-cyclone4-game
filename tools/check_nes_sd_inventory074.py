# SPDX-License-Identifier: MIT
"""Validate SDINFO074 TXT integrity and capture shape, without approving install.
CRC is a consistency check, not authentication or independent backup proof.
"""
from pathlib import Path
import argparse,json,re,zlib
PATHS=['/sd2snes/firmware.before-sdinfo072.stm','/sd2snes/firmware.stm','/sd2snes/fpga_base.bi3','/sd2snes/m3nu.bin']
ADDRESSES=[0xffb0,0x101b0,0x7fb0,0x81b0,0x40ffb0,0x4101b0]
FIXED={'identity':'SDINFO074-BASE069','read_only_inputs':'yes','crc_is_authentication':'no','menu_classification':'offline_actual_C_pending','backup_restore_execution':'not_performed','nes_core_run':'not_performed','finished':'1','blocked':'0'}
def check(raw):
    if not 0<len(raw)<6144 or not raw.startswith(b'SDINFO074_BEGIN\r\n') or not raw.endswith(b'SDINFO074_END\r\n'):
        raise ValueError('Report framing/size')
    lines=raw.decode('ascii').split('\r\n');pairs={}
    for line in lines[1:-2]:
        if '=' not in line:raise ValueError('Report field syntax')
        k,v=line.split('=',1)
        if k in pairs:raise ValueError('Duplicate field')
        pairs[k]=v
    expected=set(FIXED)|{'payload_crc32'}
    file_fields=['path','status','size','consumed','crc32','format_ok','body_crc32','expanded','expanded_crc32']
    header_fields=['address','available','reset_address','reset_available','reset','bytes']
    expected|={f'file{i}_{k}' for i in range(4) for k in file_fields}
    expected|={f'header{i}_{k}' for i in range(6) for k in header_fields}
    if set(pairs)!=expected or any(pairs[k]!=v for k,v in FIXED.items()):raise ValueError('Report contract')
    tail=b'payload_crc32='+pairs['payload_crc32'].encode()+b'\r\nSDINFO074_END\r\n'
    if not raw.endswith(tail) or not re.fullmatch('[0-9a-f]{8}',pairs['payload_crc32']) or zlib.crc32(raw[:-len(tail)])!=int(pairs['payload_crc32'],16):raise ValueError('Payload CRC')
    def dec(k):
        if not re.fullmatch(r'0|[1-9][0-9]*',pairs[k]):raise ValueError('Decimal field')
        n=int(pairs[k]);
        if n>0xffffffff:raise ValueError('Decimal overflow')
        return n
    def hexa(k,n):
        if not re.fullmatch('[0-9a-f]{'+str(n)+'}',pairs[k]):raise ValueError('Hex field')
        return int(pairs[k],16)
    files=[]
    for i,path in enumerate(PATHS):
        f={k:(pairs[f'file{i}_{k}'] if k=='path' else hexa(f'file{i}_{k}',8) if 'crc32' in k else dec(f'file{i}_{k}')) for k in file_fields}
        if f['path']!=path or f['status'] not in range(5) or f['format_ok'] not in (0,1) or f['consumed']>f['size'] or f['expanded']>2097152:raise ValueError('File record')
        limit=1048576 if i==2 else 0x400200 if i==3 else 262656
        if f['status']==1 and (not 0<f['size']<=limit or f['consumed']!=f['size']):raise ValueError('Incomplete OK file')
        files.append(f)
    headers=[]
    for i,addr in enumerate(ADDRESSES):
        h={k:(dec(f'header{i}_{k}') if k in ['available','reset_available'] else hexa(f'header{i}_{k}',160 if k=='bytes' else 2 if k=='reset' else 8)) for k in header_fields}
        if h['address']!=addr or h['available'] not in (0,1) or h['reset_available'] not in (0,1):raise ValueError('Header shape')
        data=bytes.fromhex(pairs[f'header{i}_bytes']);h['bytes']=data.hex()
        if not h['available']:
            if any(data) or h['reset_available'] or h['reset']:raise ValueError('Unavailable header data')
        else:
            if addr+80>files[3]['size']:raise ValueError('Header outside file')
            offset=512 if addr&0xfff==0x1b0 else 0
            reset=((addr-offset)&~0x7fff)|(int.from_bytes(data[76:78],'little')&0x7fff);reset+=offset
            if reset!=h['reset_address'] or (h['reset_available'] and reset>=files[3]['size']):raise ValueError('Reset address')
        headers.append(h)
    return dict(identity=FIXED['identity'],report_crc32=pairs['payload_crc32'],files=files,headers=headers,
                original_firmware_preliminary=files[0]['status']==1 and files[0]['format_ok']==1,
                original_distinct_crc=files[0]['status']==files[1]['status']==1 and files[0]['crc32']!=files[1]['crc32'],
                crc_is_authentication=False,actual_menu_classification=False,independent_backup_proven=False,
                restore_executed=False,nes_pair_installable=False,hardware_result='collection evidence only; execution origin must be confirmed separately')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args();print(json.dumps(check(a.report.read_bytes()),ensure_ascii=False,indent=2))
