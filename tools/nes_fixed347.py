# SPDX-License-Identifier: MIT
"""N5-v4 candidate: same fixed scan/order; optional full-block repeat8/16.

Python encoder and C decoder proposal only; no new RTL or production ABI.
"""
import binascii,struct
from probe_nes_decode280 import encode280
from nes_delta231 import ROOT,once


def encode347(old,new,raw,prior_raw,serial,generation):
 rr=encode280(old,new,raw,prior_raw,serial,generation)
 header=bytearray(rr[0]);header[2]=4
 out=[bytes(header)];spans=expanded=0;geometry=True
 for r in rr[1:]:
  if r[:4]==b'\xff\xff\0\3':
   r=r[:4]+struct.pack('<HHH',spans,expanded,0);geometry=False
  elif r[:4]!=b'\xff\xff\0\4':
   i=r[0]&127
   at,n=(i*66,66) if i<32 else (2112+(i-32)*64,46 if i==67 else 64) if i<68 else (4398+(i-68)*64,64)
   data=(new+raw)[at:at+n]
   if i>=32:
    for w in (1,2):
     if len(data)==n and data==data[:w]*(n//w) and 2+w<len(r):
      r=bytes([128+i,w])+data[:w];break
   if geometry:
    spans+=1
    expanded+=n if r[0]&128 else len(r)-1-(n+7)//8
  out.append(r)
 c=65535;result=[]
 for r in out:
  trailer=r[:4] in (b'\xff\xff\0\3',b'\xff\xff\0\4')
  c=binascii.crc_hqx(r[:-2] if trailer else r,c)
  result.append(r[:-2]+struct.pack('<H',c) if trailer else r)
 return result


def decoder():
 s=(ROOT/'tools/nes_decode280.c').read_text()
 s=once(s,'p[2]!=2','p[2]!=4')
 s=once(s,'   if(p[0]&128){\n    if(s->phase', '''   if(p[0]&128){
    if(index>=32){
     if(n<3||(p[1]!=1&&p[1]!=2)||n<2u+p[1])return reject();
     unsigned width=p[1];
     if(s->phase==2&&(p[2]>=64||(width==2&&p[3]>=64)))return reject();
     for(unsigned i=0;i<len;i++)base[at+i]=p[2+(i&(width-1))];
     if(s->phase==1)s->expanded+=len;
     take=ci=2+width;
    }else{
    if(s->phase''')
 s=once(s,'s->expanded+=66;take=ci=4;\n   }else{','s->expanded+=66;take=ci=4;\n    }\n   }else{')
 return s
