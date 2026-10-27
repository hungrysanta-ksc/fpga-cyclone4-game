# SPDX-License-Identifier: MIT
"""Fault injection at the actual SPI/read/STOP boundary;RAM freeze follows
the same host->checker->common-cancel propagation used by the board."""
import json,re,struct
from probe_nes_arm264 import crc
from nes_delta231 import sha

def guards(d,q,run):
 names=('packet905.hex','sizes905.hex','data905.hex','desc905.hex','length905.hex');original={n:(d/n).read_bytes()for n in names};results=[]
 def numbers(n):return [int(x,16)for x in original[n].decode().split()]
 def save(n,values,width):(d/n).write_text('\n'.join(f'{x:0{width}x}'for x in values)+'\n',newline='\n')
 allbytes=bytes(numbers('packet905.hex'));sizes=numbers('sizes905.hex')[1:];packets=[];at=0
 for size in sizes:packets.append(bytearray(allbytes[at:at+size]));at+=size
 assert at==len(allbytes)
 try:
  for case in range(1,18):
   for n,data in original.items():(d/n).write_bytes(data)
   pp=[bytearray(p)for p in packets];changed=[]
   if case in(7,8,9,10,11,12,13,14,15,16):
    job=next(i for i,p in enumerate(pp)if p[1]==0x90)
    if case==7:pp[0][5]^=128
    elif case==8:pp[job][11]^=1
    elif case==9:pp[next(i for i,p in enumerate(pp)if p[1]==0x92)][11]^=2
    elif case==10:pp[job][18]=0x7d
    elif case==12:pp[0][-1]^=1
    elif case==14:
     pp[job][-2:-2]=b'\0';pp[job][9:11]=struct.pack('<H',len(pp[job])-13)
    elif case==15:
     i=next(i for i,p in enumerate(pp)if p[1]==0x92);del pp[i][-3];pp[i][9:11]=struct.pack('<H',len(pp[i])-13)
    elif case==16:
     pp[job][11:13]=bytes.fromhex('f8ff');pp[job][15:17]=struct.pack('<H',16);pp[job][21:23]=bytes.fromhex('ffff')
    elif case==13:
     i=next(i for i,p in enumerate(pp)if p[1]in(0xaa,0xab))
     if pp[i][1]==0xab:assert pp[i][13]==3 and pp[i][14]<128;pp[i][15]^=1
     else:pp[i][13]^=1
    elif case==11:
     i=next(i for i,p in enumerate(pp)if p[1]in(0x90,0x91)and p[20]==3)
     record=bytes.fromhex('003000c00200047e80020000');packet=bytearray(bytes([0xe1,0x90,0])+bytes(2)+bytes(pp[0][5:9])+struct.pack('<H',14)+record+b'\0\0'+bytes(2));pp.insert(i,packet)
     desc=numbers('desc905.hex');lens=numbers('length905.hex');data=numbers('data905.hex');where=next(j for j in range(lens[0])if desc[17*j+9]==3);offset=sum(lens[1:where+1]);desc[17*where:17*where]=record+struct.pack('<HHB',0,2,3);data[offset:offset]=[0,0];lens.insert(where+1,2);lens[0]+=1
     save('desc905.hex',desc,2);save('data905.hex',data,2);save('length905.hex',lens,4)
    for i,p in enumerate(pp):
     p[3:5]=struct.pack('<H',i)
     if case!=12:p[-2:]=crc(p[:-2]).to_bytes(2,'big')
    save('packet905.hex',b''.join(pp),2);save('sizes905.hex',[len(pp)]+[len(p)for p in pp],4)
   evidence=d/f'guard{case:02d}-inputs';evidence.mkdir()
   for n in names: (evidence/n).write_bytes((d/n).read_bytes())
   out=run(q/'vsim.exe',['-c','record_tb',f'-gGUARD={case}','-do','onerror {quit -code 1};run -all;quit -f'],d,f'guard{case:02d}',180)
   m=re.search(r'PASS GUARD394 case=(\d+) independent=(\d+) host=(\d+) freeze=256',out);assert m and int(m[1])==case
   results.append(dict(case=case,checker=int(m[2]),host=int(m[3]),freeze_clocks=256,input_hashes={n:sha(evidence/n)for n in names}));print(m[0],flush=True)
 finally:
  for n,data in original.items():(d/n).write_bytes(data)
 return results
